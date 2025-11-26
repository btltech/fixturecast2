"""
Retrain Models with Feedback
============================
Uses feedback from actual results to:
1. Adjust ensemble weights based on model performance
2. Fine-tune models with new data
3. Update Elo ratings with actual outcomes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime

from ml_engine.elo_tracker import EloTracker
from ml_engine.feedback_learning import (
    feedback_system,
    get_performance_report,
    get_recommended_weights,
)

# Paths
MODELS_DIR = os.path.join(os.path.dirname(__file__), "trained_models")
WEIGHTS_FILE = os.path.join(MODELS_DIR, "ensemble_weights.json")


def update_ensemble_weights(min_samples: int = 20):
    """
    Update ensemble weights based on actual prediction performance.

    Args:
        min_samples: Minimum predictions needed before adjusting weights

    Returns:
        New weights dict or None if not enough data
    """
    report = get_performance_report()
    total = report.get("overall", {}).get("total", 0)

    if total < min_samples:
        print(f"Not enough data for weight adjustment (have {total}, need {min_samples})")
        return None

    recommended = get_recommended_weights()

    if not recommended:
        print("No recommended weights available yet")
        return None

    # Current default weights
    current_weights = {
        "gbdt": 0.30,
        "elo": 0.30,
        "gnn": 0.20,
        "lstm": 0.10,
        "bayesian": 0.05,
        "transformer": 0.03,
        "catboost": 0.02,
    }

    # Blend current with recommended (gradual adjustment)
    # Use 70% current, 30% recommended for stability
    blend_ratio = 0.3
    new_weights = {}

    for model in current_weights:
        current = current_weights.get(model, 0)
        recommended_val = recommended.get(model, current)
        new_weights[model] = current * (1 - blend_ratio) + recommended_val * blend_ratio

    # Normalize to sum to 1.0
    total_weight = sum(new_weights.values())
    new_weights = {k: v / total_weight for k, v in new_weights.items()}

    # Save new weights
    weight_data = {
        "weights": new_weights,
        "updated_at": datetime.now().isoformat(),
        "based_on_samples": total,
        "previous_weights": current_weights,
        "recommended_weights": recommended,
    }

    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weight_data, f, indent=2)

    print("New ensemble weights saved:")
    for model, weight in sorted(new_weights.items(), key=lambda x: -x[1]):
        change = new_weights[model] - current_weights.get(model, 0)
        change_str = f"+{change:.1%}" if change > 0 else f"{change:.1%}"
        print(f"  {model}: {weight:.1%} ({change_str})")

    return new_weights


def update_elo_from_feedback():
    """
    Update Elo ratings using actual match results from feedback.
    """
    elo_tracker = EloTracker()

    # Get evaluated predictions with results
    training_data = feedback_system.export_training_data()

    if not training_data:
        print("No feedback data available for Elo updates")
        return

    # Sort by date (if available) to maintain chronological order
    # For now, just process all results

    updates = 0
    for match in training_data:
        home_team = match["home_team"]
        away_team = match["away_team"]
        home_goals = match["home_goals"]
        away_goals = match["away_goals"]

        # Determine result
        if home_goals > away_goals:
            result = "home"
        elif away_goals > home_goals:
            result = "away"
        else:
            result = "draw"

        # Update Elo (this handles duplicates internally via match history)
        try:
            elo_tracker.update_ratings(home_team, away_team, result)
            updates += 1
        except Exception as e:
            print(f"Error updating Elo for {home_team} vs {away_team}: {e}")

    # Save updated ratings
    elo_tracker.save_ratings()

    print(f"Updated Elo ratings with {updates} match results")

    # Show top teams
    print("\nTop 10 teams by Elo:")
    sorted_teams = sorted(elo_tracker.ratings.items(), key=lambda x: x[1], reverse=True)[:10]

    for rank, (team, rating) in enumerate(sorted_teams, 1):
        print(f"  {rank}. {team}: {rating:.0f}")


def generate_performance_report():
    """Generate and display a detailed performance report"""
    report = get_performance_report()

    print("\n" + "=" * 70)
    print("FEEDBACK LEARNING PERFORMANCE REPORT")
    print("=" * 70)

    # Overall
    overall = report.get("overall", {})
    print(f"\n📊 OVERALL PERFORMANCE")
    print(f"   Total predictions evaluated: {overall.get('total', 0)}")
    print(f"   Accuracy: {overall.get('accuracy_pct', 'N/A')}")
    print(f"   Correct: {overall.get('correct', 0)}")

    # By confidence
    print(f"\n📈 BY CONFIDENCE LEVEL")
    for level in ["high", "medium", "low"]:
        stats = report.get("by_confidence", {}).get(level, {})
        if stats.get("total", 0) > 0:
            print(
                f"   {level.upper()}: {stats.get('accuracy_pct', 'N/A')} "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # By model
    print(f"\n🤖 BY MODEL PERFORMANCE")
    by_model = report.get("by_model", {})
    sorted_models = sorted(by_model.items(), key=lambda x: x[1].get("accuracy", 0), reverse=True)
    for model, stats in sorted_models:
        if stats.get("total", 0) >= 3:
            print(
                f"   {model}: {stats.get('accuracy_pct', 'N/A')} "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # By league
    print(f"\n🏆 BY LEAGUE")
    by_league = report.get("by_league", {})
    sorted_leagues = sorted(by_league.items(), key=lambda x: x[1].get("total", 0), reverse=True)[:5]
    for league_id, stats in sorted_leagues:
        if stats.get("total", 0) > 0:
            acc = stats.get("correct", 0) / stats.get("total", 1)
            print(
                f"   {stats.get('name', league_id)}: {acc*100:.1f}% "
                f"({stats.get('correct', 0)}/{stats.get('total', 0)})"
            )

    # Recent form
    print(f"\n📉 RECENT FORM")
    recent = report.get("recent_form", {})
    for period, stats in sorted(recent.items()):
        if stats.get("total", 0) > 0:
            acc = stats["accuracy"]
            emoji = "🟢" if acc >= 0.55 else "🟡" if acc >= 0.45 else "🔴"
            print(
                f"   {emoji} {period.replace('_', ' ').title()}: "
                f"{stats['correct']}/{stats['total']} ({acc*100:.0f}%)"
            )

    # Calibration
    print(f"\n🎯 CALIBRATION (predicted vs actual)")
    calibration = report.get("calibration", {})
    for bin_key, stats in sorted(calibration.items()):
        if stats.get("count", 0) >= 3:
            pred = stats["avg_predicted"] * 100
            actual = stats["avg_actual"] * 100
            error = stats["calibration_error"] * 100
            symbol = "✓" if error < 10 else "⚠️"
            print(
                f"   {bin_key}%: predicted {pred:.0f}% → actual {actual:.0f}% "
                f"(error: {error:.0f}%) {symbol}"
            )


def main():
    """Run the feedback-based model improvement pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="Retrain models using feedback data")
    parser.add_argument("--weights", action="store_true", help="Update ensemble weights")
    parser.add_argument("--elo", action="store_true", help="Update Elo ratings")
    parser.add_argument("--report", action="store_true", help="Show performance report")
    parser.add_argument("--all", action="store_true", help="Run all updates")
    parser.add_argument(
        "--min-samples", type=int, default=20, help="Minimum samples for weight adjustment"
    )

    args = parser.parse_args()

    if args.all or (not args.weights and not args.elo and not args.report):
        args.weights = True
        args.elo = True
        args.report = True

    if args.report:
        generate_performance_report()

    if args.weights:
        print("\n" + "=" * 50)
        print("UPDATING ENSEMBLE WEIGHTS")
        print("=" * 50)
        update_ensemble_weights(min_samples=args.min_samples)

    if args.elo:
        print("\n" + "=" * 50)
        print("UPDATING ELO RATINGS")
        print("=" * 50)
        update_elo_from_feedback()

    print("\n✅ Feedback-based improvements complete!")


if __name__ == "__main__":
    main()
