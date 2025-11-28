"""
Auto-Update Results
===================
Fetches completed match results from the API and records them
in the feedback learning system for model improvement.

Run this periodically (e.g., daily via cron) to keep the system updated.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Dict, List

import requests

from ml_engine.feedback_learning import feedback_system, get_performance_report

# API configuration
BACKEND_API = os.getenv("BACKEND_API_URL", "http://localhost:8001")


def fetch_completed_fixtures(league_id: int = 39, last_n: int = 20) -> List[Dict]:
    """Fetch recently completed fixtures from the backend API"""
    try:
        url = f"{BACKEND_API}/api/results?league={league_id}&last={last_n}&season=2025"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return []


def update_results_from_api(leagues: List[int] = None) -> Dict:
    """
    Fetch completed results and update the feedback system.

    Args:
        leagues: List of league IDs to check. Defaults to major leagues.

    Returns:
        Summary of updates made
    """
    if leagues is None:
        leagues = [
            39,  # Premier League
            140,  # La Liga
            135,  # Serie A
            78,  # Bundesliga
            61,  # Ligue 1
            40,  # Championship
            2,  # Champions League
            3,  # Europa League
        ]

    # Get pending predictions
    pending = feedback_system.get_pending_results()
    pending_ids = {p["fixture_id"] for p in pending}

    if not pending_ids:
        print("No pending predictions to evaluate")
        return {"updated": 0, "pending": 0}

    print(f"Found {len(pending_ids)} pending predictions")

    updated = 0
    errors = []

    for league_id in leagues:
        print(f"\nChecking league {league_id}...")
        fixtures = fetch_completed_fixtures(league_id, last_n=30)

        for fixture in fixtures:
            fixture_id = fixture.get("fixture", {}).get("id")

            if fixture_id not in pending_ids:
                continue

            # Check if match is finished
            status = fixture.get("fixture", {}).get("status", {}).get("short")
            if status not in ["FT", "AET", "PEN"]:  # Full Time, After Extra Time, Penalties
                continue

            # Get score
            home_goals = fixture.get("goals", {}).get("home")
            away_goals = fixture.get("goals", {}).get("away")

            if home_goals is None or away_goals is None:
                continue

            # Record the result
            try:
                evaluation = feedback_system.record_result(
                    fixture_id=fixture_id,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    status=status,
                )

                if evaluation:
                    home_team = fixture.get("teams", {}).get("home", {}).get("name", "Unknown")
                    away_team = fixture.get("teams", {}).get("away", {}).get("name", "Unknown")
                    correct = "✓" if evaluation["outcome_correct"] else "✗"
                    print(f"  {correct} {home_team} {home_goals}-{away_goals} {away_team}")
                    updated += 1

            except Exception as e:
                errors.append(f"Fixture {fixture_id}: {e}")

    # Print summary
    print(f"\n{'='*50}")
    print(f"Results Update Complete")
    print(f"{'='*50}")
    print(f"Updated: {updated} predictions")
    print(f"Remaining pending: {len(pending_ids) - updated}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:5]:
            print(f"  - {err}")

    # Show current performance
    report = get_performance_report()
    overall = report.get("overall", {})
    print(f"\nOverall Performance:")
    print(f"  Accuracy: {overall.get('accuracy_pct', 'N/A')}")
    print(f"  Total evaluated: {overall.get('total', 0)}")

    # Show recent form
    recent = report.get("recent_form", {})
    if "last_10" in recent:
        r10 = recent["last_10"]
        print(f"  Last 10: {r10['correct']}/{r10['total']} ({r10['accuracy']*100:.0f}%)")

    return {"updated": updated, "pending": len(pending_ids) - updated, "errors": len(errors)}


def check_model_performance():
    """Analyze and display current model performance"""
    report = get_performance_report()

    print("\n" + "=" * 60)
    print("MODEL PERFORMANCE ANALYSIS")
    print("=" * 60)

    # Overall
    overall = report.get("overall", {})
    print(
        f"\n📊 Overall: {overall.get('accuracy_pct', 'N/A')} accuracy "
        f"({overall.get('correct', 0)}/{overall.get('total', 0)})"
    )

    # By confidence
    print("\n📈 By Confidence Level:")
    for level in ["high", "medium", "low"]:
        stats = report.get("by_confidence", {}).get(level, {})
        if stats.get("total", 0) > 0:
            print(
                f"  {level.capitalize()}: {stats.get('accuracy_pct', 'N/A')} "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # By model
    print("\n🤖 By Individual Model:")
    by_model = report.get("by_model", {})
    sorted_models = sorted(by_model.items(), key=lambda x: x[1].get("accuracy", 0), reverse=True)
    for model, stats in sorted_models:
        if stats.get("total", 0) >= 5:
            print(
                f"  {model}: {stats.get('accuracy_pct', 'N/A')} "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # By league
    print("\n🏆 By League:")
    by_league = report.get("by_league", {})
    sorted_leagues = sorted(by_league.items(), key=lambda x: x[1].get("total", 0), reverse=True)
    for league_id, stats in sorted_leagues[:5]:
        if stats.get("total", 0) > 0:
            acc = stats.get("correct", 0) / stats.get("total", 1)
            print(
                f"  {stats.get('name', league_id)}: {acc*100:.1f}% "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # Recommended weight adjustments
    recommended = feedback_system.get_recommended_weight_adjustments()
    if recommended:
        print("\n⚡ Recommended Model Weights (based on performance):")
        sorted_weights = sorted(recommended.items(), key=lambda x: x[1], reverse=True)
        for model, weight in sorted_weights:
            print(f"  {model}: {weight*100:.1f}%")

    # Recent trend
    recent = report.get("recent_form", {})
    print("\n📉 Recent Form:")
    for period, stats in recent.items():
        if stats.get("total", 0) > 0:
            trend = "📈" if stats["accuracy"] >= 0.5 else "📉"
            print(
                f"  {period.replace('_', ' ').title()}: "
                f"{stats['correct']}/{stats['total']} ({stats['accuracy']*100:.0f}%) {trend}"
            )


def export_feedback_data():
    """Export feedback data for model retraining"""
    training_data = feedback_system.export_training_data()

    if not training_data:
        print("No training data available yet")
        return None

    # Save to file
    export_path = os.path.join(
        os.path.dirname(__file__), "trained_models", "feedback", "training_export.json"
    )

    with open(export_path, "w") as f:
        json.dump(training_data, f, indent=2)

    print(f"Exported {len(training_data)} samples to {export_path}")
    return export_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update results and analyze model performance")
    parser.add_argument("--update", action="store_true", help="Fetch and update results from API")
    parser.add_argument("--analyze", action="store_true", help="Show performance analysis")
    parser.add_argument("--export", action="store_true", help="Export training data")
    parser.add_argument("--all", action="store_true", help="Run all operations")

    args = parser.parse_args()

    if args.all or (not args.update and not args.analyze and not args.export):
        # Default: run everything
        update_results_from_api()
        check_model_performance()
    else:
        if args.update:
            update_results_from_api()
        if args.analyze:
            check_model_performance()
        if args.export:
            export_feedback_data()
