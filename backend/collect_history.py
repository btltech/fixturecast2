
import json
import os
import time
from datetime import datetime
from api_client import ApiClient

# Configuration
LEAGUE_ID = 39  # Premier League
SEASONS = [2020, 2021, 2022, 2023, 2024]
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")

def collect_data():
    print(f"Starting data collection for League {LEAGUE_ID}, Seasons {SEASONS}...")
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Initialize API Client
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
        config = json.load(f)
    
    client = ApiClient(config)
    
    all_matches = []
    
    for season in SEASONS:
        print(f"\nFetching fixtures for Season {season}...")
        
        # We need ALL finished matches
        # The get_fixtures method uses 'next' or date range. 
        # We'll bypass it and call _call_api directly for better control
        params = {
            "league": LEAGUE_ID,
            "season": season,
            "status": "FT"  # Finished matches only
        }
        
        response = client._call_api("fixtures", params, "long")
        
        if not response or "response" not in response:
            print(f"Failed to fetch season {season}")
            continue
            
        matches = response["response"]
        print(f"Found {len(matches)} matches for {season}")
        
        # Save raw season data
        season_file = os.path.join(DATA_DIR, f"season_{season}.json")
        with open(season_file, "w") as f:
            json.dump(matches, f, indent=2)
            
        all_matches.extend(matches)
        
        # We also need team stats for that season to build features
        # Get unique team IDs
        team_ids = set()
        for m in matches:
            team_ids.add(m['teams']['home']['id'])
            team_ids.add(m['teams']['away']['id'])
            
        print(f"Fetching team stats for {len(team_ids)} teams in season {season}...")
        
        season_stats = {}
        for team_id in team_ids:
            # Check if we already have it cached (ApiClient handles this, but let's be explicit)
            stats = client.get_team_stats(team_id, LEAGUE_ID, season)
            if stats:
                season_stats[team_id] = stats
            time.sleep(0.2)  # Rate limiting
            
        # Save stats
        stats_file = os.path.join(DATA_DIR, f"stats_{season}.json")
        with open(stats_file, "w") as f:
            json.dump(season_stats, f, indent=2)

    print(f"\nCollection complete. Total matches: {len(all_matches)}")

if __name__ == "__main__":
    collect_data()
