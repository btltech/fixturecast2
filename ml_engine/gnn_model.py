import numpy as np


class GNNModel:
    """
    League Context Model - trained AdaBoost classifier
    Analyzes team relative to league context and competitive environment.
    """

    def __init__(self):
        self.model = None
        self.feature_keys = None
        self.trained = False

    def train(self, X, y):
        """Train on league context features"""
        print("Training GNN/League Context Model (AdaBoost)...")
        from sklearn.ensemble import AdaBoostClassifier
        from sklearn.tree import DecisionTreeClassifier

        # Handle both numpy arrays and list of dicts
        if isinstance(X, np.ndarray):
            X_matrix = X
            self.n_features = X.shape[1]
            self.feature_keys = None
        else:
            # Define feature keys specific to this model (league position features)
            self.feature_keys = [
                "home_league_pos",
                "away_league_pos",
                "home_league_points",
                "away_league_points",
                "home_total_matches",
                "away_total_matches",
                "position_diff",
                "points_diff",
                "home_home_matches",
                "away_away_matches",
                "home_home_win_rate",
                "away_away_win_rate",
                "home_ppg_home",
                "away_ppg_away",
                "home_gd",
                "away_gd",
                "h2h_home_wins",
                "h2h_away_wins",
                "h2h_draws",
                "h2h_total_matches",
            ]
            X_matrix = np.array([[sample.get(k, 0) for k in self.feature_keys] for sample in X])
            self.n_features = len(self.feature_keys)

        y_array = np.array(y)

        base_estimator = DecisionTreeClassifier(max_depth=4, random_state=44)
        self.model = AdaBoostClassifier(
            estimator=base_estimator, n_estimators=50, learning_rate=0.8, random_state=44
        )
        self.model.fit(X_matrix, y_array)
        self.trained = True
        print(f"GNN model trained on {len(y_array)} samples with {self.n_features} features.")

    def predict_proba(self, X):
        """Return probabilities for batch prediction during training"""
        if self.trained and self.model is not None:
            if isinstance(X, np.ndarray):
                return self.model.predict_proba(X)
        raise ValueError("predict_proba requires trained model with numpy array input")

    def predict(self, features):
        """
        Predict using league standings context.
        Uses trained model if available, otherwise heuristic fallback.
        """
        # Use trained model if available
        if self.trained and self.model is not None and self.feature_keys is not None:
            try:
                X = np.array([[features.get(k, 0) for k in self.feature_keys]])
                probs = self.model.predict_proba(X)[0]
                # Classes: 0=Home, 1=Draw, 2=Away
                return {
                    "home_win": round(float(probs[0]), 4),
                    "draw": round(float(probs[1]), 4),
                    "away_win": round(float(probs[2]), 4),
                }
            except Exception as e:
                print(f"GNN model prediction error, using fallback: {e}")

        # Fallback: heuristic calculation
        # Get league positions
        home_rank = features.get("home_league_pos", 10)
        away_rank = features.get("away_league_pos", 10)

        home_points_season = features.get("home_league_points", 30)
        away_points_season = features.get("away_league_points", 30)

        # Determine competitive tiers
        # Top 6 = title/europe contenders
        # 7-14 = mid-table
        # 15-20 = relegation battle

        def get_tier(rank):
            if rank <= 6:
                return "top"
            elif rank <= 14:
                return "mid"
            else:
                return "bottom"

        home_tier = get_tier(home_rank)
        away_tier = get_tier(away_rank)

        # Calculate strength difference using both rank and points
        rank_diff = away_rank - home_rank  # Positive if home is better
        points_diff = home_points_season - away_points_season

        # Normalize rank difference (-19 to +19 → -1 to +1)
        rank_strength = np.tanh(rank_diff / 10)

        # Normalize points difference
        points_strength = np.tanh(points_diff / 20)

        # Combined strength indicator (60% rank, 40% points)
        strength_advantage = 0.6 * rank_strength + 0.4 * points_strength

        # Tier-based adjustments
        tier_bonus = 0

        if home_tier == "top" and away_tier == "bottom":
            tier_bonus = 0.15  # Strong favorite
        elif home_tier == "bottom" and away_tier == "top":
            tier_bonus = -0.15  # Strong underdog
        elif home_tier == "top" and away_tier == "mid":
            tier_bonus = 0.08
        elif home_tier == "mid" and away_tier == "top":
            tier_bonus = -0.08

        total_advantage = strength_advantage + tier_bonus

        # Convert to probabilities
        # Use sigmoid with home advantage built in
        home_base = 0.48  # Slight home advantage

        # Strong advantage swing: ±0.5 advantage = ±22% probability
        prob_swing = np.tanh(total_advantage * 2.5) * 0.27

        home_win_prob = home_base + prob_swing

        # Distribute rest between draw and away
        remaining = 1 - home_win_prob

        # Top teams playing each other = more draws (tactical)
        # Bottom teams = fewer draws (desperation)
        draw_modifier = 1.0

        if home_tier == "top" and away_tier == "top":
            draw_modifier = 1.25  # More tactical
        elif home_tier == "bottom" and away_tier == "bottom":
            draw_modifier = 0.85  # More open/desperate

        draw_base = 0.27 * draw_modifier
        draw_prob = remaining * (draw_base / (1 - home_base + draw_base))
        away_win_prob = remaining - draw_prob

        # Bounds checking
        home_win_prob = max(0.15, min(0.80, home_win_prob))
        draw_prob = max(0.08, min(0.38, draw_prob))
        away_win_prob = max(0.12, away_win_prob)

        # Normalize
        total = home_win_prob + draw_prob + away_win_prob

        return {
            "home_win": round(home_win_prob / total, 4),
            "draw": round(draw_prob / total, 4),
            "away_win": round(away_win_prob / total, 4),
        }

    def save(self, path):
        import joblib

        joblib.dump(self, path)

    def load(self, path):
        import joblib

        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
