
import sys
import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

# Add root to path to allow importing ml_engine as a package
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ensemble_predictor import EnsemblePredictor
from api_client import ApiClient
from safe_feature_builder import FeatureBuilder
from analysis_llm import AnalysisLLM

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://switchyard.proxy.rlwy.net:33204",
        "*"  # Allow all for now, restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Config
with open(os.path.join(os.path.dirname(__file__), 'config.json')) as f:
    config = json.load(f)

api_client = ApiClient(config)
feature_builder = FeatureBuilder()
predictor = EnsemblePredictor()
analyzer = AnalysisLLM()

# Load ML artifacts (mock)
predictor.load_artifacts("ml_engine/artifacts")

@app.get("/")
def read_root():
    return {"status": "FixtureCast Backend Running", "mode": "API-Football Live Data"}

@app.get("/api/status")
def get_api_status():
    """
    Get API-Football quota status.
    Returns requests used today, limit, and remaining.
    """
    return api_client.get_api_status()

@app.get("/api/fixtures")
def get_fixtures(league: int, season: int = 2025, next: int = 10):
    if league not in config["allowed_competitions"]:
        raise HTTPException(status_code=400, detail="League not allowed")
    return api_client.get_fixtures(league_id=league, season=season, next_n=next)

@app.get("/api/teams")
def get_teams(league: int, season: int = 2025):
    if league not in config["allowed_competitions"]:
        raise HTTPException(status_code=400, detail="League not allowed")
    return api_client.get_teams(league_id=league, season=season)

@app.get("/api/team/{team_id}")
def get_team_details(team_id: int, league: int, season: int = 2025):
    # Fetch team details, stats, recent fixtures
    team_info = api_client.get_teams(league_id=league, season=season) # This returns list, need to filter or use specific endpoint if available, but best practice says use bulk.
    # We will filter from bulk for the basic info
    target_team = None
    if "response" in team_info:
        for t in team_info["response"]:
            if t["team"]["id"] == team_id:
                target_team = t
                break
    
    if target_team is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found in league {league}")
    
    stats = api_client.get_team_stats(team_id, league, season)
    last_fixtures = api_client.get_last_fixtures(team_id, league, season, last=10)
    
    return {
        "team": target_team,
        "stats": stats,
        "recent_fixtures": last_fixtures
    }

@app.get("/api/prediction/{fixture_id}")
def get_prediction(fixture_id: int, league: int, season: int = 2025):
    """
    Generate a comprehensive ML prediction for a fixture.
    Fetches data from 24+ API endpoints and extracts 80+ features.
    Now with competition-type awareness for UCL/UEL knockouts vs domestic leagues.
    """
    # 1. Fetch core data (original 10 calls)
    fixture_details = api_client.get_fixture_details(fixture_id)
    
    if not fixture_details['response']:
        raise HTTPException(status_code=404, detail="Fixture not found")
        
    home_id = fixture_details['response'][0]['teams']['home']['id']
    away_id = fixture_details['response'][0]['teams']['away']['id']
    
    standings = api_client.get_standings(league, season)
    home_last_10 = api_client.get_last_fixtures(home_id, league, season, last=10)
    away_last_10 = api_client.get_last_fixtures(away_id, league, season, last=10)
    home_stats = api_client.get_team_stats(home_id, league, season)
    away_stats = api_client.get_team_stats(away_id, league, season)
    h2h = api_client.get_h2h(home_id, away_id)
    home_injuries = api_client.get_injuries(home_id, season)
    away_injuries = api_client.get_injuries(away_id, season)
    odds = api_client.get_odds(fixture_id)
    
    # 2. Fetch enhanced data (new 5 calls for richer predictions)
    home_players = api_client.get_players(home_id, season)
    away_players = api_client.get_players(away_id, season)
    home_coach = api_client.get_coach(home_id)
    away_coach = api_client.get_coach(away_id)
    
    # Get fixture IDs from recent matches for detailed stats
    home_fixture_ids = [f['fixture']['id'] for f in home_last_10.get('response', [])[:5]]
    away_fixture_ids = [f['fixture']['id'] for f in away_last_10.get('response', [])[:5]]
    home_recent_stats = api_client.get_recent_fixture_stats(home_fixture_ids)
    away_recent_stats = api_client.get_recent_fixture_stats(away_fixture_ids)
    
    # 3. Get competition metadata for type-aware predictions
    competition_info = api_client.get_competition_info(league)
    round_info = api_client.get_fixture_round(fixture_id) if competition_info.get("type") == "european_cup" else None
    
    # 4. Build Features (now with 80+ features including competition-type)
    features = feature_builder.build_features(
        fixture_details, standings, home_last_10, away_last_10, 
        home_stats, away_stats, h2h, home_injuries, away_injuries, odds,
        home_players=home_players,
        away_players=away_players,
        home_coach=home_coach,
        away_coach=away_coach,
        home_recent_stats=home_recent_stats,
        away_recent_stats=away_recent_stats,
        competition_info=competition_info,
        round_info=round_info
    )
    
    # 5. Predict
    prediction = predictor.predict_fixture(features)
    
    # 6. Generate AI Analysis - enrich features with Elo, rank, competition data
    elo_ratings = prediction.get('elo_ratings', {})
    enriched_features = {
        **features,
        'home_elo': elo_ratings.get('home', 1500),
        'away_elo': elo_ratings.get('away', 1500),
        'home_rank': features.get('home_league_pos', 10),
        'away_rank': features.get('away_league_pos', 10),
        'competition_name': competition_info.get('name', 'Unknown'),
        'competition_type': competition_info.get('type', 'domestic_league'),
    }
    analysis = analyzer.analyze(prediction, enriched_features)
    
    return {
        "fixture_id": fixture_id,
        "prediction": prediction,
        "analysis": analysis,
        "fixture_details": fixture_details['response'][0] if fixture_details.get('response') else {},
        "features": features,  # Return features for debugging
        "competition_info": competition_info  # Include competition metadata
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting FixtureCast Backend API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
