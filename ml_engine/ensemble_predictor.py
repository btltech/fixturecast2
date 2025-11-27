import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import numpy as np

from .bayesian_model import BayesianModel
from .calibration import CalibrationModel
from .catboost_model import CatBoostModel
from .confidence_intervals import calculate_confidence_intervals
from .elo_model import EloGlickoModel
from .elo_tracker import EloTracker
from .gbdt_model import GBDTModel
from .gnn_model import GNNModel
from .lstm_model import LSTMSequenceModel
from .monte_carlo import MonteCarloSimulator
from .poisson_model import PoissonModel
from .transformer_model import TransformerSequenceModel

# SHAP for model explanations (optional dependency)
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    def __init__(self, load_trained=True):
        print("DEBUG: Loaded EnsemblePredictor v5 - with vectorizers")
        models_dir = os.path.join(os.path.dirname(__file__), "trained_models")

        # Load feature vectorizers for each model (CRITICAL for proper predictions)
        self.vectorizers = {}
        self._load_vectorizers(models_dir)

        # Initialize models - load from disk if available, else create fresh
        if load_trained and os.path.exists(models_dir):
            self.gbdt = self._load_or_create(GBDTModel, os.path.join(models_dir, "gbdt_model.pkl"))
            self.catboost = self._load_or_create(
                CatBoostModel, os.path.join(models_dir, "catboost_model.pkl")
            )
            self.poisson = self._load_or_create(
                PoissonModel, os.path.join(models_dir, "poisson_model.pkl")
            )
            self.transformer = self._load_or_create(
                TransformerSequenceModel, os.path.join(models_dir, "transformer_model.pkl")
            )
            self.lstm = self._load_or_create(
                LSTMSequenceModel, os.path.join(models_dir, "lstm_model.pkl")
            )
            self.gnn = self._load_or_create(GNNModel, os.path.join(models_dir, "gnn_model.pkl"))
            self.bayesian = self._load_or_create(
                BayesianModel, os.path.join(models_dir, "bayesian_model.pkl")
            )
            self.elo = self._load_or_create(
                EloGlickoModel, os.path.join(models_dir, "elo_model.pkl")
            )
        else:
            # Create fresh models
            self.gbdt = GBDTModel()
            self.catboost = CatBoostModel()
            self.poisson = PoissonModel()
            self.transformer = TransformerSequenceModel()
            self.lstm = LSTMSequenceModel()
            self.gnn = GNNModel()
            self.bayesian = BayesianModel()
            self.elo = EloGlickoModel()

        self.mc = MonteCarloSimulator()
        self.calibration = CalibrationModel()

        # Load TRUE Elo tracker if available (enhanced)
        self.elo_tracker = None
        elo_ratings_path = os.path.join(models_dir, "elo_ratings.json")
        if os.path.exists(elo_ratings_path):
            try:
                self.elo_tracker = EloTracker()
                self.elo_tracker.load(elo_ratings_path)
                print(f"Loaded true Elo ratings for {len(self.elo_tracker.ratings)} teams")
            except Exception as e:
                print(f"Failed to load Elo tracker: {e}")

        # Load meta-model if exists
        self.meta_model = None
        meta_path = os.path.join(models_dir, "meta_model.pkl")
        if os.path.exists(meta_path):
            try:
                import joblib

                meta_data = joblib.load(meta_path)
                if isinstance(meta_data, dict):
                    self.meta_model = meta_data.get("model")
                    self.meta_feature_keys = meta_data.get("feature_keys", [])
                else:
                    self.meta_model = meta_data
                print("Loaded trained meta-model.")
            except Exception as e:
                print(f"Failed to load meta-model: {e}")

    def _load_or_create(self, model_class, path):
        """Load model from disk if exists, else create fresh.

        IMPORTANT: We load the pickled state (trained sklearn model, feature_keys, etc.)
        but transfer it to a fresh instance of the class. This ensures we use
        the current code (without local numpy imports) rather than the pickled
        methods which may have bugs.
        """
        if os.path.exists(path):
            try:
                import joblib

                loaded = joblib.load(path)
                # Create fresh instance with current code
                fresh_model = model_class()
                # Copy over the trained state (sklearn model, feature_keys, etc.)
                if hasattr(loaded, "__dict__"):
                    fresh_model.__dict__.update(loaded.__dict__)
                print(
                    f"Loaded trained {model_class.__name__} (state transferred to fresh instance)"
                )
                return fresh_model
            except Exception as e:
                print(f"Failed to load {model_class.__name__}, creating fresh: {e}")
        return model_class()

    def _load_vectorizers(self, models_dir):
        """Load all DictVectorizers saved during training for proper feature transformation"""
        vectorizer_files = {
            "main": "feature_vectorizer.pkl",  # For GBDT, CatBoost
            "transformer": "transformer_vectorizer.pkl",
            "lstm": "lstm_vectorizer.pkl",
            "gnn": "gnn_vectorizer.pkl",
            "bayesian": "bayesian_vectorizer.pkl",
            "elo": "elo_vectorizer.pkl",
        }

        for name, filename in vectorizer_files.items():
            path = os.path.join(models_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        self.vectorizers[name] = pickle.load(f)
                    print(
                        f"  Loaded {name} vectorizer ({len(self.vectorizers[name].get_feature_names_out())} features)"
                    )
                except Exception as e:
                    print(f"  Warning: Failed to load {name} vectorizer: {e}")

    def load_artifacts(self, artifact_dir):
        # Load all models from specified directory
        pass

    def _vectorize_features(self, features_dict, vectorizer_name):
        """Convert feature dict to numpy array using the appropriate vectorizer"""
        if vectorizer_name not in self.vectorizers:
            return None

        vec = self.vectorizers[vectorizer_name]
        try:
            # DictVectorizer.transform expects a list of dicts
            X = vec.transform([features_dict])
            return X
        except Exception as e:
            print(f"  Vectorization error for {vectorizer_name}: {e}")
            return None

    def _safe_predict(self, model, features_dict, vectorizer_name="main"):
        """
        Helper to handle sklearn models that need feature arrays.
        Tries multiple methods in order of reliability.
        """
        # Method 1: Use model's feature_keys (most reliable for GBDT/CatBoost)
        if (
            hasattr(model, "feature_keys")
            and model.feature_keys
            and hasattr(model, "model")
            and model.model is not None
        ):
            try:
                X = np.array([[features_dict.get(k, 0) for k in model.feature_keys]])
                probs = model.model.predict_proba(X)[0]
                if len(probs) == 3:
                    return {
                        "home_win": round(float(probs[0]), 4),
                        "draw": round(float(probs[1]), 4),
                        "away_win": round(float(probs[2]), 4),
                    }
            except Exception as e:
                logger.debug(f"Feature_keys prediction error for {type(model).__name__}: {e}")

        # Method 2: Try using vectorizer to transform features
        X = self._vectorize_features(features_dict, vectorizer_name)
        if X is not None and hasattr(model, "model") and model.model is not None:
            try:
                probs = model.model.predict_proba(X)[0]
                if len(probs) == 3:
                    return {
                        "home_win": round(float(probs[0]), 4),
                        "draw": round(float(probs[1]), 4),
                        "away_win": round(float(probs[2]), 4),
                    }
            except Exception as e:
                logger.debug(f"Vectorized prediction error for {type(model).__name__}: {e}")

        # Method 3: Use model's own predict method (heuristic fallback)
        return model.predict(features_dict)

    def predict_fixture(self, features):
        print("DEBUG: predict_fixture v4 called")

        # 1. Get predictions from all models (using correct vectorizers)
        p_gbdt = self._safe_predict(self.gbdt, features, "main")
        p_cat = self._safe_predict(self.catboost, features, "main")
        p_trans = self._safe_predict(self.transformer, features, "transformer")
        p_lstm = self._safe_predict(self.lstm, features, "lstm")
        p_gnn = self._safe_predict(self.gnn, features, "gnn")
        p_bayes = self._safe_predict(self.bayesian, features, "bayesian")

        # Use TRUE Elo tracker if available, else fallback to heuristic
        if self.elo_tracker:
            home_id = features.get("home_id", 0)
            away_id = features.get("away_id", 0)
            p_elo = self.elo_tracker.predict_match(home_id, away_id)
            # Add Elo ratings to features for display
            features["home_elo_rating"] = p_elo.get("home_rating", 1500)
            features["away_elo_rating"] = p_elo.get("away_rating", 1500)
        else:
            p_elo = self.elo.predict(features.get("home_id"), features.get("away_id"), features)

        # Poisson & Monte Carlo
        lambdas = self.poisson.predict(features)
        mc_res = self.mc.simulate(lambdas["home_lambda"], lambdas["away_lambda"])

        # 2. Ensemble (Weighted Average)
        # More balanced weights to prevent domination by 2 models
        # Distribution ensures diverse model opinions are heard
        weights = {
            "gbdt": 0.22,  # Trained model with enhanced features
            "elo": 0.22,  # True Elo ratings
            "gnn": 0.18,  # League context
            "lstm": 0.14,  # Form trends
            "bayesian": 0.10,  # Odds-based
            "transformer": 0.08,  # Sequence patterns
            "catboost": 0.06,  # Goals-based predictor
        }

        # Calculate weighted sum
        w_home = (
            p_gbdt["home_win"] * weights["gbdt"]
            + p_elo["home_win"] * weights["elo"]
            + p_gnn["home_win"] * weights["gnn"]
            + p_lstm["home_win"] * weights["lstm"]
            + p_bayes["home_win"] * weights["bayesian"]
            + p_trans["home_win"] * weights["transformer"]
            + p_cat["home_win"] * weights["catboost"]
        )

        w_draw = (
            p_gbdt["draw"] * weights["gbdt"]
            + p_elo["draw"] * weights["elo"]
            + p_gnn["draw"] * weights["gnn"]
            + p_lstm["draw"] * weights["lstm"]
            + p_bayes["draw"] * weights["bayesian"]
            + p_trans["draw"] * weights["transformer"]
            + p_cat["draw"] * weights["catboost"]
        )

        w_away = (
            p_gbdt["away_win"] * weights["gbdt"]
            + p_elo["away_win"] * weights["elo"]
            + p_gnn["away_win"] * weights["gnn"]
            + p_lstm["away_win"] * weights["lstm"]
            + p_bayes["away_win"] * weights["bayesian"]
            + p_trans["away_win"] * weights["transformer"]
            + p_cat["away_win"] * weights["catboost"]
        )

        # Normalize (just in case weights don't sum exactly to 1)
        total_w = sum(weights.values())
        avg_home = w_home / total_w
        avg_draw = w_draw / total_w
        avg_away = w_away / total_w

        # 3. Calibration
        # Apply temperature scaling to sharpen/soften predictions
        probs = {"home_win": avg_home, "draw": avg_draw, "away_win": avg_away}
        calibrated = self.calibration.calibrate(probs)

        # 4. Construct response
        # Find most likely scoreline using intelligent weighted selection
        if mc_res["score_dist"]:
            home_prob = calibrated["home_win_prob"]
            draw_prob = calibrated["draw_prob"]
            away_prob = calibrated["away_win_prob"]
            btts_prob = mc_res["btts_prob"]
            over25_prob = mc_res["over25_prob"]

            score_dist = mc_res["score_dist"]

            # Categorize scores by outcome
            home_win_scores = {}
            draw_scores = {}
            away_win_scores = {}

            for score, count in score_dist.items():
                h, a = int(score.split("-")[0]), int(score.split("-")[1])
                if h > a:
                    home_win_scores[score] = count
                elif h == a:
                    draw_scores[score] = count
                else:
                    away_win_scores[score] = count

            # Calculate weighted probability for each score
            # Enhanced: Consider outcome probability + BTTS/Over2.5 alignment
            total_mc = sum(score_dist.values())
            weighted_scores = {}

            for score, count in home_win_scores.items():
                h, a = int(score.split("-")[0]), int(score.split("-")[1])
                mc_prob = count / total_mc
                base_weight = mc_prob * home_prob

                # Bonus for BTTS/Over2.5 alignment
                btts_bonus = 1.3 if (h >= 1 and a >= 1 and btts_prob > 0.45) else 1.0
                over25_bonus = 1.2 if ((h + a > 2.5) and over25_prob > 0.45) else 1.0

                weighted_scores[score] = base_weight * btts_bonus * over25_bonus

            for score, count in draw_scores.items():
                h, a = int(score.split("-")[0]), int(score.split("-")[1])
                mc_prob = count / total_mc
                base_weight = mc_prob * draw_prob

                # Bonus for BTTS/Over2.5 alignment
                btts_bonus = 1.3 if (h >= 1 and a >= 1 and btts_prob > 0.45) else 1.0
                over25_bonus = 1.2 if ((h + a > 2.5) and over25_prob > 0.45) else 1.0

                weighted_scores[score] = base_weight * btts_bonus * over25_bonus

            for score, count in away_win_scores.items():
                h, a = int(score.split("-")[0]), int(score.split("-")[1])
                mc_prob = count / total_mc
                base_weight = mc_prob * away_prob

                # Bonus for BTTS/Over2.5 alignment
                btts_bonus = 1.3 if (h >= 1 and a >= 1 and btts_prob > 0.45) else 1.0
                over25_bonus = 1.2 if ((h + a > 2.5) and over25_prob > 0.45) else 1.0

                weighted_scores[score] = base_weight * btts_bonus * over25_bonus

            # Pick score with highest weighted probability
            if weighted_scores:
                most_likely_score = max(weighted_scores.items(), key=lambda x: x[1])[0]
            else:
                most_likely_score = max(score_dist.items(), key=lambda x: x[1])[0]
        else:
            # Fallback based on predicted outcome
            if calibrated["home_win_prob"] > calibrated["away_win_prob"]:
                most_likely_score = (
                    "1-0" if calibrated["home_win_prob"] > calibrated["draw_prob"] else "1-1"
                )
            elif calibrated["away_win_prob"] > calibrated["draw_prob"]:
                most_likely_score = "0-1"
            else:
                most_likely_score = "1-1"

        # 5. Calculate confidence intervals based on model variance
        confidence_intervals = calculate_confidence_intervals(
            calibrated,
            {
                "gbdt": p_gbdt,
                "catboost": p_cat,
                "transformer": p_trans,
                "lstm": p_lstm,
                "gnn": p_gnn,
                "bayesian": p_bayes,
                "elo": p_elo,
            },
        )

        return {
            "home_win_prob": calibrated["home_win_prob"],
            "draw_prob": calibrated["draw_prob"],
            "away_win_prob": calibrated["away_win_prob"],
            "predicted_scoreline": most_likely_score,
            "btts_prob": mc_res["btts_prob"],
            "over25_prob": mc_res["over25_prob"],
            "scoreline_distribution": mc_res["score_dist"],
            "confidence_intervals": confidence_intervals,  # NEW: Uncertainty ranges
            "elo_ratings": {
                "home": p_elo.get("home_rating", features.get("home_elo_rating", 1500)),
                "away": p_elo.get("away_rating", features.get("away_elo_rating", 1500)),
                "diff": p_elo.get("rating_diff", 0),
            },
            "model_breakdown": {
                "gbdt": p_gbdt,
                "catboost": p_cat,
                "transformer": p_trans,
                "lstm": p_lstm,
                "gnn": p_gnn,
                "bayesian": p_bayes,
                "elo": p_elo,
                "monte_carlo": mc_res,
            },
        }

    def explain_prediction(self, features: Dict[str, Any], top_k: int = 10) -> Dict[str, Any]:
        """
        Generate SHAP-based explanations for a prediction.

        Args:
            features: Dictionary of match features
            top_k: Number of top contributing features to return

        Returns:
            Dictionary with feature importance explanations
        """
        if not SHAP_AVAILABLE:
            logger.warning("SHAP not available - returning feature-based explanation")
            return self._fallback_explanation(features, top_k)

        try:
            # Get the underlying GBDT/CatBoost model for SHAP (tree-based = fast SHAP)
            explanations = {}

            # GBDT explanation (most reliable for tree-based SHAP)
            if hasattr(self.gbdt, "model") and self.gbdt.model is not None:
                gbdt_explanation = self._explain_gbdt(features, top_k)
                if gbdt_explanation:
                    explanations["gbdt"] = gbdt_explanation

            # CatBoost explanation
            if hasattr(self.catboost, "model") and self.catboost.model is not None:
                catboost_explanation = self._explain_catboost(features, top_k)
                if catboost_explanation:
                    explanations["catboost"] = catboost_explanation

            # Aggregate explanations across models
            aggregated = self._aggregate_explanations(explanations, top_k)

            return {
                "shap_available": True,
                "top_features": aggregated,
                "model_explanations": explanations,
                "interpretation": self._generate_interpretation(aggregated, features),
            }

        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return self._fallback_explanation(features, top_k)

    def _explain_gbdt(self, features: Dict[str, Any], top_k: int) -> Optional[Dict]:
        """Generate SHAP explanation for GBDT model."""
        try:
            # Get vectorizer for GBDT
            vectorizer = self.vectorizers.get("gbdt")
            if vectorizer is None:
                return None

            # Transform features to model format
            feature_vector = vectorizer.transform([features])
            feature_names = (
                vectorizer.get_feature_names_out()
                if hasattr(vectorizer, "get_feature_names_out")
                else [f"feature_{i}" for i in range(feature_vector.shape[1])]
            )

            # Create TreeExplainer for GBDT
            explainer = shap.TreeExplainer(self.gbdt.model)
            shap_values = explainer.shap_values(feature_vector)

            # Handle multi-class output
            if isinstance(shap_values, list):
                # Take the class with highest prediction
                shap_values = np.abs(shap_values).mean(axis=0)

            # Get top contributing features
            importance = np.abs(shap_values[0])
            top_indices = np.argsort(importance)[-top_k:][::-1]

            return {
                "features": [
                    {
                        "name": feature_names[i],
                        "importance": float(importance[i]),
                        "value": (
                            float(feature_vector[0, i])
                            if hasattr(feature_vector, "__getitem__")
                            else None
                        ),
                    }
                    for i in top_indices
                ],
                "base_value": (
                    float(explainer.expected_value)
                    if hasattr(explainer.expected_value, "__float__")
                    else None
                ),
            }
        except Exception as e:
            logger.debug(f"GBDT SHAP failed: {e}")
            return None

    def _explain_catboost(self, features: Dict[str, Any], top_k: int) -> Optional[Dict]:
        """Generate SHAP explanation for CatBoost model."""
        try:
            vectorizer = self.vectorizers.get("catboost")
            if vectorizer is None:
                return None

            feature_vector = vectorizer.transform([features])
            feature_names = (
                vectorizer.get_feature_names_out()
                if hasattr(vectorizer, "get_feature_names_out")
                else [f"feature_{i}" for i in range(feature_vector.shape[1])]
            )

            # CatBoost has built-in SHAP support
            shap_values = self.catboost.model.get_feature_importance(
                data=feature_vector, type="ShapValues"
            )

            importance = np.abs(shap_values[0, :-1])  # Exclude bias term
            top_indices = np.argsort(importance)[-top_k:][::-1]

            return {
                "features": [
                    {
                        "name": feature_names[i],
                        "importance": float(importance[i]),
                        "value": (
                            float(feature_vector[0, i])
                            if hasattr(feature_vector, "__getitem__")
                            else None
                        ),
                    }
                    for i in top_indices
                ]
            }
        except Exception as e:
            logger.debug(f"CatBoost SHAP failed: {e}")
            return None

    def _aggregate_explanations(self, explanations: Dict, top_k: int) -> List[Dict]:
        """Aggregate feature importance across multiple model explanations."""
        feature_scores = {}

        for model_name, explanation in explanations.items():
            if "features" not in explanation:
                continue
            for feat in explanation["features"]:
                name = feat["name"]
                importance = feat["importance"]
                if name in feature_scores:
                    feature_scores[name]["importance"] += importance
                    feature_scores[name]["count"] += 1
                else:
                    feature_scores[name] = {
                        "name": name,
                        "importance": importance,
                        "count": 1,
                        "value": feat.get("value"),
                    }

        # Average and sort
        for name in feature_scores:
            feature_scores[name]["importance"] /= feature_scores[name]["count"]

        sorted_features = sorted(
            feature_scores.values(), key=lambda x: x["importance"], reverse=True
        )[:top_k]

        return sorted_features

    def _fallback_explanation(self, features: Dict[str, Any], top_k: int) -> Dict[str, Any]:
        """Provide a fallback explanation when SHAP is not available."""
        # Use domain knowledge to explain key features
        important_features = [
            ("home_form", "Home team's recent form"),
            ("away_form", "Away team's recent form"),
            ("home_elo_rating", "Home team's Elo rating"),
            ("away_elo_rating", "Away team's Elo rating"),
            ("h2h_home_wins", "Head-to-head home wins"),
            ("home_goals_scored_avg", "Home team avg goals scored"),
            ("away_goals_scored_avg", "Away team avg goals scored"),
            ("home_goals_conceded_avg", "Home team avg goals conceded"),
            ("away_goals_conceded_avg", "Away team avg goals conceded"),
            ("home_win_rate", "Home team win rate"),
        ]

        explanations = []
        for feature_key, description in important_features[:top_k]:
            if feature_key in features:
                explanations.append(
                    {
                        "name": feature_key,
                        "description": description,
                        "value": features[feature_key],
                        "importance": None,  # Unknown without SHAP
                    }
                )

        return {
            "shap_available": False,
            "top_features": explanations,
            "interpretation": "SHAP analysis not available. Showing key match features.",
            "note": "Install 'shap' package for detailed model explanations: pip install shap",
        }

    def _generate_interpretation(self, top_features: List[Dict], features: Dict) -> str:
        """Generate a natural language interpretation of feature importance."""
        if not top_features:
            return "Unable to generate interpretation."

        interpretations = []
        for feat in top_features[:3]:  # Top 3 features
            name = feat["name"]
            feat.get("importance", 0)

            # Map feature names to readable descriptions
            if "elo" in name.lower():
                interpretations.append(f"Team strength rating ({name})")
            elif "form" in name.lower():
                interpretations.append(f"Recent form ({name})")
            elif "goals_scored" in name.lower():
                interpretations.append(f"Attacking capability ({name})")
            elif "goals_conceded" in name.lower():
                interpretations.append(f"Defensive strength ({name})")
            elif "h2h" in name.lower():
                interpretations.append(f"Head-to-head history ({name})")
            elif "win_rate" in name.lower():
                interpretations.append(f"Overall win percentage ({name})")
            else:
                interpretations.append(name.replace("_", " ").title())

        if interpretations:
            return f"Prediction primarily influenced by: {', '.join(interpretations)}"
        return "Prediction based on ensemble of 11 models."
