#!/usr/bin/env python3
"""Local test script to exercise Discord bot helper functions.

This imports `scripts/discord_bot.py` and calls `get_todays_fixtures` and
`get_prediction` for the first fixture, printing results. Run from project
root with virtualenv activated.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Import the module functions without running the bot
import importlib.util
import sys

# Import the discord_bot module by path so we don't require 'scripts' as a package
module_path = os.path.join(os.path.dirname(__file__), "discord_bot.py")
spec = importlib.util.spec_from_file_location("discord_bot", module_path)
discord_bot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = discord_bot
spec.loader.exec_module(discord_bot)


def main():
    print("Checking backend & ML API connectivity and retrieving fixtures...")
    fixtures, motd = discord_bot.get_todays_fixtures()
    print(f"Found {len(fixtures)} fixtures today")
    if not fixtures:
        print("No fixtures returned. Stopping test.")
        return

    fixture = fixtures[0]
    fixture_id = fixture["fixture"]["id"]
    league_id = fixture["league"]["id"]
    # Defensive: ensure IDs are clean integers (strip accidental whitespace/newlines)
    try:
        fixture_id = int(str(fixture_id).strip())
        league_id = int(str(league_id).strip())
    except Exception:
        print(
            f"❌ Invalid IDs from fixtures: fixture_id={fixture['fixture']['id']} league_id={fixture['league']['id']}"
        )
        return

    print(f"Testing prediction for fixture id={fixture_id}, league={league_id}")

    prediction = discord_bot.get_prediction(fixture_id, league_id)
    if not prediction:
        print("Prediction API returned no data or an error")
        return

    print("Prediction payload keys:", list(prediction.keys()))
    # If prediction contains 'prediction' dict, show summary
    pred = prediction.get("prediction") or prediction
    print("Sample prediction summary:")
    print("  home_win_prob:", pred.get("home_win_prob"))
    print("  draw_prob:", pred.get("draw_prob"))
    print("  away_win_prob:", pred.get("away_win_prob"))
    print("  predicted_scoreline:", pred.get("predicted_scoreline"))


if __name__ == "__main__":
    main()
