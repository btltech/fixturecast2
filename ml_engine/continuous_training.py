#!/usr/bin/env python3
"""
Continuous Training Pipeline for FixtureCast ML Models.

This script:
1. Fetches latest match data from all supported leagues (including 2025 season)
2. Combines with existing historical data
3. Retrains all models with fresh data
4. Saves updated models

Run weekly or after significant match days to keep models current.
"""

import json
import os
import sys
import time
from datetime import datetime

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "trained_models")

# All leagues we want to train on
LEAGUES = {
    # Top 5 Leagues
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    # Additional Top Leagues
    88: "Eredivisie",
    94: "Primeira Liga",
    # Second Tier Leagues
    40: "Championship",
    141: "Segunda División",
    136: "Serie B",
    79: "2. Bundesliga",
    62: "Ligue 2",
    # European Competitions (limited historical data)
    2: "Champions League",
    3: "Europa League",
    848: "Conference League",
}

# Seasons to fetch (including current)
SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]


def fetch_league_data(client, league_id: int, seasons: list) -> list:
    """Fetch all finished matches for a league across multiple seasons."""
    all_matches = []
    league_name = LEAGUES.get(league_id, f"League {league_id}")

    for season in seasons:
        print(f"  Fetching {league_name} {season}...")
        try:
            params = {"league": league_id, "season": season, "status": "FT"}
            response = client._call_api("fixtures", params, "long")

            if response and "response" in response:
                matches = response["response"]
                all_matches.extend(matches)
                print(f"    -> {len(matches)} matches")
            else:
                print(f"    -> No data")

            # Rate limiting
            time.sleep(0.5)
        except Exception as e:
            print(f"    -> Error: {e}")

    return all_matches


def collect_all_league_data():
    """Collect data from all supported leagues."""
    from backend.api_client import ApiClient

    config_path = os.path.join(os.path.dirname(__file__), "../backend/config.json")
    with open(config_path) as f:
        config = json.load(f)

    client = ApiClient(config)

    all_matches = []

    print("\n" + "=" * 60)
    print("COLLECTING DATA FROM ALL LEAGUES")
    print("=" * 60)

    for league_id, league_name in LEAGUES.items():
        print(f"\n📊 {league_name} (ID: {league_id})")

        # For European competitions, only fetch recent seasons
        if league_id in [2, 3, 848]:
            seasons_to_fetch = [2023, 2024, 2025]
        else:
            seasons_to_fetch = SEASONS

        matches = fetch_league_data(client, league_id, seasons_to_fetch)

        if matches:
            # Save individual league file
            league_file = os.path.join(DATA_DIR, f"league_{league_id}_all.json")
            with open(league_file, "w") as f:
                json.dump(matches, f)
            print(f"  ✅ Saved {len(matches)} matches to {league_file}")

        all_matches.extend(matches)

    # Save combined dataset
    combined_file = os.path.join(DATA_DIR, "all_leagues_combined.json")
    with open(combined_file, "w") as f:
        json.dump(all_matches, f)

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_matches)} matches collected")
    print(f"Saved to: {combined_file}")
    print(f"{'='*60}\n")

    return all_matches


def retrain_all_models():
    """Retrain all ML models with the latest data."""
    print("\n" + "=" * 60)
    print("RETRAINING ALL MODELS")
    print("=" * 60 + "\n")

    # Import and run the comprehensive training script
    from ml_engine.train_all_comprehensive import train_all_models as train_main

    try:
        train_main()
        print("\n✅ All models retrained successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_continuous_training(collect_data: bool = True, train: bool = True):
    """
    Run the full continuous training pipeline.

    Args:
        collect_data: Whether to fetch fresh data from API
        train: Whether to retrain models
    """
    start_time = datetime.now()
    print(f"\n🚀 Starting Continuous Training Pipeline")
    print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Collect Data: {collect_data}")
    print(f"   Train Models: {train}")

    if collect_data:
        try:
            collect_all_league_data()
        except Exception as e:
            print(f"❌ Data collection failed: {e}")
            if train:
                print("   Continuing with existing data...")

    if train:
        success = retrain_all_models()
        if not success:
            return False

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"✅ CONTINUOUS TRAINING COMPLETE")
    print(f"   Duration: {duration:.1f} seconds")
    print(f"   Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Continuous Training Pipeline")
    parser.add_argument(
        "--no-collect", action="store_true", help="Skip data collection, use existing data"
    )
    parser.add_argument("--no-train", action="store_true", help="Skip training, only collect data")
    parser.add_argument(
        "--collect-only", action="store_true", help="Only collect data, don't train"
    )
    parser.add_argument(
        "--train-only", action="store_true", help="Only train, don't collect new data"
    )

    args = parser.parse_args()

    collect = not args.no_collect and not args.train_only
    train = not args.no_train and not args.collect_only

    success = run_continuous_training(collect_data=collect, train=train)
    sys.exit(0 if success else 1)
