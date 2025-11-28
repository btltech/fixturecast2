#!/usr/bin/env python3
"""
Weekly Backtest Script
======================
Evaluates the PREVIOUS week's trained models on matches that finished
in the past 7 days to measure real-world performance.

This runs BEFORE retraining to show how well the old model performed.
Saves results to JSON and sends notifications to Discord/Telegram.
"""

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")


def fetch_recent_finished_matches(days=7):
    """Fetch finished matches from the past N days"""
    leagues = [39, 140, 135, 78, 61, 2, 3]  # Major leagues
    all_matches = []

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    print(f"Fetching matches since {cutoff_date}...")

    for league_id in leagues:
        try:
            response = requests.get(
                f"{BACKEND_API_URL}/api/results",
                params={"league": league_id, "last": 30, "season": 2025},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            fixtures = data.get("response", [])
            for fixture in fixtures:
                match_date = fixture.get("fixture", {}).get("date", "")
                status = fixture.get("fixture", {}).get("status", {}).get("short")

                # Only include finished matches after cutoff
                if status in ["FT", "AET", "PEN"] and match_date >= cutoff_date:
                    all_matches.append(fixture)

        except Exception as e:
            print(f"Warning: Could not fetch league {league_id}: {e}")
            continue

    print(f"Found {len(all_matches)} finished matches\n")
    return all_matches


def generate_prediction_for_match(fixture):
    """Generate prediction using local trained models"""
    from backend.safe_feature_builder import build_features_for_fixture
    from ml_engine.ensemble_predictor import EnsemblePredictor

    try:
        # Build features for this match
        features = build_features_for_fixture(fixture)

        # Load trained models and predict
        predictor = EnsemblePredictor(load_trained=True)
        prediction = predictor.predict(features)

        return prediction

    except Exception as e:
        print(f"  Error generating prediction: {e}")
        return None


def evaluate_prediction(prediction, actual_home_goals, actual_away_goals):
    """Evaluate a prediction against actual result"""
    if not prediction:
        return None

    # Determine actual outcome
    if actual_home_goals > actual_away_goals:
        actual_outcome = "home_win"
    elif actual_away_goals > actual_home_goals:
        actual_outcome = "away_win"
    else:
        actual_outcome = "draw"

    # Get predicted outcome (highest probability)
    pred_probs = prediction.get("probabilities", {})
    home_prob = pred_probs.get("home_win", 0)
    draw_prob = pred_probs.get("draw", 0)
    away_prob = pred_probs.get("away_win", 0)

    if home_prob > draw_prob and home_prob > away_prob:
        predicted_outcome = "home_win"
        confidence = home_prob
    elif away_prob > draw_prob and away_prob > home_prob:
        predicted_outcome = "away_win"
        confidence = away_prob
    else:
        predicted_outcome = "draw"
        confidence = draw_prob

    # Check if prediction was correct
    correct = predicted_outcome == actual_outcome

    # Calculate profit (assuming odds based on probabilities)
    # Simple kelly criterion: bet when confidence > 60%
    bet_amount = 10 if confidence > 0.6 else 0
    implied_odds = 1 / confidence if confidence > 0 else 1
    profit = 0

    if bet_amount > 0:
        if correct:
            profit = bet_amount * (implied_odds - 1)
        else:
            profit = -bet_amount

    return {
        "correct": correct,
        "confidence": confidence,
        "predicted": predicted_outcome,
        "actual": actual_outcome,
        "profit": profit,
        "bet_amount": bet_amount,
    }


def save_backtest_metrics(summary, detailed_results):
    """Save backtest results to JSON file"""
    metrics_file = os.path.join(os.path.dirname(__file__), "..", "backend", "backtest_history.json")

    # Load existing history
    history = []
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r") as f:
                history = json.load(f)
        except:
            history = []

    # Add new entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": summary,
        "sample_size": len(detailed_results),
        "details": detailed_results[:10],  # Save first 10 for reference
    }

    history.append(entry)

    # Keep only last 52 weeks (1 year)
    history = history[-52:]

    # Save
    os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
    with open(metrics_file, "w") as f:
        json.dump(history, f, indent=2)

    print(f"✅ Metrics saved to {metrics_file}")


def send_notifications(summary):
    """Send backtest summary to Discord and Telegram"""

    # Discord webhook
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook:
        try:
            embed = {
                "title": "📊 Weekly Backtest Results",
                "description": "Performance of last week's models on recent matches",
                "color": 0x00FF00 if summary["accuracy"] >= 55 else 0xFF9900,
                "fields": [
                    {
                        "name": "🎯 Accuracy",
                        "value": f"{summary['accuracy']:.1f}% ({summary['correct']}/{summary['evaluated']})",
                        "inline": True,
                    },
                    {"name": "💰 Profit", "value": f"${summary['profit']:.2f}", "inline": True},
                    {"name": "📈 ROI", "value": f"{summary['roi']:.1f}%", "inline": True},
                ],
                "footer": {
                    "text": f"Evaluated {summary['total_matches']} matches from past 7 days"
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            payload = {"embeds": [embed]}
            response = requests.post(discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Discord notification sent")
        except Exception as e:
            print(f"⚠️ Discord notification failed: {e}")

    # Telegram notification (optional)
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_channel = os.getenv("TELEGRAM_CHANNEL_ID")

    if telegram_token and telegram_channel:
        try:
            message = (
                f"📊 <b>Weekly Backtest Results</b>\n\n"
                f"🎯 Accuracy: <b>{summary['accuracy']:.1f}%</b> ({summary['correct']}/{summary['evaluated']})\n"
                f"💰 Profit: <b>${summary['profit']:.2f}</b>\n"
                f"📈 ROI: <b>{summary['roi']:.1f}%</b>\n\n"
                f"<i>Evaluated {summary['total_matches']} matches from past 7 days</i>"
            )

            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {"chat_id": telegram_channel, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Telegram notification sent")
        except Exception as e:
            print(f"⚠️ Telegram notification failed: {e}")


def run_weekly_backtest():
    """Main backtesting function"""
    print("=" * 70)
    print("WEEKLY BACKTEST - PREVIOUS MODEL PERFORMANCE")
    print("=" * 70)
    print()

    # Fetch recent matches
    matches = fetch_recent_finished_matches(days=7)

    if not matches:
        print("No matches found to backtest.")
        return

    results = []
    total_correct = 0
    total_profit = 0.0
    total_bet = 0.0

    print("Generating predictions and evaluating...\n")

    for match in matches:
        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]
        home_goals = match["goals"]["home"]
        away_goals = match["goals"]["away"]

        print(f"  {home_team} {home_goals}-{away_goals} {away_team}")

        # Generate prediction
        prediction = generate_prediction_for_match(match)

        # Evaluate
        evaluation = evaluate_prediction(prediction, home_goals, away_goals)

        if evaluation:
            results.append(evaluation)
            if evaluation["correct"]:
                total_correct += 1
                print(
                    f"    ✅ Correct! Predicted: {evaluation['predicted']} (Confidence: {evaluation['confidence']*100:.1f}%)"
                )
            else:
                print(
                    f"    ❌ Wrong. Predicted: {evaluation['predicted']}, Actual: {evaluation['actual']}"
                )

            total_profit += evaluation["profit"]
            total_bet += evaluation["bet_amount"]

            if evaluation["profit"] != 0:
                print(f"    💰 Profit: ${evaluation['profit']:.2f}")
        else:
            print(f"    ⚠️  Could not evaluate")

    # Print summary
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY")
    print("=" * 70)

    if results:
        accuracy = (total_correct / len(results)) * 100
        print(f"\n📊 Accuracy: {accuracy:.1f}% ({total_correct}/{len(results)})")
        print(f"💰 Total Profit: ${total_profit:.2f}")
        print(f"💵 Total Wagered: ${total_bet:.2f}")

        if total_bet > 0:
            roi = (total_profit / total_bet) * 100
            print(f"📈 ROI: {roi:.1f}%")

        # Breakdown by confidence
        high_conf = [r for r in results if r["confidence"] > 0.7]
        if high_conf:
            high_correct = sum(1 for r in high_conf if r["correct"])
            print(
                f"\n🎯 High Confidence (>70%): {high_correct}/{len(high_conf)} ({high_correct/len(high_conf)*100:.1f}%)"
            )

        print()
    else:
        print("\nNo results to analyze.")

    return {
        "total_matches": len(matches),
        "evaluated": len(results),
        "correct": total_correct,
        "accuracy": accuracy if results else 0,
        "profit": total_profit,
        "roi": (total_profit / total_bet * 100) if total_bet > 0 else 0,
    }


if __name__ == "__main__":
    try:
        summary = run_weekly_backtest()

        if summary and summary.get("evaluated", 0) > 0:
            # Save metrics to file
            results_for_save = []  # Detailed results would come from run_weekly_backtest
            save_backtest_metrics(summary, results_for_save)

            # Send notifications
            send_notifications(summary)

    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
