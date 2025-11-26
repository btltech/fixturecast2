#!/usr/bin/env python3
"""
Collect historical match data from multiple top European leagues.
This will significantly expand the training dataset for ML models.
"""

import json
import os
import time
from datetime import datetime

from api_client import ApiClient

# Top European Leagues
LEAGUES = {
    39: "Premier League (England)",
    140: "La Liga (Spain)",
    135: "Serie A (Italy)",
    78: "Bundesliga (Germany)",
    61: "Ligue 1 (France)",
    40: "Championship (England)",
}

SEASONS = [2020, 2021, 2022, 2023, 2024]
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")


def collect_all_leagues():
    """Collect historical data from all configured leagues."""
    print("=" * 60)
    print("MULTI-LEAGUE HISTORICAL DATA COLLECTION")
    print(f"Leagues: {len(LEAGUES)}")
    print(f"Seasons: {SEASONS}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Initialize API Client
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
        config = json.load(f)

    client = ApiClient(config)

    # Track totals
    total_matches = 0
    league_summary = {}

    for league_id, league_name in LEAGUES.items():
        print(f"\n{'='*60}")
        print(f"LEAGUE: {league_name} (ID: {league_id})")
        print("=" * 60)

        league_matches = []
        league_stats = {}

        for season in SEASONS:
            print(f"\n  Season {season}...")

            # Fetch all finished matches
            params = {
                "league": league_id,
                "season": season,
                "status": "FT",  # Finished matches only
            }

            response = client._call_api("fixtures", params, "long")

            if not response or "response" not in response:
                print(f"    ❌ Failed to fetch season {season}")
                continue

            matches = response["response"]
            match_count = len(matches)
            print(f"    ✓ Found {match_count} matches")

            # Add league_id to each match for training
            for m in matches:
                m["league_id"] = league_id
                m["league_name"] = league_name

            league_matches.extend(matches)

            # Small delay to respect rate limits
            time.sleep(0.3)

        # Save league data
        league_file = os.path.join(DATA_DIR, f"league_{league_id}_all.json")
        with open(league_file, "w") as f:
            json.dump(league_matches, f, indent=2)

        league_summary[league_name] = len(league_matches)
        total_matches += len(league_matches)
        print(f"\n  Total for {league_name}: {len(league_matches)} matches")

    # Create combined dataset for training
    print("\n" + "=" * 60)
    print("COMBINING ALL LEAGUES INTO UNIFIED DATASET")
    print("=" * 60)

    all_matches = []
    for league_id in LEAGUES.keys():
        league_file = os.path.join(DATA_DIR, f"league_{league_id}_all.json")
        if os.path.exists(league_file):
            with open(league_file, "r") as f:
                matches = json.load(f)
                all_matches.extend(matches)

    # Save combined dataset
    combined_file = os.path.join(DATA_DIR, "all_leagues_combined.json")
    with open(combined_file, "w") as f:
        json.dump(all_matches, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("COLLECTION SUMMARY")
    print("=" * 60)
    for league, count in league_summary.items():
        print(f"  {league}: {count} matches")
    print("-" * 40)
    print(f"  TOTAL: {total_matches} matches")
    print(f"\nCombined file: {combined_file}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return total_matches


if __name__ == "__main__":
    collect_all_leagues()
