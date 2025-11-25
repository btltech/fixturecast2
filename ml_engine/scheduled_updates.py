"""
Scheduled Update Runner
=======================
Automatically runs feedback updates and model improvements on a schedule.
Can be run via cron or as a background service.

Recommended schedule: 1st and 15th of each month at 3:00 AM UTC

Cron setup:
    0 3 1,15 * * /path/to/venv/bin/python /path/to/scheduled_updates.py >> /var/log/fixturecast_updates.log 2>&1

Or use launchd on macOS - see instructions below.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml_engine.auto_update_results import update_results_from_api, check_model_performance
from ml_engine.retrain_with_feedback import update_ensemble_weights, update_elo_from_feedback
from ml_engine.feedback_learning import get_performance_report

# Configuration
CONFIG_FILE = BASE_DIR / "ml_engine" / "trained_models" / "scheduler_config.json"
LOG_FILE = BASE_DIR / "ml_engine" / "trained_models" / "update_log.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load scheduler configuration"""
    default_config = {
        "enabled": True,
        "update_days": [1, 15],  # 1st and 15th of month
        "update_hour_utc": 3,    # 3 AM UTC
        "min_samples_for_weight_update": 20,
        "leagues_to_track": [39, 140, 135, 78, 61, 40, 2, 3],
        "last_run": None,
        "run_count": 0
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Save default config
    save_config(default_config)
    return default_config


def save_config(config):
    """Save scheduler configuration"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, default=str)


def log_update(status: str, details: dict):
    """Log update run to history"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "details": details
    }
    
    # Load existing log
    log_data = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE) as f:
                log_data = json.load(f)
        except:
            log_data = []
    
    # Append and keep last 100 entries
    log_data.append(log_entry)
    log_data = log_data[-100:]
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2, default=str)


def should_run_today(config: dict) -> bool:
    """Check if update should run today based on config"""
    today = datetime.now()
    return today.day in config.get("update_days", [1, 15])


def run_scheduled_update(force: bool = False):
    """
    Run the complete scheduled update pipeline:
    1. Fetch and record completed match results
    2. Evaluate predictions vs actual
    3. Update model weights based on performance
    4. Update Elo ratings
    5. Generate performance report
    """
    config = load_config()
    
    if not config.get("enabled") and not force:
        logger.info("Scheduled updates are disabled")
        return {"status": "disabled"}
    
    if not should_run_today(config) and not force:
        logger.info(f"Not scheduled to run today (day {datetime.now().day})")
        return {"status": "not_scheduled"}
    
    logger.info("="*60)
    logger.info("STARTING SCHEDULED UPDATE")
    logger.info(f"Run #{config.get('run_count', 0) + 1}")
    logger.info("="*60)
    
    results = {
        "started_at": datetime.now().isoformat(),
        "results_updated": 0,
        "weights_updated": False,
        "elo_updated": False,
        "errors": []
    }
    
    try:
        # Step 1: Fetch and update results
        logger.info("\n[1/4] Fetching completed match results...")
        try:
            update_result = update_results_from_api(
                leagues=config.get("leagues_to_track")
            )
            results["results_updated"] = update_result.get("updated", 0)
            logger.info(f"Updated {results['results_updated']} results")
        except Exception as e:
            logger.error(f"Error updating results: {e}")
            results["errors"].append(f"Results update: {str(e)}")
        
        # Step 2: Update ensemble weights
        logger.info("\n[2/4] Updating ensemble weights...")
        try:
            min_samples = config.get("min_samples_for_weight_update", 20)
            new_weights = update_ensemble_weights(min_samples=min_samples)
            results["weights_updated"] = new_weights is not None
            if new_weights:
                logger.info("Weights updated successfully")
            else:
                logger.info("Not enough data for weight update")
        except Exception as e:
            logger.error(f"Error updating weights: {e}")
            results["errors"].append(f"Weight update: {str(e)}")
        
        # Step 3: Update Elo ratings
        logger.info("\n[3/4] Updating Elo ratings...")
        try:
            update_elo_from_feedback()
            results["elo_updated"] = True
            logger.info("Elo ratings updated")
        except Exception as e:
            logger.error(f"Error updating Elo: {e}")
            results["errors"].append(f"Elo update: {str(e)}")
        
        # Step 4: Generate performance report
        logger.info("\n[4/4] Generating performance report...")
        try:
            report = get_performance_report()
            results["performance"] = {
                "overall_accuracy": report.get("overall", {}).get("accuracy_pct", "N/A"),
                "total_evaluated": report.get("overall", {}).get("total", 0)
            }
            check_model_performance()
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            results["errors"].append(f"Report: {str(e)}")
        
        # Update config
        config["last_run"] = datetime.now().isoformat()
        config["run_count"] = config.get("run_count", 0) + 1
        save_config(config)
        
        results["completed_at"] = datetime.now().isoformat()
        results["status"] = "success" if not results["errors"] else "partial"
        
        log_update(results["status"], results)
        
        logger.info("\n" + "="*60)
        logger.info("UPDATE COMPLETE")
        logger.info(f"Results updated: {results['results_updated']}")
        logger.info(f"Weights updated: {results['weights_updated']}")
        logger.info(f"Elo updated: {results['elo_updated']}")
        if results["errors"]:
            logger.warning(f"Errors: {len(results['errors'])}")
        logger.info("="*60)
        
        return results
        
    except Exception as e:
        logger.error(f"Critical error in scheduled update: {e}")
        results["status"] = "failed"
        results["errors"].append(f"Critical: {str(e)}")
        log_update("failed", results)
        return results


def generate_cron_instructions():
    """Generate cron/launchd setup instructions"""
    python_path = sys.executable
    script_path = Path(__file__).absolute()
    
    print("\n" + "="*70)
    print("SCHEDULED UPDATE SETUP INSTRUCTIONS")
    print("="*70)
    
    # Cron (Linux/macOS)
    print("\n📅 Option 1: Cron (Linux/macOS)")
    print("-"*40)
    print("Run: crontab -e")
    print("Add this line (runs 1st and 15th at 3 AM UTC):")
    print(f"\n0 3 1,15 * * {python_path} {script_path} --run >> /tmp/fixturecast_updates.log 2>&1\n")
    
    # macOS launchd
    print("\n📅 Option 2: launchd (macOS)")
    print("-"*40)
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fixturecast.scheduled-updates</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>--run</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Day</key>
            <integer>1</integer>
            <key>Hour</key>
            <integer>3</integer>
        </dict>
        <dict>
            <key>Day</key>
            <integer>15</integer>
            <key>Hour</key>
            <integer>3</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/fixturecast_updates.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/fixturecast_updates_error.log</string>
</dict>
</plist>'''
    
    plist_path = Path.home() / "Library/LaunchAgents/com.fixturecast.scheduled-updates.plist"
    print(f"Save this to: {plist_path}")
    print(f"\n{plist_content}\n")
    print("Then run:")
    print(f"  launchctl load {plist_path}")
    print(f"  launchctl start com.fixturecast.scheduled-updates")
    
    print("\n" + "="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="FixtureCast Scheduled Updates")
    parser.add_argument("--run", action="store_true", help="Run the update now")
    parser.add_argument("--force", action="store_true", help="Force run even if not scheduled")
    parser.add_argument("--setup", action="store_true", help="Show setup instructions")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--enable", action="store_true", help="Enable scheduled updates")
    parser.add_argument("--disable", action="store_true", help="Disable scheduled updates")
    
    args = parser.parse_args()
    
    if args.setup:
        generate_cron_instructions()
        return
    
    if args.enable:
        config = load_config()
        config["enabled"] = True
        save_config(config)
        print("✅ Scheduled updates ENABLED")
        return
    
    if args.disable:
        config = load_config()
        config["enabled"] = False
        save_config(config)
        print("❌ Scheduled updates DISABLED")
        return
    
    if args.status:
        config = load_config()
        print("\n📊 Scheduler Status")
        print("-"*40)
        print(f"Enabled: {'✅ Yes' if config.get('enabled') else '❌ No'}")
        print(f"Update days: {config.get('update_days', [1, 15])}")
        print(f"Last run: {config.get('last_run', 'Never')}")
        print(f"Total runs: {config.get('run_count', 0)}")
        print(f"Today is day {datetime.now().day} - {'Will run' if should_run_today(config) else 'Not scheduled'}")
        return
    
    if args.run or args.force:
        run_scheduled_update(force=args.force)
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
