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
    """Generate prediction by calling the ML API (which has all real features)"""
    try:
        fixture_id = fixture["fixture"]["id"]
        league_id = fixture["league"]["id"]

        # Call the ML API which fetches real team stats and features
        response = requests.get(
            f"{ML_API_URL}/api/prediction/{fixture_id}",
            params={"league": league_id},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        # Extract probabilities from the response
        prediction = data.get("prediction", {})

        return {
            "probabilities": {
                "home_win": prediction.get("home_win_prob", 0),
                "draw": prediction.get("draw_prob", 0),
                "away_win": prediction.get("away_win_prob", 0),
            },
            "btts_prob": prediction.get("btts_prob", 0.5),
            "over25_prob": prediction.get("over25_prob", 0.5),
            "predicted_scoreline": prediction.get("predicted_scoreline", "1-1"),
            "confidence": prediction.get("ensemble_confidence", 0),
        }

    except Exception as e:
        print(f"  Error generating prediction: {e}")
        return None


def evaluate_prediction(prediction, actual_home_goals, actual_away_goals):
    """Evaluate a prediction against actual result for ALL markets"""
    if not prediction:
        return None

    total_goals = actual_home_goals + actual_away_goals

    # ==========================================
    # MARKET 1: 1X2 (Match Result)
    # ==========================================
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

    match_result_correct = predicted_outcome == actual_outcome

    # ==========================================
    # MARKET 2: BTTS (Both Teams to Score)
    # ==========================================
    actual_btts = actual_home_goals > 0 and actual_away_goals > 0
    btts_prob = prediction.get("btts_prob", 0.5)
    predicted_btts = btts_prob > 0.5
    btts_correct = predicted_btts == actual_btts
    btts_confidence = btts_prob if predicted_btts else (1 - btts_prob)

    # ==========================================
    # MARKET 3: Over/Under 2.5 Goals
    # ==========================================
    actual_over25 = total_goals > 2.5
    over25_prob = prediction.get("over25_prob", 0.5)
    predicted_over25 = over25_prob > 0.5
    over25_correct = predicted_over25 == actual_over25
    over25_confidence = over25_prob if predicted_over25 else (1 - over25_prob)

    # ==========================================
    # MARKET 4: Correct Score
    # ==========================================
    predicted_scoreline = prediction.get("predicted_scoreline", "1-1")
    actual_scoreline = f"{actual_home_goals}-{actual_away_goals}"
    correct_score_correct = predicted_scoreline == actual_scoreline

    # Calculate profit for 1X2 market (main bet)
    bet_amount = 10 if confidence > 0.6 else 0
    implied_odds = 1 / confidence if confidence > 0 else 1
    profit = 0

    if bet_amount > 0:
        if match_result_correct:
            profit = bet_amount * (implied_odds - 1)
        else:
            profit = -bet_amount

    return {
        # 1X2 Market
        "match_result_correct": match_result_correct,
        "predicted": predicted_outcome,
        "actual": actual_outcome,
        "confidence": confidence,
        # BTTS Market
        "btts_correct": btts_correct,
        "btts_predicted": predicted_btts,
        "btts_actual": actual_btts,
        "btts_confidence": btts_confidence,
        # Over 2.5 Market
        "over25_correct": over25_correct,
        "over25_predicted": predicted_over25,
        "over25_actual": actual_over25,
        "over25_confidence": over25_confidence,
        # Correct Score Market
        "correct_score_correct": correct_score_correct,
        "predicted_scoreline": predicted_scoreline,
        "actual_scoreline": actual_scoreline,
        # Profit tracking (for 1X2)
        "profit": profit,
        "bet_amount": bet_amount,
        # Legacy field for compatibility
        "correct": match_result_correct,
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
            # Color based on overall 1X2 accuracy
            color = 0x00FF00 if summary["accuracy"] >= 55 else 0xFF9900

            embed = {
                "title": "📊 Weekly Backtest Results - All Markets",
                "description": "Performance of last week's models on recent matches",
                "color": color,
                "fields": [
                    {
                        "name": "🏆 Match Result (1X2)",
                        "value": f"{summary['accuracy']:.1f}% ({summary['correct']}/{summary['evaluated']})",
                        "inline": True,
                    },
                    {
                        "name": "⚽ Both Teams Score",
                        "value": f"{summary.get('btts_accuracy', 0):.1f}% ({summary.get('btts_correct', 0)}/{summary['evaluated']})",
                        "inline": True,
                    },
                    {
                        "name": "📈 Over/Under 2.5",
                        "value": f"{summary.get('over25_accuracy', 0):.1f}% ({summary.get('over25_correct', 0)}/{summary['evaluated']})",
                        "inline": True,
                    },
                    {
                        "name": "🎯 Correct Score",
                        "value": f"{summary.get('correct_score_accuracy', 0):.1f}% ({summary.get('correct_score_correct', 0)}/{summary['evaluated']})",
                        "inline": True,
                    },
                    {"name": "💰 Profit", "value": f"${summary['profit']:.2f}", "inline": True},
                    {"name": "📊 ROI", "value": f"{summary['roi']:.1f}%", "inline": True},
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
                f"📊 <b>Weekly Backtest Results - All Markets</b>\n\n"
                f"🏆 <b>Match Result (1X2):</b> {summary['accuracy']:.1f}% ({summary['correct']}/{summary['evaluated']})\n"
                f"⚽ <b>Both Teams Score:</b> {summary.get('btts_accuracy', 0):.1f}% ({summary.get('btts_correct', 0)}/{summary['evaluated']})\n"
                f"📈 <b>Over/Under 2.5:</b> {summary.get('over25_accuracy', 0):.1f}% ({summary.get('over25_correct', 0)}/{summary['evaluated']})\n"
                f"🎯 <b>Correct Score:</b> {summary.get('correct_score_accuracy', 0):.1f}% ({summary.get('correct_score_correct', 0)}/{summary['evaluated']})\n\n"
                f"💰 Profit: <b>${summary['profit']:.2f}</b>\n"
                f"📊 ROI: <b>{summary['roi']:.1f}%</b>\n\n"
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

    print(f"Using ML API at: {ML_API_URL}")
    print("Predictions will use real team stats and features\n")

    results = []

    # Track all 4 markets
    match_result_correct = 0
    btts_correct = 0
    over25_correct = 0
    correct_score_correct = 0

    total_profit = 0.0
    total_bet = 0.0

    print("Generating predictions and evaluating...\n")

    for match in matches:
        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]
        home_goals = match["goals"]["home"]
        away_goals = match["goals"]["away"]

        print(f"  {home_team} {home_goals}-{away_goals} {away_team}")

        # Generate prediction via ML API (which fetches real features)
        prediction = generate_prediction_for_match(match)

        # Evaluate
        evaluation = evaluate_prediction(prediction, home_goals, away_goals)

        if evaluation:
            results.append(evaluation)

            # Track 1X2 (Match Result)
            if evaluation["match_result_correct"]:
                match_result_correct += 1
                print(
                    f"    ✅ 1X2: Correct! Predicted: {evaluation['predicted']} (Confidence: {evaluation['confidence']*100:.1f}%)"
                )
            else:
                print(
                    f"    ❌ 1X2: Wrong. Predicted: {evaluation['predicted']}, Actual: {evaluation['actual']}"
                )

            # Track BTTS
            if evaluation["btts_correct"]:
                btts_correct += 1
                btts_pred = "Yes" if evaluation["btts_predicted"] else "No"
                print(f"    ✅ BTTS: Correct! Predicted: {btts_pred}")
            else:
                btts_pred = "Yes" if evaluation["btts_predicted"] else "No"
                btts_act = "Yes" if evaluation["btts_actual"] else "No"
                print(f"    ❌ BTTS: Wrong. Predicted: {btts_pred}, Actual: {btts_act}")

            # Track Over 2.5
            if evaluation["over25_correct"]:
                over25_correct += 1
                over_pred = "Over" if evaluation["over25_predicted"] else "Under"
                print(f"    ✅ O/U 2.5: Correct! Predicted: {over_pred}")
            else:
                over_pred = "Over" if evaluation["over25_predicted"] else "Under"
                over_act = "Over" if evaluation["over25_actual"] else "Under"
                print(f"    ❌ O/U 2.5: Wrong. Predicted: {over_pred}, Actual: {over_act}")

            # Track Correct Score
            if evaluation["correct_score_correct"]:
                correct_score_correct += 1
                print(f"    🎯 SCORE: Correct! Predicted: {evaluation['predicted_scoreline']}")
            else:
                print(
                    f"    ❌ SCORE: Wrong. Predicted: {evaluation['predicted_scoreline']}, Actual: {evaluation['actual_scoreline']}"
                )

            total_profit += evaluation["profit"]
            total_bet += evaluation["bet_amount"]

            if evaluation["profit"] != 0:
                print(f"    💰 Profit: ${evaluation['profit']:.2f}")
            print()  # Blank line between matches
        else:
            print(f"    ⚠️  Could not evaluate\n")

    # Print summary
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY - ALL MARKETS")
    print("=" * 70)

    if results:
        n = len(results)

        # Calculate accuracy for each market
        mr_accuracy = (match_result_correct / n) * 100
        btts_accuracy = (btts_correct / n) * 100
        over25_accuracy = (over25_correct / n) * 100
        cs_accuracy = (correct_score_correct / n) * 100

        print(f"\n📊 ACCURACY BY MARKET (out of {n} matches):")
        print(f"   🏆 Match Result (1X2): {mr_accuracy:.1f}% ({match_result_correct}/{n})")
        print(f"   ⚽ Both Teams to Score: {btts_accuracy:.1f}% ({btts_correct}/{n})")
        print(f"   📈 Over/Under 2.5 Goals: {over25_accuracy:.1f}% ({over25_correct}/{n})")
        print(f"   🎯 Correct Score: {cs_accuracy:.1f}% ({correct_score_correct}/{n})")

        print(f"\n💰 Total Profit (1X2 bets): ${total_profit:.2f}")
        print(f"💵 Total Wagered: ${total_bet:.2f}")

        roi = 0
        if total_bet > 0:
            roi = (total_profit / total_bet) * 100
            print(f"📈 ROI: {roi:.1f}%")

        # Breakdown by confidence for 1X2
        high_conf = [r for r in results if r["confidence"] > 0.7]
        if high_conf:
            high_correct = sum(1 for r in high_conf if r["match_result_correct"])
            print(
                f"\n🎯 High Confidence 1X2 (>70%): {high_correct}/{len(high_conf)} ({high_correct/len(high_conf)*100:.1f}%)"
            )

        print()

        return {
            "total_matches": len(matches),
            "evaluated": n,
            # 1X2 Market
            "correct": match_result_correct,
            "accuracy": mr_accuracy,
            # BTTS Market
            "btts_correct": btts_correct,
            "btts_accuracy": btts_accuracy,
            # Over 2.5 Market
            "over25_correct": over25_correct,
            "over25_accuracy": over25_accuracy,
            # Correct Score Market
            "correct_score_correct": correct_score_correct,
            "correct_score_accuracy": cs_accuracy,
            # Profit
            "profit": total_profit,
            "roi": roi,
        }
    else:
        print("\nNo results to analyze.")
        return {
            "total_matches": len(matches),
            "evaluated": 0,
            "correct": 0,
            "accuracy": 0,
            "btts_correct": 0,
            "btts_accuracy": 0,
            "over25_correct": 0,
            "over25_accuracy": 0,
            "correct_score_correct": 0,
            "correct_score_accuracy": 0,
            "profit": 0,
            "roi": 0,
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
