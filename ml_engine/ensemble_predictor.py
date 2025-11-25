
import json
import os
import numpy as np
from .gbdt_model import GBDTModel
from .catboost_model import CatBoostModel
from .poisson_model import PoissonModel
from .transformer_model import TransformerSequenceModel
from .lstm_model import LSTMSequenceModel
from .gnn_model import GNNModel
from .bayesian_model import BayesianModel
from .elo_model import EloGlickoModel
from .monte_carlo import MonteCarloSimulator
from .calibration import CalibrationModel
from .elo_tracker import EloTracker
from .confidence_intervals import calculate_confidence_intervals

class EnsemblePredictor:
    def __init__(self, load_trained=True):
        models_dir = os.path.join(os.path.dirname(__file__), "trained_models")
        
        # Initialize models - load from disk if available, else create fresh
        if load_trained and os.path.exists(models_dir):
            self.gbdt = self._load_or_create(GBDTModel, os.path.join(models_dir, "gbdt_model.pkl"))
            self.catboost = self._load_or_create(CatBoostModel, os.path.join(models_dir, "catboost_model.pkl"))
            self.poisson = self._load_or_create(PoissonModel, os.path.join(models_dir, "poisson_model.pkl"))
            self.transformer = self._load_or_create(TransformerSequenceModel, os.path.join(models_dir, "transformer_model.pkl"))
            self.lstm = self._load_or_create(LSTMSequenceModel, os.path.join(models_dir, "lstm_model.pkl"))
            self.gnn = self._load_or_create(GNNModel, os.path.join(models_dir, "gnn_model.pkl"))
            self.bayesian = self._load_or_create(BayesianModel, os.path.join(models_dir, "bayesian_model.pkl"))
            self.elo = self._load_or_create(EloGlickoModel, os.path.join(models_dir, "elo_model.pkl"))
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
                    self.meta_model = meta_data.get('model')
                    self.meta_feature_keys = meta_data.get('feature_keys', [])
                else:
                    self.meta_model = meta_data
                print("Loaded trained meta-model.")
            except Exception as e:
                print(f"Failed to load meta-model: {e}")
    
    def _load_or_create(self, model_class, path):
        """Load model from disk if exists, else create fresh"""
        if os.path.exists(path):
            try:
                import joblib
                model = joblib.load(path)
                print(f"Loaded trained {model_class.__name__}")
                return model
            except Exception as e:
                print(f"Failed to load {model_class.__name__}, creating fresh: {e}")
        return model_class()
        
    def load_artifacts(self, artifact_dir):
        # Load all models from specified directory
        pass

    def predict_fixture(self, features):
        import numpy as np
        
        # Helper function to handle sklearn models that need feature arrays
        def safe_predict(model, features_dict):
            # Check if it's an sklearn model (has fit/predict_proba but not from our wrappers)
            if hasattr(model, 'feature_keys') and hasattr(model, 'predict_proba'):
                # It's a trained sklearn model with feature_keys attached
                X = np.array([[features_dict.get(k, 0) for k in model.feature_keys]])
                probs = model.predict_proba(X)[0]
                # Return in expected format
                if len(probs) == 3:
                    # Assuming class order: check classes_ attribute
                    return {
                        "home_win": round(float(probs[2]), 4),
                        "draw": round(float(probs[1]), 4),
                        "away_win": round(float(probs[0]), 4)
                    }
            # Not sklearn or doesn't have feature_keys, use model's own predict
            return model.predict(features_dict)
        
        # 1. Get predictions from all models
        p_gbdt = safe_predict(self.gbdt, features)
        p_cat = safe_predict(self.catboost, features)
        p_trans = self.transformer.predict(features)
        p_lstm = self.lstm.predict(features)
        p_gnn = self.gnn.predict(features)
        p_bayes = self.bayesian.predict(features)
        
        # Use TRUE Elo tracker if available, else fallback to heuristic
        if self.elo_tracker:
            home_id = features.get('home_id', 0)
            away_id = features.get('away_id', 0)
            p_elo = self.elo_tracker.predict_match(home_id, away_id)
            # Add Elo ratings to features for display
            features['home_elo_rating'] = p_elo.get('home_rating', 1500)
            features['away_elo_rating'] = p_elo.get('away_rating', 1500)
        else:
            p_elo = self.elo.predict(features.get('home_id'), features.get('away_id'), features)
        
        # Poisson & Monte Carlo
        lambdas = self.poisson.predict(features)
        mc_res = self.mc.simulate(lambdas['home_lambda'], lambdas['away_lambda'])
        
        # 2. Ensemble (Weighted Average)
        # More balanced weights to prevent domination by 2 models
        # Distribution ensures diverse model opinions are heard
        weights = {
            'gbdt': 0.22,      # Trained model with enhanced features
            'elo': 0.22,       # True Elo ratings
            'gnn': 0.18,       # League context
            'lstm': 0.14,      # Form trends
            'bayesian': 0.10,  # Odds-based
            'transformer': 0.08,  # Sequence patterns
            'catboost': 0.06,  # Goals-based predictor
        }
        
        # Calculate weighted sum
        w_home = (
            p_gbdt['home_win'] * weights['gbdt'] +
            p_elo['home_win'] * weights['elo'] +
            p_gnn['home_win'] * weights['gnn'] +
            p_lstm['home_win'] * weights['lstm'] +
            p_bayes['home_win'] * weights['bayesian'] +
            p_trans['home_win'] * weights['transformer'] +
            p_cat['home_win'] * weights['catboost']
        )
        
        w_draw = (
            p_gbdt['draw'] * weights['gbdt'] +
            p_elo['draw'] * weights['elo'] +
            p_gnn['draw'] * weights['gnn'] +
            p_lstm['draw'] * weights['lstm'] +
            p_bayes['draw'] * weights['bayesian'] +
            p_trans['draw'] * weights['transformer'] +
            p_cat['draw'] * weights['catboost']
        )
        
        w_away = (
            p_gbdt['away_win'] * weights['gbdt'] +
            p_elo['away_win'] * weights['elo'] +
            p_gnn['away_win'] * weights['gnn'] +
            p_lstm['away_win'] * weights['lstm'] +
            p_bayes['away_win'] * weights['bayesian'] +
            p_trans['away_win'] * weights['transformer'] +
            p_cat['away_win'] * weights['catboost']
        )
        
        # Normalize (just in case weights don't sum exactly to 1)
        total_w = sum(weights.values())
        avg_home = w_home / total_w
        avg_draw = w_draw / total_w
        avg_away = w_away / total_w
        
        # 3. Calibration
        # Apply temperature scaling to sharpen/soften predictions
        probs = {
            "home_win": avg_home,
            "draw": avg_draw,
            "away_win": avg_away
        }
        calibrated = self.calibration.calibrate(probs)
        
        # 4. Construct response
        # Find most likely scoreline using intelligent weighted selection
        if mc_res['score_dist']:
            home_prob = calibrated["home_win_prob"]
            draw_prob = calibrated["draw_prob"]
            away_prob = calibrated["away_win_prob"]
            btts_prob = mc_res['btts_prob']
            over25_prob = mc_res['over25_prob']
            
            score_dist = mc_res['score_dist']
            
            # Categorize scores by outcome
            home_win_scores = {}
            draw_scores = {}
            away_win_scores = {}
            
            for score, count in score_dist.items():
                h, a = int(score.split('-')[0]), int(score.split('-')[1])
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
                h, a = int(score.split('-')[0]), int(score.split('-')[1])
                mc_prob = count / total_mc
                base_weight = mc_prob * home_prob
                
                # Bonus for BTTS/Over2.5 alignment
                btts_bonus = 1.3 if (h >= 1 and a >= 1 and btts_prob > 0.45) else 1.0
                over25_bonus = 1.2 if ((h + a > 2.5) and over25_prob > 0.45) else 1.0
                
                weighted_scores[score] = base_weight * btts_bonus * over25_bonus
                
            for score, count in draw_scores.items():
                h, a = int(score.split('-')[0]), int(score.split('-')[1])
                mc_prob = count / total_mc
                base_weight = mc_prob * draw_prob
                
                # Bonus for BTTS/Over2.5 alignment
                btts_bonus = 1.3 if (h >= 1 and a >= 1 and btts_prob > 0.45) else 1.0
                over25_bonus = 1.2 if ((h + a > 2.5) and over25_prob > 0.45) else 1.0
                
                weighted_scores[score] = base_weight * btts_bonus * over25_bonus
                
            for score, count in away_win_scores.items():
                h, a = int(score.split('-')[0]), int(score.split('-')[1])
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
                most_likely_score = "1-0" if calibrated["home_win_prob"] > calibrated["draw_prob"] else "1-1"
            elif calibrated["away_win_prob"] > calibrated["draw_prob"]:
                most_likely_score = "0-1"
            else:
                most_likely_score = "1-1"
        
        # 5. Calculate confidence intervals based on model variance
        confidence_intervals = calculate_confidence_intervals(calibrated, {
            'gbdt': p_gbdt,
            'catboost': p_cat,
            'transformer': p_trans,
            'lstm': p_lstm,
            'gnn': p_gnn,
            'bayesian': p_bayes,
            'elo': p_elo
        })
        
        return {
            "home_win_prob": calibrated["home_win_prob"],
            "draw_prob": calibrated["draw_prob"],
            "away_win_prob": calibrated["away_win_prob"],
            "predicted_scoreline": most_likely_score,
            "btts_prob": mc_res['btts_prob'],
            "over25_prob": mc_res['over25_prob'],
            "scoreline_distribution": mc_res['score_dist'],
            "confidence_intervals": confidence_intervals,  # NEW: Uncertainty ranges
            "elo_ratings": {
                "home": p_elo.get('home_rating', features.get('home_elo_rating', 1500)),
                "away": p_elo.get('away_rating', features.get('away_elo_rating', 1500)),
                "diff": p_elo.get('rating_diff', 0)
            },
            "model_breakdown": {
                "gbdt": p_gbdt,
                "catboost": p_cat,
                "transformer": p_trans,
                "lstm": p_lstm,
                "gnn": p_gnn,
                "bayesian": p_bayes,
                "elo": p_elo,
                "monte_carlo": mc_res
            }
        }
