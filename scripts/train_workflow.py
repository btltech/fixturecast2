#!/usr/bin/env python3
"""
Training pipeline orchestrator for GitHub Actions.
Handles model retraining, metrics collection, and notifications.
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def log_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def run_training():
    """Run the continuous training pipeline"""
    log_section("🚀 Starting Model Retraining Pipeline")

    try:
        result = subprocess.run(
            ["python", "-m", "ml_engine.continuous_training", "--no-collect", "--train"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            timeout=3600,
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        if result.returncode != 0:
            log_section("❌ Training Failed")
            return False

        log_section("✅ Training Complete")
        return True

    except subprocess.TimeoutExpired:
        log_section("❌ Training Timeout")
        return False
    except Exception as e:
        log_section(f"❌ Error: {e}")
        return False


def check_metrics():
    """Check if new metrics were generated"""
    metrics_file = os.path.join(os.path.dirname(__file__), "data", "metrics", "summary.json")

    if os.path.exists(metrics_file):
        try:
            with open(metrics_file) as f:
                metrics = json.load(f)

            log_section("📊 Training Metrics Summary")
            print(f"7-Day Accuracy: {metrics.get('7_day', {}).get('accuracy', 'N/A')}")
            print(f"30-Day Accuracy: {metrics.get('30_day', {}).get('accuracy', 'N/A')}")
            print(f"All-Time Accuracy: {metrics.get('all_time', {}).get('accuracy', 'N/A')}")

            return True
        except Exception as e:
            print(f"Could not read metrics: {e}")
            return False

    return False


def generate_summary():
    """Generate training summary"""
    log_section("📝 Training Summary")

    timestamp = datetime.now().isoformat()
    summary = {
        "timestamp": timestamp,
        "status": "completed",
        "description": "Automated weekly model retraining",
    }

    summary_file = os.path.join(os.path.dirname(__file__), "TRAINING_SUMMARY.json")

    try:
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"Summary written to {summary_file}")
        return True
    except Exception as e:
        print(f"Could not write summary: {e}")
        return False


if __name__ == "__main__":
    success = run_training()

    if success:
        check_metrics()
        generate_summary()
        sys.exit(0)
    else:
        sys.exit(1)
