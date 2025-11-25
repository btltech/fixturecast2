#!/usr/bin/env python3
"""
FastAPI server for FixtureCast ML predictions.
Exposes endpoints to get match predictions using the trained ensemble.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
from collections import defaultdict
from datetime import datetime
import json
import sys
import os

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ensemble_predictor import EnsemblePredictor
from ml_engine.feedback_learning import log_prediction as log_feedback_prediction

app = FastAPI(
    title="FixtureCast ML API",
    description="Machine Learning powered football match prediction API",
    version="1.2.0"
)

# ============================================
# PREDICTION STATISTICS TRACKING
# ============================================
STATS_FILE = os.path.join(os.path.dirname(__file__), "prediction_stats.json")

class PredictionStatsTracker:
    """Tracks prediction statistics for model performance monitoring"""
    
    # Model metadata for display
    MODEL_METADATA = {
        "gnn": {
            "full_name": "Graph Neural Network",
            "description": "Analyzes team relationships and league context through graph-based learning",
            "type": "Deep Learning"
        },
        "elo": {
            "full_name": "Elo-Glicko Rating",
            "description": "Chess-inspired rating system adapted for football team strength",
            "type": "Statistical"
        },
        "lstm": {
            "full_name": "Long Short-Term Memory",
            "description": "Captures sequential patterns in team form and momentum",
            "type": "Deep Learning"
        },
        "gbdt": {
            "full_name": "Gradient Boosted Decision Trees",
            "description": "Ensemble of decision trees for robust feature-based predictions",
            "type": "Machine Learning"
        },
        "bayesian": {
            "full_name": "Bayesian Inference",
            "description": "Probabilistic model incorporating betting odds and prior knowledge",
            "type": "Statistical"
        },
        "transformer": {
            "full_name": "Transformer Network",
            "description": "Attention-based model analyzing complex feature interactions",
            "type": "Deep Learning"
        },
        "catboost": {
            "full_name": "CatBoost",
            "description": "Gradient boosting with native handling of categorical features",
            "type": "Machine Learning"
        },
        "poisson": {
            "full_name": "Poisson Distribution",
            "description": "Models expected goals using Poisson probability distribution",
            "type": "Statistical"
        },
        "monte_carlo": {
            "full_name": "Monte Carlo Simulation",
            "description": "Simulates thousands of match outcomes for scoreline prediction",
            "type": "Simulation"
        }
    }
    
    # Ensemble weights from the predictor (MUST match ensemble_predictor.py)
    ENSEMBLE_WEIGHTS = {
        "gbdt": 0.30,
        "elo": 0.30,
        "gnn": 0.20,
        "lstm": 0.10,
        "bayesian": 0.05,
        "transformer": 0.03,
        "catboost": 0.02,
        "monte_carlo": 0.00  # Auxiliary - used for scoreline
    }
    
    def __init__(self):
        self.stats = {
            "total_predictions": 0,
            "predictions_by_model": defaultdict(int),
            "confidence_sums": defaultdict(float),
            "confidence_counts": defaultdict(int),
            "predictions_log": [],
            "started_at": datetime.now().isoformat(),
            "last_prediction_at": None
        }
        self._load_stats()
    
    def _load_stats(self):
        """Load stats from file if exists"""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f:
                    loaded = json.load(f)
                    self.stats["total_predictions"] = loaded.get("total_predictions", 0)
                    self.stats["predictions_by_model"] = defaultdict(int, loaded.get("predictions_by_model", {}))
                    self.stats["confidence_sums"] = defaultdict(float, loaded.get("confidence_sums", {}))
                    self.stats["confidence_counts"] = defaultdict(int, loaded.get("confidence_counts", {}))
                    self.stats["predictions_log"] = loaded.get("predictions_log", [])[-100:]
                    self.stats["started_at"] = loaded.get("started_at", datetime.now().isoformat())
                    self.stats["last_prediction_at"] = loaded.get("last_prediction_at")
                    print(f"Loaded prediction stats: {self.stats['total_predictions']} total predictions")
            except Exception as e:
                print(f"Could not load stats: {e}")
    
    def _save_stats(self):
        """Persist stats to file"""
        try:
            save_data = {
                "total_predictions": self.stats["total_predictions"],
                "predictions_by_model": dict(self.stats["predictions_by_model"]),
                "confidence_sums": dict(self.stats["confidence_sums"]),
                "confidence_counts": dict(self.stats["confidence_counts"]),
                "predictions_log": self.stats["predictions_log"][-100:],
                "started_at": self.stats["started_at"],
                "last_prediction_at": self.stats["last_prediction_at"]
            }
            with open(STATS_FILE, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            print(f"Could not save stats: {e}")
    
    def record_prediction(self, model_breakdown: dict, ensemble_confidence: float):
        """Record a new prediction"""
        self.stats["total_predictions"] += 1
        self.stats["last_prediction_at"] = datetime.now().isoformat()
        
        # Track per-model confidence
        for model_name, preds in model_breakdown.items():
            self.stats["predictions_by_model"][model_name] += 1
            if isinstance(preds, dict) and "home_win" in preds:
                max_conf = max(preds.get("home_win", 0), preds.get("draw", 0), preds.get("away_win", 0))
                self.stats["confidence_sums"][model_name] += max_conf
                self.stats["confidence_counts"][model_name] += 1
        
        # Log prediction
        self.stats["predictions_log"].append({
            "timestamp": datetime.now().isoformat(),
            "ensemble_confidence": round(ensemble_confidence, 4)
        })
        
        # Keep only last 100 logs
        if len(self.stats["predictions_log"]) > 100:
            self.stats["predictions_log"] = self.stats["predictions_log"][-100:]
        
        # Persist every 5 predictions
        if self.stats["total_predictions"] % 5 == 0:
            self._save_stats()
    
    def get_model_stats(self) -> dict:
        """Get formatted statistics for all models"""
        models = []
        
        for model_name, weight in self.ENSEMBLE_WEIGHTS.items():
            metadata = self.MODEL_METADATA.get(model_name, {})
            pred_count = self.stats["predictions_by_model"].get(model_name, 0)
            
            # Calculate average confidence
            conf_sum = self.stats["confidence_sums"].get(model_name, 0)
            conf_count = self.stats["confidence_counts"].get(model_name, 0)
            avg_confidence = round(conf_sum / conf_count, 4) if conf_count > 0 else 0.0
            
            models.append({
                "name": model_name,
                "full_name": metadata.get("full_name", model_name.upper()),
                "description": metadata.get("description", ""),
                "type": metadata.get("type", "Unknown"),
                "weight": weight,
                "predictions": pred_count,
                "avg_confidence": avg_confidence,
                "status": "active" if weight > 0 else "auxiliary"
            })
        
        # Sort by weight (highest first)
        models.sort(key=lambda x: x["weight"], reverse=True)
        
        # Calculate ensemble-level stats
        total_preds = self.stats["total_predictions"]
        
        # Average ensemble confidence from recent predictions
        recent_logs = self.stats["predictions_log"][-50:]
        avg_ensemble_conf = (
            round(sum(log["ensemble_confidence"] for log in recent_logs) / len(recent_logs), 4)
            if recent_logs else 0.0
        )
        
        return {
            "ensemble_accuracy": None,  # Real accuracy requires outcome validation (coming soon)
            "total_predictions": total_preds,
            "avg_ensemble_confidence": avg_ensemble_conf,
            "models": models,
            "tracking_since": self.stats["started_at"],
            "last_prediction": self.stats["last_prediction_at"],
            "note": "Accuracy metrics require outcome validation which is coming in a future update."
        }

# Initialize stats tracker
stats_tracker = PredictionStatsTracker()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictor once at startup (loads trained models)
from api_client import ApiClient
from safe_feature_builder import FeatureBuilder
from analysis_llm import AnalysisLLM
import json

# Initialize components
predictor = None
api_client = None
feature_builder = FeatureBuilder()
analysis_llm = AnalysisLLM()

@app.on_event("startup")
async def startup_event():
    global predictor, api_client
    print("Loading ML models...")
    predictor = EnsemblePredictor(load_trained=True)
    print("ML models loaded successfully!")
    
    # Initialize API Client
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path) as f:
            config = json.load(f)
        api_client = ApiClient(config)
        print("API Client initialized! Enhanced feature set (24 API calls per prediction)")
    except Exception as e:
        print(f"Warning: Failed to initialize API Client: {e}")

class MatchFeatures(BaseModel):
    """Feature dict for a single match prediction"""
    home_id: int
    away_id: int
    home_name: str
    away_name: str
    home_league_points: float = 30
    away_league_points: float = 30
    home_league_pos: int = 10
    away_league_pos: int = 10
    home_points_last10: float = 15
    away_points_last10: float = 15
    home_form_last5: float = 7
    away_form_last5: float = 7
    home_goals_for_avg: float = 1.3
    away_goals_for_avg: float = 1.2
    home_goals_against_avg: float = 1.2
    away_goals_against_avg: float = 1.3
    home_wins_last10: int = 5
    away_wins_last10: int = 5
    home_draws_last10: int = 3
    away_draws_last10: int = 3
    home_losses_last10: int = 2
    away_losses_last10: int = 2
    home_goals_for_last10: int = 13
    away_goals_for_last10: int = 12
    home_goals_against_last10: int = 12
    away_goals_against_last10: int = 13
    h2h_home_wins: int = 2
    h2h_draws: int = 2
    h2h_away_wins: int = 2
    h2h_total_matches: int = 6
    home_clean_sheets: int = 3
    away_clean_sheets: int = 3
    home_total_matches: int = 20
    away_total_matches: int = 20
    # Optional odds data
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    odds_available: bool = False

class PredictionResponse(BaseModel):
    """Response containing match prediction"""
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_scoreline: str
    btts_prob: float
    over25_prob: float
    model_breakdown: Dict
    scoreline_distribution: Optional[Dict] = None

@app.get("/")
async def root():
    return {
        "service": "FixtureCast ML API",
        "version": "1.0.0",
        "status": "running",
        "models_loaded": predictor is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": predictor is not None
    }

@app.get("/api/prediction/{fixture_id}")
async def predict_fixture(fixture_id: int, league: int = 39, season: int = 2025):
    """
    Get prediction for a specific fixture ID.
    Fetches real data, builds features, and runs prediction.
    Now with competition-type awareness for UCL/UEL knockouts vs domestic leagues.
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    if api_client is None:
        raise HTTPException(status_code=503, detail="API Client not initialized")

    try:
        # 1. Fetch Fixture Details directly by ID
        fixture_response = api_client.get_fixture_details(fixture_id)
        
        if not fixture_response or not fixture_response.get('response'):
            raise HTTPException(status_code=404, detail="Fixture not found")
            
        fixture = fixture_response['response'][0]
        
        # Auto-detect league from fixture if not explicitly provided or default
        actual_league = fixture.get('league', {}).get('id', league)
        if actual_league and actual_league != league:
            print(f"Auto-detected league {actual_league} from fixture (param was {league})")
            league = actual_league
        
        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']
        
        # 2. Fetch other required data
        standings = api_client.get_standings(league, season)
        home_stats = api_client.get_team_stats(home_id, league, season)
        away_stats = api_client.get_team_stats(away_id, league, season)
        
        # Fetch last 10 matches for form analysis
        home_last_10 = api_client.get_last_fixtures(home_id, league, season, last=10)
        away_last_10 = api_client.get_last_fixtures(away_id, league, season, last=10)
        
        # Fetch H2H
        h2h = api_client.get_h2h(home_id, away_id)
        
        # Fetch odds (optional)
        odds = api_client.get_odds(fixture_id)
        
        # Fetch injuries
        home_injuries = api_client.get_injuries(home_id, season)
        away_injuries = api_client.get_injuries(away_id, season)
        
        # 2b. Enhanced data fetching (always enabled for best predictions)
        # Fetch player and coach data (4 additional calls)
        home_players = api_client.get_players(home_id, season)
        away_players = api_client.get_players(away_id, season)
        home_coach = api_client.get_coach(home_id)
        away_coach = api_client.get_coach(away_id)
        
        # Fetch detailed statistics for recent matches (up to 10 more calls)
        home_fixture_ids = [f['fixture']['id'] for f in home_last_10.get('response', [])[:5]]
        away_fixture_ids = [f['fixture']['id'] for f in away_last_10.get('response', [])[:5]]
        home_recent_stats = api_client.get_recent_fixture_stats(home_fixture_ids)
        away_recent_stats = api_client.get_recent_fixture_stats(away_fixture_ids)
        
        # 2c. Get competition metadata for type-aware predictions
        competition_info = api_client.get_competition_info(league)
        round_info = api_client.get_fixture_round(fixture_id) if competition_info.get("type") == "european_cup" else None
        
        # 3. Build features with fallback
        try:
            features = feature_builder.build_features(
                fixture_details={'response': [fixture]},
                standings=standings,
                home_last_10=home_last_10,
                away_last_10=away_last_10,
                home_stats=home_stats,
                away_stats=away_stats,
                h2h=h2h,
                home_injuries=home_injuries,
                away_injuries=away_injuries,
                odds=odds,
                home_players=home_players,
                away_players=away_players,
                home_coach=home_coach,
                away_coach=away_coach,
                home_recent_stats=home_recent_stats,
                away_recent_stats=away_recent_stats,
                competition_info=competition_info,
                round_info=round_info
            )
        except Exception as e:
            print(f"Feature building failed: {e}. Using fallback features.")
            # Fallback: Create basic features from what we have or use defaults
            # We'll create a default feature dict and populate what we can
            features = {
                "home_id": home_id, "away_id": away_id,
                "home_name": fixture['teams']['home']['name'],
                "away_name": fixture['teams']['away']['name'],
                "home_league_points": 30, "away_league_points": 30, # Defaults
                "home_league_pos": 10, "away_league_pos": 10,
                "home_goals_for_avg": 1.3, "away_goals_for_avg": 1.2,
                "home_goals_against_avg": 1.2, "away_goals_against_avg": 1.3,
                # Add other required keys with defaults
                "home_points_last10": 15, "away_points_last10": 15,
                "home_form_last5": 7, "away_form_last5": 7,
                "home_wins_last10": 5, "away_wins_last10": 5,
                "home_draws_last10": 3, "away_draws_last10": 3,
                "home_losses_last10": 2, "away_losses_last10": 2,
                "home_goals_for_last10": 13, "away_goals_for_last10": 12,
                "home_goals_against_last10": 12, "away_goals_against_last10": 13,
                "h2h_home_wins": 2, "h2h_draws": 2, "h2h_away_wins": 2,
                "h2h_total_matches": 6,
                "home_clean_sheets": 3, "away_clean_sheets": 3,
                "home_total_matches": 20, "away_total_matches": 20,
                "odds_available": False,
                # Competition defaults
                "is_domestic_league": 1, "is_european_cup": 0,
                "is_knockout_stage": 0, "competition_prestige": 1.0
            }
        
        # 4. Predict
        result = predictor.predict_fixture(features)
        
        # 4.5 Validate prediction consistency
        validation = validate_prediction_consistency(result, features)
        
        # 5. Enrich features with Elo ratings for analysis
        elo_ratings = result.get('elo_ratings', {})
        enriched_features = {
            **features,
            'home_elo': elo_ratings.get('home', 1500),
            'away_elo': elo_ratings.get('away', 1500),
            'home_rank': features.get('home_league_pos', 10),
            'away_rank': features.get('away_league_pos', 10),
        }
        print(f"DEBUG: enriched_features home_elo={enriched_features.get('home_elo')}, away_elo={enriched_features.get('away_elo')}, home_rank={enriched_features.get('home_rank')}, away_rank={enriched_features.get('away_rank')}")
        
        # 6. Generate comprehensive analysis text using polished AnalysisLLM
        analysis = analysis_llm.analyze(result, enriched_features)
        
        # Track prediction stats
        ensemble_confidence = max(result['home_win_prob'], result['draw_prob'], result['away_win_prob'])
        stats_tracker.record_prediction(result.get('model_breakdown', {}), ensemble_confidence)
        
        # Log prediction for feedback learning system
        try:
            log_feedback_prediction(
                fixture_id=fixture_id,
                home_team=fixture['teams']['home']['name'],
                away_team=fixture['teams']['away']['name'],
                league_id=league,
                league_name=fixture.get('league', {}).get('name', 'Unknown'),
                match_date=fixture['fixture']['date'],
                prediction=result,
                model_breakdown=result.get('model_breakdown', {})
            )
        except Exception as e:
            print(f"Warning: Failed to log prediction for feedback: {e}")
        
        return {
            "prediction": result,
            "fixture_details": fixture,
            "analysis": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in predict_fixture: {e}")
        raise HTTPException(status_code=500, detail=str(e))




def validate_prediction_consistency(result: dict, features: dict) -> dict:
    """
    Validate prediction for logical consistency and flag warnings.
    Returns validation result with warnings if inconsistencies found.
    """
    warnings = []
    
    predicted_score = result.get('predicted_scoreline', '0-0')
    btts_prob = result.get('btts_prob', 0)
    over25_prob = result.get('over25_prob', 0)
    home_prob = result.get('home_win_prob', 0)
    draw_prob = result.get('draw_prob', 0)
    away_prob = result.get('away_win_prob', 0)
    
    # Parse predicted scoreline
    try:
        h_goals, a_goals = map(int, predicted_score.split('-'))
        
        # Check 1: BTTS vs Scoreline
        if btts_prob > 0.50 and (h_goals == 0 or a_goals == 0):
            warnings.append(f"⚠️ BTTS is {btts_prob*100:.0f}% but predicted score is {predicted_score} (only one team scores)")
        elif btts_prob < 0.35 and h_goals >= 1 and a_goals >= 1:
            warnings.append(f"⚠️ BTTS is only {btts_prob*100:.0f}% but predicted score is {predicted_score} (both teams score)")
        
        # Check 2: Over 2.5 vs Scoreline
        total_goals = h_goals + a_goals
        if over25_prob > 0.55 and total_goals <= 2:
            warnings.append(f"⚠️ Over 2.5 is {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} total goals)")
        elif over25_prob < 0.35 and total_goals > 3:
            warnings.append(f"⚠️ Over 2.5 is only {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} goals)")
        
        # Check 3: Scoreline vs Outcome Probability
        if h_goals > a_goals and home_prob < 0.40:
            warnings.append(f"⚠️ Home win predicted ({predicted_score}) but home win probability is only {home_prob*100:.0f}%")
        elif a_goals > h_goals and away_prob < 0.40:
            warnings.append(f"⚠️ Away win predicted ({predicted_score}) but away win probability is only {away_prob*100:.0f}%")
        elif h_goals == a_goals and draw_prob < 0.25:
            warnings.append(f"⚠️ Draw predicted ({predicted_score}) but draw probability is only {draw_prob*100:.0f}%")
            
    except Exception as e:
        warnings.append(f"⚠️ Could not validate scoreline: {e}")
    
    # Check 4: Model breakdown consensus
    model_breakdown = result.get('model_breakdown', {})
    models_favoring_home = 0
    models_favoring_away = 0
    
    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and 'home_win' in preds:
            h, a = preds.get('home_win', 0), preds.get('away_win', 0)
            if h > a:
                models_favoring_home += 1
            elif a > h:
                models_favoring_away += 1
    
    total_models = models_favoring_home + models_favoring_away
    if total_models > 0:
        if models_favoring_home > models_favoring_away and home_prob < away_prob:
            warnings.append(f"⚠️ {models_favoring_home}/{total_models} models favor home but ensemble favors away")
        elif models_favoring_away > models_favoring_home and away_prob < home_prob:
            warnings.append(f"⚠️ {models_favoring_away}/{total_models} models favor away but ensemble favors home")
    
    # Log warnings if any
    if warnings:
        print(f"\n🔍 Prediction Validation Warnings for {features.get('home_name', 'Home')} vs {features.get('away_name', 'Away')}:")
        for warning in warnings:
            print(f"   {warning}")
    
    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
        "warning_count": len(warnings)
    }


def generate_enhanced_analysis(fixture: dict, features: dict, result: dict) -> str:
    """
    Generate comprehensive match analysis with:
    1. H2H history context
    2. League position context  
    3. Model consensus indicator
    4. Rich tactical insights based on goals data
    """
    home_name = fixture['teams']['home']['name']
    away_name = fixture['teams']['away']['name']
    
    home_prob = result['home_win_prob'] * 100
    draw_prob = result['draw_prob'] * 100
    away_prob = result['away_win_prob'] * 100
    btts_prob = result['btts_prob'] * 100
    over25_prob = result['over25_prob'] * 100
    
    # ============================================
    # 1. DETERMINE FAVORITE & CONFIDENCE BADGE
    # ============================================
    if home_prob > away_prob:
        favorite, favorite_prob = home_name, home_prob
        underdog, underdog_prob = away_name, away_prob
    else:
        favorite, favorite_prob = away_name, away_prob
        underdog, underdog_prob = home_name, home_prob
    
    # Confidence badge with risk assessment
    if favorite_prob > 70:
        confidence_badge = "🟢 HIGH CONFIDENCE"
        confidence_desc = "strong favorite"
        risk_level = "Low risk"
    elif favorite_prob > 55:
        confidence_badge = "🟡 MEDIUM CONFIDENCE"
        confidence_desc = "moderate favorite"
        risk_level = "Medium risk"
    elif favorite_prob > 40:
        confidence_badge = "🟠 COMPETITIVE MATCH"
        confidence_desc = "slight edge"
        risk_level = "Higher risk - close call"
    else:
        confidence_badge = "🔴 UPSET ALERT"
        confidence_desc = "marginal favorite"
        risk_level = "High risk - anything can happen"
    
    # ============================================
    # 2. MODEL CONSENSUS ANALYSIS
    # ============================================
    model_breakdown = result.get('model_breakdown', {})
    models_favoring_home = 0
    models_favoring_away = 0
    models_favoring_draw = 0
    model_opinions = []
    
    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and 'home_win' in preds:
            h, d, a = preds.get('home_win', 0), preds.get('draw', 0), preds.get('away_win', 0)
            if h > d and h > a:
                models_favoring_home += 1
                model_opinions.append(f"{model_name.upper()}: {home_name}")
            elif a > d and a > h:
                models_favoring_away += 1
                model_opinions.append(f"{model_name.upper()}: {away_name}")
            else:
                models_favoring_draw += 1
                model_opinions.append(f"{model_name.upper()}: Draw")
    
    total_models = models_favoring_home + models_favoring_away + models_favoring_draw
    if total_models > 0:
        consensus_home = models_favoring_home / total_models
        consensus_away = models_favoring_away / total_models
        
        # Determine who the weighted ensemble actually favors
        ensemble_favors_home = home_prob > away_prob and home_prob > draw_prob
        ensemble_favors_away = away_prob > home_prob and away_prob > draw_prob
        
        # Check if model count agrees with weighted probability
        model_count_favors_home = models_favoring_home > models_favoring_away
        model_count_favors_away = models_favoring_away > models_favoring_home
        
        if consensus_home >= 0.75 and ensemble_favors_home:
            consensus_text = f"🤝 **Strong Consensus**: {models_favoring_home} of {total_models} models favor {home_name}. High model agreement increases prediction reliability."
        elif consensus_away >= 0.75 and ensemble_favors_away:
            consensus_text = f"🤝 **Strong Consensus**: {models_favoring_away} of {total_models} models favor {away_name}. High model agreement increases prediction reliability."
        elif ensemble_favors_home and not model_count_favors_home:
            # Weighted result differs from model count - explain the weighted models carry more influence
            consensus_text = f"⚖️ **Weighted Analysis**: While {models_favoring_away} of {total_models} models individually favor {away_name}, our higher-weighted models (GBDT, Elo) favor {home_name}. The weighted ensemble gives {home_name} the edge."
        elif ensemble_favors_away and not model_count_favors_away:
            # Weighted result differs from model count - explain the weighted models carry more influence
            consensus_text = f"⚖️ **Weighted Analysis**: While {models_favoring_home} of {total_models} models individually favor {home_name}, our higher-weighted models (GBDT, Elo) favor {away_name}. The weighted ensemble gives {away_name} the edge."
        elif max(consensus_home, consensus_away) >= 0.5:
            majority = home_name if consensus_home > consensus_away else away_name
            count = models_favoring_home if consensus_home > consensus_away else models_favoring_away
            consensus_text = f"⚖️ **Moderate Consensus**: {count} of {total_models} models lean toward {majority}. Model agreement supports the prediction."
        else:
            consensus_text = f"⚠️ **Models Divided**: Our AI models are split ({models_favoring_home} for {home_name}, {models_favoring_away} for {away_name}, {models_favoring_draw} for Draw). This match is highly unpredictable."
    else:
        consensus_text = ""
    
    # ============================================
    # 3. HEAD-TO-HEAD HISTORY
    # ============================================
    h2h_home = features.get('h2h_home_wins', 0)
    h2h_draws = features.get('h2h_draws', 0)
    h2h_away = features.get('h2h_away_wins', 0)
    h2h_total = features.get('h2h_total_matches', 0)
    
    if h2h_total > 0:
        if h2h_home > h2h_away + 2:
            h2h_text = f"📊 **Head-to-Head**: {home_name} dominates this fixture with {h2h_home} wins in {h2h_total} meetings ({h2h_draws} draws, {h2h_away} away wins). Historical advantage is significant."
        elif h2h_away > h2h_home + 2:
            h2h_text = f"📊 **Head-to-Head**: {away_name} has the upper hand historically with {h2h_away} wins in {h2h_total} meetings. {home_name} struggles in this fixture."
        elif h2h_draws >= h2h_home and h2h_draws >= h2h_away:
            h2h_text = f"📊 **Head-to-Head**: These teams often share the spoils - {h2h_draws} draws in {h2h_total} meetings. Consider a draw bet."
        else:
            h2h_text = f"📊 **Head-to-Head**: Balanced history with {h2h_home} home wins, {h2h_draws} draws, {h2h_away} away wins in {h2h_total} meetings."
    else:
        h2h_text = "📊 **Head-to-Head**: Limited historical data available for this matchup."
    
    # ============================================
    # 4. LEAGUE POSITION CONTEXT
    # ============================================
    home_pos = features.get('home_league_pos', 10)
    away_pos = features.get('away_league_pos', 10)
    home_pts = features.get('home_league_points', 0)
    away_pts = features.get('away_league_points', 0)
    
    pos_diff = abs(home_pos - away_pos)
    pts_diff = abs(home_pts - away_pts)
    
    if pos_diff >= 10:
        if home_pos < away_pos:
            league_text = f"🏆 **League Context**: Major mismatch! {home_name} ({home_pos}{'st' if home_pos == 1 else 'nd' if home_pos == 2 else 'rd' if home_pos == 3 else 'th'} with {home_pts}pts) vs {away_name} ({away_pos}{'th'} with {away_pts}pts). Class difference should tell."
        else:
            league_text = f"🏆 **League Context**: {away_name} ({away_pos}{'st' if away_pos == 1 else 'nd' if away_pos == 2 else 'rd' if away_pos == 3 else 'th'} with {away_pts}pts) visits lower-ranked {home_name} ({home_pos}{'th'} with {home_pts}pts). Favorites are clear."
    elif pos_diff >= 5 or pts_diff >= 8:
        higher = home_name if home_pos < away_pos else away_name
        higher_pos = min(home_pos, away_pos)
        higher_pts = max(home_pts, away_pts)
        league_text = f"🏆 **League Context**: {higher} sits {pos_diff} places higher in the table ({higher_pos}{'st' if higher_pos == 1 else 'nd' if higher_pos == 2 else 'rd' if higher_pos == 3 else 'th'} with {higher_pts}pts, {pts_diff}-point advantage). Noticeable quality gap."
    elif pos_diff <= 2 and pts_diff <= 3:
        league_text = f"🏆 **League Context**: Both teams level in the standings ({home_name}: {home_pos}{'th'} with {home_pts}pts, {away_name}: {away_pos}{'th'} with {away_pts}pts). Expect a tight contest."
    else:
        higher = home_name if home_pts > away_pts else away_name
        league_text = f"🏆 **League Context**: {home_name} ({home_pos}{'th'}, {home_pts}pts) hosts {away_name} ({away_pos}{'th'}, {away_pts}pts). {higher} has the edge in standings."
    
    # ============================================
    # 5. RICH TACTICAL INSIGHTS (Goals Data)
    # ============================================
    home_gf_avg = features.get('home_goals_for_avg', 1.3)
    home_ga_avg = features.get('home_goals_against_avg', 1.2)
    away_gf_avg = features.get('away_goals_for_avg', 1.2)
    away_ga_avg = features.get('away_goals_against_avg', 1.3)
    
    # Handle missing/zero data - use league averages as fallback
    if away_gf_avg == 0 or away_ga_avg == 0:
        # Newly promoted team or missing data - estimate from league position
        if away_pos >= 15:
            away_gf_avg = 0.9  # Struggling team estimate
            away_ga_avg = 1.6
        else:
            away_gf_avg = 1.2
            away_ga_avg = 1.3
    
    if home_gf_avg == 0 or home_ga_avg == 0:
        if home_pos >= 15:
            home_gf_avg = 0.9
            home_ga_avg = 1.6
        else:
            home_gf_avg = 1.2
            home_ga_avg = 1.3
    
    home_clean_sheets = features.get('home_clean_sheets', 0)
    away_clean_sheets = features.get('away_clean_sheets', 0)
    
    # Team styles
    home_style = "attacking" if home_gf_avg > 1.8 else "balanced" if home_gf_avg > 1.2 else "defensive"
    away_style = "attacking" if away_gf_avg > 1.8 else "balanced" if away_gf_avg > 1.2 else "defensive"
    home_defense = "solid" if home_ga_avg < 1.0 else "average" if home_ga_avg < 1.5 else "leaky"
    away_defense = "solid" if away_ga_avg < 1.0 else "average" if away_ga_avg < 1.5 else "leaky"
    
    if home_style == "attacking" and away_defense == "leaky":
        tactical_text = f"⚔️ **Tactical Matchup**: {home_name}'s potent attack (avg {home_gf_avg:.1f} goals/game) faces {away_name}'s vulnerable defense (conceding {away_ga_avg:.1f}/game). Goals expected!"
    elif away_style == "attacking" and home_defense == "leaky":
        tactical_text = f"⚔️ **Tactical Matchup**: {away_name} scores freely ({away_gf_avg:.1f}/game) and {home_name} struggles defensively ({home_ga_avg:.1f} conceded/game). Away goals likely."
    elif home_defense == "solid" and away_defense == "solid":
        tactical_text = f"⚔️ **Tactical Matchup**: Two defensively strong teams - {home_name} ({home_clean_sheets} clean sheets) vs {away_name} ({away_clean_sheets} clean sheets). Low-scoring affair expected."
    elif home_style == "attacking" and away_style == "attacking":
        tactical_text = f"⚔️ **Tactical Matchup**: Attacking philosophies clash! {home_name} ({home_gf_avg:.1f} goals/game) vs {away_name} ({away_gf_avg:.1f}/game). Entertainment guaranteed."
    else:
        tactical_text = f"⚔️ **Tactical Matchup**: {home_name} ({home_style} approach, {home_gf_avg:.1f} scored, {home_ga_avg:.1f} conceded) vs {away_name} ({away_style} style, {away_gf_avg:.1f} scored, {away_ga_avg:.1f} conceded)."
    
    # ============================================
    # 6. FORM ANALYSIS (Enhanced with league context)
    # ============================================
    home_form = features.get('home_form_last5', 7)
    away_form = features.get('away_form_last5', 7)
    home_wins_10 = features.get('home_wins_last10', 5)
    away_wins_10 = features.get('away_wins_last10', 5)
    
    # Cross-reference form with league position for coherence
    if home_form > away_form + 4:
        form_text = f"📈 **Form Guide**: {home_name} is flying ({home_wins_10}W in last 10, {home_form}pts from last 5). {away_name} struggling in comparison ({away_wins_10}W, {away_form}pts). Momentum strongly favors the hosts."
    elif away_form > home_form + 4:
        form_text = f"📈 **Form Guide**: {away_name} arrives in red-hot form ({away_wins_10}W in last 10, {away_form}pts from last 5). {home_name} ({home_wins_10}W, {home_form}pts) may struggle to cope."
    elif abs(home_form - away_form) <= 2:
        # If form is similar but league position isn't, add context
        if pos_diff > 8:
            higher_team = home_name if home_pos < away_pos else away_name
            lower_team = away_name if home_pos < away_pos else home_name
            form_text = f"📈 **Form Guide**: Recent form is similar ({home_name} {home_form}pts, {away_name} {away_form}pts from last 5), but {higher_team}'s overall quality should prevail over {lower_team}."
        else:
            form_text = f"📈 **Form Guide**: Both teams in similar form - {home_name} ({home_form}pts) vs {away_name} ({away_form}pts) from last 5. Recent results are level."
    else:
        better = home_name if home_form > away_form else away_name
        form_text = f"📈 **Form Guide**: {better} has a slight edge in recent form ({home_name}: {home_form}pts, {away_name}: {away_form}pts from last 5)."
    
    # ============================================
    # 7. GOALS PREDICTION
    # ============================================
    btts_text = f"Both teams to score: **{'Yes' if btts_prob > 50 else 'No'}** ({btts_prob:.0f}% probability)"
    over_under_text = f"Over 2.5 goals: **{'Likely' if over25_prob > 55 else 'Possible' if over25_prob > 40 else 'Unlikely'}** ({over25_prob:.0f}%)"
    
    # ============================================
    # 8. FINAL RECOMMENDATION
    # ============================================
    if favorite_prob > 65 and (models_favoring_home >= 5 or models_favoring_away >= 5):
        recommendation = f"✅ **Verdict**: {favorite} is a **strong pick** with high model consensus and {favorite_prob:.0f}% probability. {risk_level}."
    elif draw_prob > 28 and models_favoring_draw >= 2:
        recommendation = f"🤝 **Verdict**: This fixture has **draw written all over it** ({draw_prob:.0f}%). Multiple models see stalemate. Consider Draw or Double Chance."
    elif underdog_prob > 35:
        recommendation = f"⚡ **Verdict**: **Upset potential!** {underdog} at {underdog_prob:.0f}% offers value. {favorite} isn't as dominant as expected."
    elif favorite_prob > 50:
        recommendation = f"📊 **Verdict**: {favorite} is favored ({favorite_prob:.0f}%) but this is no certainty. {risk_level}. Consider Draw No Bet for safety."
    else:
        recommendation = f"🎲 **Verdict**: Coin flip match. No clear winner - {home_name} ({home_prob:.0f}%) vs {away_name} ({away_prob:.0f}%). Small stakes only."
    
    # ============================================
    # 9. ELO RATINGS (NEW)
    # ============================================
    elo_ratings = result.get('elo_ratings', {})
    home_elo = elo_ratings.get('home', 1500)
    away_elo = elo_ratings.get('away', 1500)
    elo_diff = elo_ratings.get('diff', 0)
    
    if abs(elo_diff) > 150:
        better = home_name if elo_diff > 0 else away_name
        worse = away_name if elo_diff > 0 else home_name
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — **{abs(elo_diff):.0f} point gap** in favor of {better}. Clear quality advantage."
    elif abs(elo_diff) > 80:
        better = home_name if elo_diff > 0 else away_name
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — {better} rated notably higher ({abs(elo_diff):.0f} pts difference)."
    else:
        elo_text = f"📈 **Elo Ratings**: {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — Evenly matched on long-term rating ({abs(elo_diff):.0f} pts apart)."
    
    # ============================================
    # ASSEMBLE FINAL ANALYSIS
    # ============================================
    analysis = f"""## {home_name} vs {away_name}

{confidence_badge} | **{favorite}** favored at {favorite_prob:.1f}%

---

### 📊 Prediction Summary

| Outcome | Probability |
|---------|-------------|
| {home_name} Win | {home_prob:.1f}% |
| Draw | {draw_prob:.1f}% |
| {away_name} Win | {away_prob:.1f}% |

**Predicted Score: {result['predicted_scoreline']}**

{btts_text}
{over_under_text}

---

### 🔍 Deep Analysis

{consensus_text}

{elo_text}

{h2h_text}

{league_text}

{tactical_text}

{form_text}

---

### 🎯 Our Verdict

{recommendation}

---

*Analysis by FixtureCast AI — 8-model ensemble (GBDT 22%, Elo 22%, GNN 18%, LSTM 14%, Bayesian 10%, Transformer 8%, CatBoost 6%)*
"""
    
    return analysis

@app.post("/predict", response_model=PredictionResponse)
async def predict_match(features: MatchFeatures):
    """
    Predict match outcome given team features.
    
    Args:
        features: MatchFeatures object with team statistics
        
    Returns:
        PredictionResponse with win probabilities and scoreline prediction
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    
    try:
        # Convert Pydantic model to dict
        features_dict = features.dict()
        
        # Get prediction from ensemble
        result = predictor.predict_fixture(features_dict)
        
        # Track prediction stats
        ensemble_confidence = max(result['home_win_prob'], result['draw_prob'], result['away_win_prob'])
        stats_tracker.record_prediction(result.get('model_breakdown', {}), ensemble_confidence)
        
        return PredictionResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.get("/models/info")
async def get_models_info():
    """Get information about loaded models"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    
    return {
        "base_models": [
            "GBDTModel",
            "CatBoostModel",
            "PoissonModel",
            "TransformerSequenceModel",
            "LSTMSequenceModel",
            "GNNModel",
            "BayesianModel",
            "EloGlickoModel"
        ],
        "meta_model_loaded": predictor.meta_model is not None,
        "ensemble_weights": {
            "gbdt": 0.22,
            "elo": 0.22,
            "gnn": 0.18,
            "lstm": 0.14,
            "bayesian": 0.10,
            "transformer": 0.08,
            "catboost": 0.06,
            "monte_carlo": 0.00  # Auxiliary
        }
    }

@app.get("/api/model-stats")
async def get_model_stats():
    """
    Get comprehensive statistics about model performance and usage.
    Returns prediction counts, confidence metrics, and model metadata.
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    
    return stats_tracker.get_model_stats()


# ============================================
# FEEDBACK LEARNING ENDPOINTS
# ============================================
from ml_engine.feedback_learning import (
    feedback_system, 
    get_performance_report, 
    get_recommended_weights,
    record_result
)

@app.get("/api/feedback/performance")
async def get_feedback_performance():
    """
    Get feedback learning performance report.
    Shows how well our predictions match actual results.
    """
    return get_performance_report()

@app.get("/api/feedback/pending")
async def get_pending_predictions():
    """Get predictions awaiting result evaluation"""
    pending = feedback_system.get_pending_results()
    return {
        "count": len(pending),
        "predictions": [
            {
                "fixture_id": p['fixture_id'],
                "home_team": p['home_team'],
                "away_team": p['away_team'],
                "match_date": p['match_date'],
                "predicted_outcome": p['prediction']['predicted_outcome'],
                "confidence": p['prediction']['confidence']
            }
            for p in pending[:20]  # Limit to 20
        ]
    }

@app.post("/api/feedback/record-result")
async def api_record_result(fixture_id: int, home_goals: int, away_goals: int):
    """
    Manually record a match result to evaluate prediction.
    """
    evaluation = record_result(fixture_id, home_goals, away_goals)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="No prediction found for this fixture")
    return {
        "status": "recorded",
        "evaluation": evaluation
    }

@app.get("/api/feedback/recommended-weights")
async def get_recommended_model_weights():
    """
    Get recommended model weights based on actual performance.
    These can be used to improve ensemble accuracy.
    """
    weights = get_recommended_weights()
    if not weights:
        return {
            "status": "insufficient_data",
            "message": "Need at least 10 evaluated predictions per model",
            "weights": {}
        }
    return {
        "status": "available",
        "weights": weights
    }

@app.post("/api/feedback/update-from-api")
async def update_results_from_backend():
    """
    Fetch completed match results from the backend API 
    and update the feedback system.
    """
    try:
        from ml_engine.auto_update_results import update_results_from_api
        result = update_results_from_api()
        return {
            "status": "success",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("Starting FixtureCast ML API server...")
    print("API docs will be available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
