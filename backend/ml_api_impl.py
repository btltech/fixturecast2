#!/usr/bin/env python3
"""
FastAPI server for FixtureCast ML predictions.
Exposes endpoints to get match predictions using the trained ensemble.
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from metrics_tracker import MetricsTracker

from ml_engine.ensemble_predictor import EnsemblePredictor
from ml_engine.feedback_learning import log_prediction as log_feedback_prediction

# Initialize metrics tracker for logging predictions
metrics_tracker = MetricsTracker()

# ============================================
# SEASONAL STATS LOADING FOR ENHANCED PREDICTIONS
# ============================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "historical")


def load_all_seasonal_stats():
    """
    Load team statistics from stats files for enhanced predictions.
    Returns: {season: {team_id: team_stats}}
    """
    all_stats = {}

    for year in [2020, 2021, 2022, 2023, 2024]:
        filepath = os.path.join(DATA_DIR, f"stats_{year}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    season_stats = json.load(f)

                # Convert to team_id -> stats mapping
                stats_by_team = {}
                for team_id, data in season_stats.items():
                    try:
                        team_data = data.get("response", data)  # Handle both formats
                        if isinstance(team_data, dict):
                            stats_by_team[int(team_id)] = {
                                "form": team_data.get("form", ""),
                                "fixtures": team_data.get("fixtures", {}),
                                "goals_for": team_data.get("goals", {}).get("for", {}),
                                "goals_against": team_data.get("goals", {}).get("against", {}),
                                "biggest": team_data.get("biggest", {}),
                                "clean_sheet": team_data.get("clean_sheet", {}),
                                "failed_to_score": team_data.get("failed_to_score", {}),
                                "penalty": team_data.get("penalty", {}),
                                "lineups": team_data.get("lineups", []),
                                "cards": team_data.get("cards", {}),
                            }
                    except (KeyError, TypeError, ValueError):
                        continue

                all_stats[year] = stats_by_team
                print(f"  Loaded stats for {len(stats_by_team)} teams from {year}")
            except Exception as e:
                print(f"  Warning: Failed to load stats_{year}.json: {e}")

    return all_stats


def extract_seasonal_features(team_stats, prefix="home"):
    """
    Extract all features from team seasonal stats.
    Returns a dict of numeric features with prefix (home_ or away_).
    """
    features = {}

    if not team_stats:
        # Return default neutral features
        defaults = {
            f"{prefix}_stat_home_win_rate": 0.4,
            f"{prefix}_stat_away_win_rate": 0.3,
            f"{prefix}_stat_home_draw_rate": 0.3,
            f"{prefix}_stat_away_draw_rate": 0.3,
            f"{prefix}_stat_goals_for_home_avg": 1.3,
            f"{prefix}_stat_goals_for_away_avg": 1.0,
            f"{prefix}_stat_goals_against_home_avg": 1.0,
            f"{prefix}_stat_goals_against_away_avg": 1.3,
            f"{prefix}_stat_clean_sheet_home_rate": 0.3,
            f"{prefix}_stat_clean_sheet_away_rate": 0.2,
            f"{prefix}_stat_failed_to_score_home_rate": 0.2,
            f"{prefix}_stat_failed_to_score_away_rate": 0.3,
            f"{prefix}_stat_penalty_success_rate": 0.75,
            f"{prefix}_stat_biggest_win_streak": 3,
            f"{prefix}_stat_biggest_lose_streak": 2,
            f"{prefix}_stat_goals_0_15_pct": 0.1,
            f"{prefix}_stat_goals_16_30_pct": 0.15,
            f"{prefix}_stat_goals_31_45_pct": 0.15,
            f"{prefix}_stat_goals_46_60_pct": 0.2,
            f"{prefix}_stat_goals_61_75_pct": 0.2,
            f"{prefix}_stat_goals_76_90_pct": 0.2,
            f"{prefix}_stat_conceded_0_15_pct": 0.1,
            f"{prefix}_stat_conceded_46_60_pct": 0.2,
            f"{prefix}_stat_conceded_76_90_pct": 0.2,
            f"{prefix}_stat_yellow_cards_per_game": 2.0,
            f"{prefix}_stat_red_cards_per_game": 0.1,
            f"{prefix}_stat_primary_formation": 0,
            f"{prefix}_stat_form_win_pct": 0.4,
        }
        return defaults

    # FIXTURES DATA
    fixtures = team_stats.get("fixtures", {})
    played = fixtures.get("played", {})
    wins = fixtures.get("wins", {})
    draws = fixtures.get("draws", {})
    loses = fixtures.get("loses", {})

    total_played = played.get("total", 38) or 38
    home_played = played.get("home", 19) or 19
    away_played = played.get("away", 19) or 19

    # Win/draw/loss rates by venue
    features[f"{prefix}_stat_home_win_rate"] = (wins.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_win_rate"] = (wins.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_home_draw_rate"] = (draws.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_draw_rate"] = (draws.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_home_loss_rate"] = (loses.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_away_loss_rate"] = (loses.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_total_wins"] = wins.get("total", 0) or 0
    features[f"{prefix}_stat_total_draws"] = draws.get("total", 0) or 0
    features[f"{prefix}_stat_total_losses"] = loses.get("total", 0) or 0

    # GOALS FOR DATA
    goals_for = team_stats.get("goals_for", {})
    gf_avg = goals_for.get("average", {})
    gf_minute = goals_for.get("minute", {})
    gf_total = goals_for.get("total", {})

    features[f"{prefix}_stat_goals_for_home_avg"] = float(gf_avg.get("home", "1.3") or "1.3")
    features[f"{prefix}_stat_goals_for_away_avg"] = float(gf_avg.get("away", "1.0") or "1.0")
    features[f"{prefix}_stat_goals_for_total"] = gf_total.get("total", 50) or 50

    # Goals by minute period
    for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]:
        period_data = gf_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"{prefix}_stat_goals_{period_key}_pct"] = pct

    # GOALS AGAINST DATA
    goals_against = team_stats.get("goals_against", {})
    ga_avg = goals_against.get("average", {})
    ga_minute = goals_against.get("minute", {})
    ga_total = goals_against.get("total", {})

    features[f"{prefix}_stat_goals_against_home_avg"] = float(ga_avg.get("home", "1.0") or "1.0")
    features[f"{prefix}_stat_goals_against_away_avg"] = float(ga_avg.get("away", "1.3") or "1.3")
    features[f"{prefix}_stat_goals_against_total"] = ga_total.get("total", 50) or 50

    # Conceded by minute period
    for period in ["0-15", "46-60", "76-90"]:
        period_data = ga_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"{prefix}_stat_conceded_{period_key}_pct"] = pct

    # BIGGEST WINS/LOSSES
    biggest = team_stats.get("biggest", {})
    streak = biggest.get("streak", {})

    features[f"{prefix}_stat_biggest_win_streak"] = streak.get("wins", 1) or 1
    features[f"{prefix}_stat_biggest_lose_streak"] = streak.get("loses", 1) or 1
    features[f"{prefix}_stat_biggest_draw_streak"] = streak.get("draws", 1) or 1

    # CLEAN SHEET DATA
    clean_sheet = team_stats.get("clean_sheet", {})
    features[f"{prefix}_stat_clean_sheet_home_rate"] = (
        clean_sheet.get("home", 0) or 0
    ) / home_played
    features[f"{prefix}_stat_clean_sheet_away_rate"] = (
        clean_sheet.get("away", 0) or 0
    ) / away_played
    features[f"{prefix}_stat_clean_sheet_total"] = clean_sheet.get("total", 10) or 10

    # FAILED TO SCORE DATA
    fts = team_stats.get("failed_to_score", {})
    features[f"{prefix}_stat_failed_to_score_home_rate"] = (fts.get("home", 0) or 0) / home_played
    features[f"{prefix}_stat_failed_to_score_away_rate"] = (fts.get("away", 0) or 0) / away_played
    features[f"{prefix}_stat_failed_to_score_total"] = fts.get("total", 8) or 8

    # PENALTY DATA
    penalty = team_stats.get("penalty", {})
    scored = penalty.get("scored", {})
    missed = penalty.get("missed", {})
    pen_scored = scored.get("total", 0) or 0
    pen_missed = missed.get("total", 0) or 0
    if pen_scored + pen_missed > 0:
        features[f"{prefix}_stat_penalty_success_rate"] = pen_scored / (pen_scored + pen_missed)
    else:
        features[f"{prefix}_stat_penalty_success_rate"] = 0.75

    # LINEUPS/FORMATIONS
    lineups = team_stats.get("lineups", [])
    if lineups:
        formation_map = {
            "4-3-3": 1,
            "4-4-2": 2,
            "3-4-3": 3,
            "4-2-3-1": 4,
            "3-5-2": 5,
            "4-1-4-1": 6,
            "5-3-2": 7,
            "3-4-2-1": 8,
            "4-5-1": 9,
            "5-4-1": 10,
        }
        primary_formation = lineups[0].get("formation", "4-3-3") if lineups else "4-3-3"
        features[f"{prefix}_stat_primary_formation"] = formation_map.get(primary_formation, 0)
        features[f"{prefix}_stat_formation_consistency"] = (
            lineups[0].get("played", 20) / total_played if lineups else 0.5
        )
    else:
        features[f"{prefix}_stat_primary_formation"] = 0
        features[f"{prefix}_stat_formation_consistency"] = 0.5

    # CARDS DATA
    cards = team_stats.get("cards", {})
    yellow = cards.get("yellow", {})
    red = cards.get("red", {})

    yellow_total = sum(
        (yellow.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )
    red_total = sum(
        (red.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )
    features[f"{prefix}_stat_yellow_cards_per_game"] = yellow_total / total_played
    features[f"{prefix}_stat_red_cards_per_game"] = red_total / total_played

    # FORM DATA
    form_str = team_stats.get("form", "")
    if form_str:
        form_wins = form_str.count("W")
        form_draws = form_str.count("D")
        form_len = len(form_str) or 1
        features[f"{prefix}_stat_form_win_pct"] = form_wins / form_len
        features[f"{prefix}_stat_form_draw_pct"] = form_draws / form_len
        # Recent 5 games
        recent = form_str[-5:]
        features[f"{prefix}_stat_recent_form_win_pct"] = (
            recent.count("W") / len(recent) if recent else 0.4
        )
    else:
        features[f"{prefix}_stat_form_win_pct"] = 0.4
        features[f"{prefix}_stat_form_draw_pct"] = 0.3
        features[f"{prefix}_stat_recent_form_win_pct"] = 0.4

    return features


def enrich_features_with_seasonal_stats(features, home_id, away_id, seasonal_stats):
    """
    Enrich feature dict with seasonal statistics for both teams.
    Uses most recent available season data (2024 preferred).
    """
    enhanced = dict(features)  # Copy original

    # Find best available stats for each team (most recent season)
    home_stats = None
    away_stats = None

    for year in [2024, 2023, 2022, 2021, 2020]:
        if year in seasonal_stats:
            if home_id in seasonal_stats[year] and not home_stats:
                home_stats = seasonal_stats[year][home_id]
            if away_id in seasonal_stats[year] and not away_stats:
                away_stats = seasonal_stats[year][away_id]
            if home_stats and away_stats:
                break

    # Extract and add features
    home_features = extract_seasonal_features(home_stats, prefix="home")
    away_features = extract_seasonal_features(away_stats, prefix="away")

    enhanced.update(home_features)
    enhanced.update(away_features)

    # Also add without prefix for compatibility with training feature keys
    for key, val in home_features.items():
        # Convert home_stat_xxx to stat_xxx_home
        if key.startswith("home_stat_"):
            stat_name = key.replace("home_stat_", "stat_")
            enhanced[stat_name] = val

    for key, val in away_features.items():
        if key.startswith("away_stat_"):
            stat_name = key.replace("away_stat_", "stat_")
            # Only add away stats if they don't conflict
            if stat_name not in enhanced:
                enhanced[stat_name] = val

    return enhanced


# Load seasonal stats once at module load
print("Loading seasonal team statistics for enhanced predictions...")
SEASONAL_STATS = load_all_seasonal_stats()
print(f"Loaded stats for {sum(len(s) for s in SEASONAL_STATS.values())} total team-seasons")


app = FastAPI(
    title="FixtureCast ML API",
    description="Machine Learning powered football match prediction API",
    version="1.2.0",
)
print("DEBUG: ml_api_impl loaded")

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
            "type": "Deep Learning",
        },
        "elo": {
            "full_name": "Elo-Glicko Rating",
            "description": "Chess-inspired rating system adapted for football team strength",
            "type": "Statistical",
        },
        "lstm": {
            "full_name": "Long Short-Term Memory",
            "description": "Captures sequential patterns in team form and momentum",
            "type": "Deep Learning",
        },
        "gbdt": {
            "full_name": "Gradient Boosted Decision Trees",
            "description": "Ensemble of decision trees for robust feature-based predictions",
            "type": "Machine Learning",
        },
        "bayesian": {
            "full_name": "Bayesian Inference",
            "description": "Probabilistic model incorporating betting odds and prior knowledge",
            "type": "Statistical",
        },
        "transformer": {
            "full_name": "Transformer Network",
            "description": "Attention-based model analyzing complex feature interactions",
            "type": "Deep Learning",
        },
        "catboost": {
            "full_name": "CatBoost",
            "description": "Gradient boosting with native handling of categorical features",
            "type": "Machine Learning",
        },
        "poisson": {
            "full_name": "Poisson Distribution",
            "description": "Models expected goals using Poisson probability distribution",
            "type": "Statistical",
        },
        "monte_carlo": {
            "full_name": "Monte Carlo Simulation",
            "description": "Simulates thousands of match outcomes for scoreline prediction",
            "type": "Simulation",
        },
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
        "monte_carlo": 0.00,  # Auxiliary - used for scoreline
    }

    def __init__(self):
        self.stats = {
            "total_predictions": 0,
            "predictions_by_model": defaultdict(int),
            "confidence_sums": defaultdict(float),
            "confidence_counts": defaultdict(int),
            "predictions_log": [],
            "started_at": datetime.now().isoformat(),
            "last_prediction_at": None,
        }
        self._load_stats()

    def _load_stats(self):
        """Load stats from file if exists"""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    loaded = json.load(f)
                    self.stats["total_predictions"] = loaded.get("total_predictions", 0)
                    self.stats["predictions_by_model"] = defaultdict(
                        int, loaded.get("predictions_by_model", {})
                    )
                    self.stats["confidence_sums"] = defaultdict(
                        float, loaded.get("confidence_sums", {})
                    )
                    self.stats["confidence_counts"] = defaultdict(
                        int, loaded.get("confidence_counts", {})
                    )
                    self.stats["predictions_log"] = loaded.get("predictions_log", [])[-100:]
                    self.stats["started_at"] = loaded.get("started_at", datetime.now().isoformat())
                    self.stats["last_prediction_at"] = loaded.get("last_prediction_at")
                    print(
                        f"Loaded prediction stats: {self.stats['total_predictions']} total predictions"
                    )
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
                "last_prediction_at": self.stats["last_prediction_at"],
            }
            with open(STATS_FILE, "w") as f:
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
                max_conf = max(
                    preds.get("home_win", 0), preds.get("draw", 0), preds.get("away_win", 0)
                )
                self.stats["confidence_sums"][model_name] += max_conf
                self.stats["confidence_counts"][model_name] += 1

        # Log prediction
        self.stats["predictions_log"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "ensemble_confidence": round(ensemble_confidence, 4),
            }
        )

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

            models.append(
                {
                    "name": model_name,
                    "full_name": metadata.get("full_name", model_name.upper()),
                    "description": metadata.get("description", ""),
                    "type": metadata.get("type", "Unknown"),
                    "weight": weight,
                    "predictions": pred_count,
                    "avg_confidence": avg_confidence,
                    "status": "active" if weight > 0 else "auxiliary",
                }
            )

        # Sort by weight (highest first)
        models.sort(key=lambda x: x["weight"], reverse=True)

        # Calculate ensemble-level stats
        total_preds = self.stats["total_predictions"]

        # Average ensemble confidence from recent predictions
        recent_logs = self.stats["predictions_log"][-50:]
        avg_ensemble_conf = (
            round(sum(log["ensemble_confidence"] for log in recent_logs) / len(recent_logs), 4)
            if recent_logs
            else 0.0
        )

        return {
            "ensemble_accuracy": None,  # Real accuracy requires outcome validation (coming soon)
            "total_predictions": total_preds,
            "avg_ensemble_confidence": avg_ensemble_conf,
            "models": models,
            "tracking_since": self.stats["started_at"],
            "last_prediction": self.stats["last_prediction_at"],
            "note": "Accuracy metrics require outcome validation which is coming in a future update.",
        }


# Initialize stats tracker
stats_tracker = PredictionStatsTracker()

# Enable CORS - Allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to add Prometheus metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)
    print("Prometheus metrics enabled at /metrics")
except ImportError:
    print("Prometheus metrics not available - install prometheus-fastapi-instrumentator")

import json
import logging
from contextlib import asynccontextmanager

from analysis_llm import AnalysisLLM

# Initialize predictor once at startup (loads trained models)
from api_client import ApiClient, RedisCache
from safe_feature_builder import FeatureBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
predictor = None
api_client = None
feature_builder = FeatureBuilder()
analysis_llm = AnalysisLLM()
prediction_cache = RedisCache(prefix="fixturecast:mlpred:")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global predictor, api_client

    # Startup
    logger.info("Loading ML models...")
    predictor = EnsemblePredictor(load_trained=True)
    logger.info("ML models loaded successfully!")

    # Initialize API Client
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path) as f:
            config = json.load(f)
        api_client = ApiClient(config)
        logger.info("API Client initialized! Enhanced feature set (24 API calls per prediction)")
    except Exception as e:
        logger.warning(f"Failed to initialize API Client: {e}")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down ML API...")
    predictor = None
    api_client = None


# Re-create app with lifespan
app = FastAPI(
    title="FixtureCast ML API",
    description="Machine Learning powered football match prediction API",
    version="2.0.0",
    lifespan=lifespan,
)

# Re-add middleware after app recreation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchFeatures(BaseModel):
    """
    Feature dict for a single match prediction with validation.
    All numeric fields are validated for reasonable ranges.
    """

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

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "home_id": 42,
                "away_id": 33,
                "home_name": "Arsenal",
                "away_name": "Manchester United",
                "home_league_points": 45,
                "away_league_points": 38,
                "home_league_pos": 3,
                "away_league_pos": 7,
            }
        }

    def validate_probabilities(self) -> bool:
        """Validate that odds are in reasonable range if provided."""
        if self.odds_home_win is not None:
            if not (1.0 <= self.odds_home_win <= 100.0):
                return False
        if self.odds_draw is not None:
            if not (1.0 <= self.odds_draw <= 100.0):
                return False
        if self.odds_away_win is not None:
            if not (1.0 <= self.odds_away_win <= 100.0):
                return False
        return True


class PredictionResponse(BaseModel):
    """
    Response containing match prediction with confidence intervals.
    All probabilities are validated to be between 0 and 1.
    """

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_scoreline: str
    btts_prob: float
    over25_prob: float
    model_breakdown: Dict
    scoreline_distribution: Optional[Dict] = None
    confidence_intervals: Optional[Dict] = None
    elo_ratings: Optional[Dict] = None

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "home_win_prob": 0.45,
                "draw_prob": 0.28,
                "away_win_prob": 0.27,
                "predicted_scoreline": "2-1",
                "btts_prob": 0.62,
                "over25_prob": 0.58,
                "model_breakdown": {},
            }
        }

    def validate_probabilities(self) -> bool:
        """Ensure all probabilities are valid (between 0 and 1)."""
        probs = [
            self.home_win_prob,
            self.draw_prob,
            self.away_win_prob,
            self.btts_prob,
            self.over25_prob,
        ]
        return all(0.0 <= p <= 1.0 for p in probs)

    def probabilities_sum_valid(self) -> bool:
        """Check that main outcome probabilities sum to approximately 1."""
        total = self.home_win_prob + self.draw_prob + self.away_win_prob
        return 0.99 <= total <= 1.01


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    detail: Optional[str] = None
    code: int = 500
    timestamp: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Prediction failed",
                "detail": "Unable to fetch team statistics",
                "code": 503,
                "timestamp": "2025-01-15T10:30:00Z",
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    models_loaded: bool
    api_client_ready: bool
    timestamp: str
    uptime_seconds: Optional[float] = None


@app.get("/debug/source")
async def get_source():
    try:
        with open(
            os.path.join(os.path.dirname(__file__), "..", "ml_engine", "ensemble_predictor.py"), "r"
        ) as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    return {
        "service": "FixtureCast ML API",
        "version": "2.0.0",
        "status": "running",
        "models_loaded": predictor is not None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": predictor is not None,
        "api_client_ready": api_client is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint for ML API.
    Returns metrics in Prometheus text exposition format.
    """
    from starlette.responses import PlainTextResponse

    # Get stats from tracker
    stats = stats_tracker.stats

    # Build Prometheus format output
    lines = [
        "# HELP ml_api_predictions_total Total number of predictions made",
        "# TYPE ml_api_predictions_total counter",
        f'ml_api_predictions_total {stats.get("total_predictions", 0)}',
        "",
        "# HELP ml_api_models_loaded Whether ML models are loaded",
        "# TYPE ml_api_models_loaded gauge",
        f"ml_api_models_loaded {1 if predictor else 0}",
        "",
        "# HELP ml_api_client_ready Whether API client is initialized",
        "# TYPE ml_api_client_ready gauge",
        f"ml_api_client_ready {1 if api_client else 0}",
    ]

    # Add per-model confidence averages
    lines.append("")
    lines.append("# HELP ml_api_model_avg_confidence Average model confidence per model type")
    lines.append("# TYPE ml_api_model_avg_confidence gauge")
    for model, count in stats.get("confidence_counts", {}).items():
        if count > 0:
            avg_conf = stats.get("confidence_sums", {}).get(model, 0) / count
            lines.append(f'ml_api_model_avg_confidence{{model="{model}"}} {avg_conf:.4f}')

    # Add prediction counts by model
    lines.append("")
    lines.append("# HELP ml_api_predictions_by_model Predictions by model type")
    lines.append("# TYPE ml_api_predictions_by_model counter")
    for model, count in stats.get("predictions_by_model", {}).items():
        lines.append(f'ml_api_predictions_by_model{{model="{model}"}} {count}')

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


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

        if not fixture_response or not fixture_response.get("response"):
            raise HTTPException(status_code=404, detail="Fixture not found")

        fixture = fixture_response["response"][0]

        # Cache key (skip caching for live/finished fixtures)
        status_short = fixture.get("fixture", {}).get("status", {}).get("short")
        kickoff_ts = fixture.get("fixture", {}).get("timestamp")  # epoch seconds
        cache_key = None
        allow_cache = status_short not in {"FT", "AET", "PEN", "CANC", "ABD", "1H", "2H", "LIVE"}
        # If fixture starts within 2 hours, use a shorter TTL later; still allow cache for now
        near_kickoff = False
        if kickoff_ts:
            time_to_kickoff = kickoff_ts - time.time()
            near_kickoff = 0 < time_to_kickoff <= 2 * 3600
        if allow_cache:
            cache_key = f"prediction:{fixture_id}:{season}"
            cached = prediction_cache.get(cache_key)
            if cached:
                return cached

        # Auto-detect league from fixture if not explicitly provided or default
        actual_league = fixture.get("league", {}).get("id", league)
        if actual_league and actual_league != league:
            print(f"Auto-detected league {actual_league} from fixture (param was {league})")
            league = actual_league

        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

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
        home_fixture_ids = [f["fixture"]["id"] for f in home_last_10.get("response", [])[:5]]
        away_fixture_ids = [f["fixture"]["id"] for f in away_last_10.get("response", [])[:5]]
        home_recent_stats = api_client.get_recent_fixture_stats(home_fixture_ids)
        away_recent_stats = api_client.get_recent_fixture_stats(away_fixture_ids)

        # 2c. Get competition metadata for type-aware predictions
        competition_info = api_client.get_competition_info(league)
        round_info = (
            api_client.get_fixture_round(fixture_id)
            if competition_info.get("type") == "european_cup"
            else None
        )

        # 3. Build features with fallback
        try:
            features = feature_builder.build_features(
                fixture_details={"response": [fixture]},
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
                round_info=round_info,
            )
        except Exception as e:
            print(f"Feature building failed: {e}. Using fallback features.")
            # Fallback: Create basic features from what we have or use defaults
            # We'll create a default feature dict and populate what we can
            features = {
                "home_id": home_id,
                "away_id": away_id,
                "home_name": fixture["teams"]["home"]["name"],
                "away_name": fixture["teams"]["away"]["name"],
                "home_league_points": 30,
                "away_league_points": 30,  # Defaults
                "home_league_pos": 10,
                "away_league_pos": 10,
                "home_goals_for_avg": 1.3,
                "away_goals_for_avg": 1.2,
                "home_goals_against_avg": 1.2,
                "away_goals_against_avg": 1.3,
                # Add other required keys with defaults
                "home_points_last10": 15,
                "away_points_last10": 15,
                "home_form_last5": 7,
                "away_form_last5": 7,
                "home_wins_last10": 5,
                "away_wins_last10": 5,
                "home_draws_last10": 3,
                "away_draws_last10": 3,
                "home_losses_last10": 2,
                "away_losses_last10": 2,
                "home_goals_for_last10": 13,
                "away_goals_for_last10": 12,
                "home_goals_against_last10": 12,
                "away_goals_against_last10": 13,
                "h2h_home_wins": 2,
                "h2h_draws": 2,
                "h2h_away_wins": 2,
                "h2h_total_matches": 6,
                "home_clean_sheets": 3,
                "away_clean_sheets": 3,
                "home_total_matches": 20,
                "away_total_matches": 20,
                "odds_available": False,
                # Competition defaults
                "is_domestic_league": 1,
                "is_european_cup": 0,
                "is_knockout_stage": 0,
                "competition_prestige": 1.0,
            }

        # 3.5 ENHANCE features with seasonal statistics (for ML models trained with enhanced data)
        features = enrich_features_with_seasonal_stats(features, home_id, away_id, SEASONAL_STATS)
        print(f"DEBUG: Enhanced features with seasonal stats - total keys: {len(features)}")

        # 4. Predict
        result = predictor.predict_fixture(features)

        # 4.5 Validate prediction consistency
        validate_prediction_consistency(result, features)

        # 5. Enrich features with Elo ratings for analysis
        elo_ratings = result.get("elo_ratings", {})
        enriched_features = {
            **features,
            "home_elo": elo_ratings.get("home", 1500),
            "away_elo": elo_ratings.get("away", 1500),
            "home_rank": features.get("home_league_pos", 10),
            "away_rank": features.get("away_league_pos", 10),
        }
        print(
            f"DEBUG: enriched_features home_elo={enriched_features.get('home_elo')}, away_elo={enriched_features.get('away_elo')}, home_rank={enriched_features.get('home_rank')}, away_rank={enriched_features.get('away_rank')}"
        )

        # 6. Generate comprehensive analysis text using polished AnalysisLLM
        analysis = analysis_llm.analyze(result, enriched_features)

        # Track prediction stats
        ensemble_confidence = max(
            result["home_win_prob"], result["draw_prob"], result["away_win_prob"]
        )
        stats_tracker.record_prediction(result.get("model_breakdown", {}), ensemble_confidence)

        # Log prediction for feedback learning system
        try:
            log_feedback_prediction(
                fixture_id=fixture_id,
                home_team=fixture["teams"]["home"]["name"],
                away_team=fixture["teams"]["away"]["name"],
                league_id=league,
                league_name=fixture.get("league", {}).get("name", "Unknown"),
                match_date=fixture["fixture"]["date"],
                prediction=result,
                model_breakdown=result.get("model_breakdown", {}),
            )
        except Exception as e:
            print(f"Warning: Failed to log prediction for feedback: {e}")

        response_payload = {"prediction": result, "fixture_details": fixture, "analysis": analysis}

        # Cache the prediction for short-term reuse
        if cache_key:
            try:
                ttl = 300 if near_kickoff else 600
                prediction_cache.set(cache_key, response_payload, ttl=ttl)
            except Exception as e:
                print(f"Prediction cache set failed: {e}")

        return response_payload

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

    predicted_score = result.get("predicted_scoreline", "0-0")
    btts_prob = result.get("btts_prob", 0)
    over25_prob = result.get("over25_prob", 0)
    home_prob = result.get("home_win_prob", 0)
    draw_prob = result.get("draw_prob", 0)
    away_prob = result.get("away_win_prob", 0)

    # Parse predicted scoreline
    try:
        h_goals, a_goals = map(int, predicted_score.split("-"))

        # Check 1: BTTS vs Scoreline
        if btts_prob > 0.50 and (h_goals == 0 or a_goals == 0):
            warnings.append(
                f"⚠️ BTTS is {btts_prob*100:.0f}% but predicted score is {predicted_score} (only one team scores)"
            )
        elif btts_prob < 0.35 and h_goals >= 1 and a_goals >= 1:
            warnings.append(
                f"⚠️ BTTS is only {btts_prob*100:.0f}% but predicted score is {predicted_score} (both teams score)"
            )

        # Check 2: Over 2.5 vs Scoreline
        total_goals = h_goals + a_goals
        if over25_prob > 0.55 and total_goals <= 2:
            warnings.append(
                f"⚠️ Over 2.5 is {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} total goals)"
            )
        elif over25_prob < 0.35 and total_goals > 3:
            warnings.append(
                f"⚠️ Over 2.5 is only {over25_prob*100:.0f}% but predicted score is {predicted_score} ({total_goals} goals)"
            )

        # Check 3: Scoreline vs Outcome Probability
        if h_goals > a_goals and home_prob < 0.40:
            warnings.append(
                f"⚠️ Home win predicted ({predicted_score}) but home win probability is only {home_prob*100:.0f}%"
            )
        elif a_goals > h_goals and away_prob < 0.40:
            warnings.append(
                f"⚠️ Away win predicted ({predicted_score}) but away win probability is only {away_prob*100:.0f}%"
            )
        elif h_goals == a_goals and draw_prob < 0.25:
            warnings.append(
                f"⚠️ Draw predicted ({predicted_score}) but draw probability is only {draw_prob*100:.0f}%"
            )

    except Exception as e:
        warnings.append(f"⚠️ Could not validate scoreline: {e}")

    # Check 4: Model breakdown consensus
    model_breakdown = result.get("model_breakdown", {})
    models_favoring_home = 0
    models_favoring_away = 0

    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and "home_win" in preds:
            h, a = preds.get("home_win", 0), preds.get("away_win", 0)
            if h > a:
                models_favoring_home += 1
            elif a > h:
                models_favoring_away += 1

    total_models = models_favoring_home + models_favoring_away
    if total_models > 0:
        if models_favoring_home > models_favoring_away and home_prob < away_prob:
            warnings.append(
                f"⚠️ {models_favoring_home}/{total_models} models favor home but ensemble favors away"
            )
        elif models_favoring_away > models_favoring_home and away_prob < home_prob:
            warnings.append(
                f"⚠️ {models_favoring_away}/{total_models} models favor away but ensemble favors home"
            )

    # Log warnings if any
    if warnings:
        print(
            f"\n🔍 Prediction Validation Warnings for {features.get('home_name', 'Home')} vs {features.get('away_name', 'Away')}:"
        )
        for warning in warnings:
            print(f"   {warning}")

    return {"is_valid": len(warnings) == 0, "warnings": warnings, "warning_count": len(warnings)}


def generate_enhanced_analysis(fixture: dict, features: dict, result: dict) -> str:
    """
    Generate comprehensive match analysis with:
    1. H2H history context
    2. League position context
    3. Model consensus indicator
    4. Rich tactical insights based on goals data
    """
    home_name = fixture["teams"]["home"]["name"]
    away_name = fixture["teams"]["away"]["name"]

    home_prob = result["home_win_prob"] * 100
    draw_prob = result["draw_prob"] * 100
    away_prob = result["away_win_prob"] * 100
    btts_prob = result["btts_prob"] * 100
    over25_prob = result["over25_prob"] * 100

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
        risk_level = "Low risk"
    elif favorite_prob > 55:
        confidence_badge = "🟡 MEDIUM CONFIDENCE"
        risk_level = "Medium risk"
    elif favorite_prob > 40:
        confidence_badge = "🟠 COMPETITIVE MATCH"
        risk_level = "Higher risk - close call"
    else:
        confidence_badge = "🔴 UPSET ALERT"
        risk_level = "High risk - anything can happen"

    # ============================================
    # 2. MODEL CONSENSUS ANALYSIS
    # ============================================
    model_breakdown = result.get("model_breakdown", {})
    models_favoring_home = 0
    models_favoring_away = 0
    models_favoring_draw = 0
    model_opinions = []

    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and "home_win" in preds:
            h, d, a = preds.get("home_win", 0), preds.get("draw", 0), preds.get("away_win", 0)
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
            count = (
                models_favoring_home if consensus_home > consensus_away else models_favoring_away
            )
            consensus_text = f"⚖️ **Moderate Consensus**: {count} of {total_models} models lean toward {majority}. Model agreement supports the prediction."
        else:
            consensus_text = f"⚠️ **Models Divided**: Our AI models are split ({models_favoring_home} for {home_name}, {models_favoring_away} for {away_name}, {models_favoring_draw} for Draw). This match is highly unpredictable."
    else:
        consensus_text = ""

    # ============================================
    # 3. HEAD-TO-HEAD HISTORY
    # ============================================
    h2h_home = features.get("h2h_home_wins", 0)
    h2h_draws = features.get("h2h_draws", 0)
    h2h_away = features.get("h2h_away_wins", 0)
    h2h_total = features.get("h2h_total_matches", 0)

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
    home_pos = features.get("home_league_pos", 10)
    away_pos = features.get("away_league_pos", 10)
    home_pts = features.get("home_league_points", 0)
    away_pts = features.get("away_league_points", 0)

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
    home_gf_avg = features.get("home_goals_for_avg", 1.3)
    home_ga_avg = features.get("home_goals_against_avg", 1.2)
    away_gf_avg = features.get("away_goals_for_avg", 1.2)
    away_ga_avg = features.get("away_goals_against_avg", 1.3)

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

    home_clean_sheets = features.get("home_clean_sheets", 0)
    away_clean_sheets = features.get("away_clean_sheets", 0)

    # Team styles
    home_style = (
        "attacking" if home_gf_avg > 1.8 else "balanced" if home_gf_avg > 1.2 else "defensive"
    )
    away_style = (
        "attacking" if away_gf_avg > 1.8 else "balanced" if away_gf_avg > 1.2 else "defensive"
    )
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
    home_form = features.get("home_form_last5", 7)
    away_form = features.get("away_form_last5", 7)
    home_wins_10 = features.get("home_wins_last10", 5)
    away_wins_10 = features.get("away_wins_last10", 5)

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
    elo_ratings = result.get("elo_ratings", {})
    home_elo = elo_ratings.get("home", 1500)
    away_elo = elo_ratings.get("away", 1500)
    elo_diff = elo_ratings.get("diff", 0)

    if abs(elo_diff) > 150:
        better = home_name if elo_diff > 0 else away_name
        away_name if elo_diff > 0 else home_name
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

        # ENHANCE features with seasonal statistics (for ML models trained with enhanced data)
        home_id = features_dict.get("home_id", 0)
        away_id = features_dict.get("away_id", 0)
        features_dict = enrich_features_with_seasonal_stats(
            features_dict, home_id, away_id, SEASONAL_STATS
        )
        print(f"DEBUG: /predict endpoint - Enhanced features, total keys: {len(features_dict)}")

        # Get prediction from ensemble
        result = predictor.predict_fixture(features_dict)

        # Track prediction stats
        ensemble_confidence = max(
            result["home_win_prob"], result["draw_prob"], result["away_win_prob"]
        )
        stats_tracker.record_prediction(result.get("model_breakdown", {}), ensemble_confidence)

        # Log prediction to metrics tracker
        try:
            fixture_id = features_dict.get("fixture_id", 0)
            home_team = features_dict.get("home_team", "Unknown")
            away_team = features_dict.get("away_team", "Unknown")
            predicted_score = result.get("predicted_scoreline", "")

            metrics_tracker.log_prediction(
                fixture_id=fixture_id,
                home_team=home_team,
                away_team=away_team,
                home_pred=result["home_win_prob"],
                draw_pred=result["draw_prob"],
                away_pred=result["away_win_prob"],
                predicted_score=predicted_score,
                model_breakdown=result.get("model_breakdown", {}),
            )
        except Exception as e:
            logger.warning(f"Failed to log prediction to metrics: {e}")

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
            "EloGlickoModel",
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
            "monte_carlo": 0.00,  # Auxiliary
        },
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
    record_result,
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
                "fixture_id": p["fixture_id"],
                "home_team": p["home_team"],
                "away_team": p["away_team"],
                "match_date": p["match_date"],
                "predicted_outcome": p["prediction"]["predicted_outcome"],
                "confidence": p["prediction"]["confidence"],
            }
            for p in pending[:20]  # Limit to 20
        ],
    }


@app.post("/api/feedback/record-result")
async def api_record_result(fixture_id: int, home_goals: int, away_goals: int):
    """
    Manually record a match result to evaluate prediction.
    """
    evaluation = record_result(fixture_id, home_goals, away_goals)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="No prediction found for this fixture")

    # Log actual result to metrics tracker
    try:
        # Determine result (H=home, D=draw, A=away)
        if home_goals > away_goals:
            actual_result = "H"
        elif home_goals < away_goals:
            actual_result = "A"
        else:
            actual_result = "D"

        actual_score = f"{home_goals}-{away_goals}"
        metrics_tracker.log_actual_result(fixture_id, actual_result, actual_score)
    except Exception as e:
        logger.warning(f"Failed to log result to metrics: {e}")

    return {"status": "recorded", "evaluation": evaluation}


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
            "weights": {},
        }
    return {"status": "available", "weights": weights}


@app.post("/api/feedback/update-from-api")
async def update_results_from_backend():
    """
    Fetch completed match results from the backend API
    and update the feedback system.
    """
    try:
        from ml_engine.auto_update_results import update_results_from_api

        result = update_results_from_api()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MODEL PERFORMANCE METRICS
# ============================================


@app.get("/api/metrics/summary")
async def get_metrics_summary():
    """
    Get model performance summary including accuracy and calibration.
    7-day, 30-day, and all-time breakdowns.
    """
    try:
        metrics_tracker.export_summary()

        summary_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "metrics", "summary.json"
        )
        if os.path.exists(summary_file):
            with open(summary_file) as f:
                return json.load(f)
        else:
            return {
                "error": "No metrics available yet",
                "message": "Predictions will start being tracked once matches are predicted",
            }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/model-comparison")
async def get_model_comparison():
    """
    Compare individual model performance in the ensemble.
    """
    try:
        return metrics_tracker.get_model_comparison()
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/log-prediction")
async def log_prediction_metric(
    fixture_id: int,
    home_team: str,
    away_team: str,
    home_pred: float,
    draw_pred: float,
    away_pred: float,
    predicted_score: str,
    model_breakdown: Optional[Dict] = None,
):
    """
    Log a prediction for later accuracy tracking.
    Call this endpoint when making predictions.
    """
    try:
        metrics_tracker.log_prediction(
            fixture_id=fixture_id,
            home_team=home_team,
            away_team=away_team,
            home_pred=home_pred,
            draw_pred=draw_pred,
            away_pred=away_pred,
            predicted_score=predicted_score,
            model_breakdown=model_breakdown,
        )
        return {"status": "logged", "fixture_id": fixture_id}
    except Exception as e:
        logger.error(f"Error logging prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/log-result")
async def log_actual_result(fixture_id: int, actual_result: str, actual_score: str):
    """
    Log actual match result (H/D/A) to calculate prediction accuracy.
    Call this when match is finished.
    """
    try:
        metrics_tracker.log_actual_result(fixture_id, actual_result, actual_score)
        return {"status": "updated", "fixture_id": fixture_id}
    except Exception as e:
        logger.error(f"Error logging result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FixtureCast ML API server on port {port}...")
    print(f"API docs will be available at http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
