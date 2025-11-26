import numpy as np


class LSTMSequenceModel:
    """
    Performance Trend Model - trained ExtraTrees classifier
    Analyzes trajectory and momentum of team performance.
    """

    def __init__(self):
        self.model = None
        self.feature_keys = None
        self.trained = False

    def train(self, X, y):
        """Train on trend/trajectory features"""
        print("Training LSTM/Trend Model (ExtraTrees)...")
        from sklearn.ensemble import ExtraTreesClassifier

        # Handle both numpy arrays and list of dicts
        if isinstance(X, np.ndarray):
            X_matrix = X
            self.n_features = X.shape[1]
            self.feature_keys = None
        else:
            # Define feature keys specific to this model (trend features)
            self.feature_keys = [
                "home_points_last10",
                "away_points_last10",
                "home_league_pos",
                "away_league_pos",
                "home_league_points",
                "away_league_points",
                "home_goals_for_last5",
                "home_goals_against_last5",
                "away_goals_for_last5",
                "away_goals_against_last5",
                "home_gd",
                "away_gd",
                "home_gd_per_game",
                "away_gd_per_game",
                "points_diff",
                "position_diff",
                "home_ppg",
                "away_ppg",
                "home_ppg_home",
                "away_ppg_away",
                "home_win_streak",
                "away_win_streak",
                "home_unbeaten_streak",
                "away_unbeaten_streak",
            ]
            X_matrix = np.array([[sample.get(k, 0) for k in self.feature_keys] for sample in X])
            self.n_features = len(self.feature_keys)

        y_array = np.array(y)

        self.model = ExtraTreesClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=8,
            random_state=43,
            class_weight="balanced",
        )
        self.model.fit(X_matrix, y_array)
        self.trained = True
        print(f"LSTM model trained on {len(y_array)} samples with {self.n_features} features.")

    def predict_proba(self, X):
        """Return probabilities for batch prediction during training"""
        if self.trained and self.model is not None:
            if isinstance(X, np.ndarray):
                return self.model.predict_proba(X)
        raise ValueError("predict_proba requires trained model with numpy array input")

    def predict(self, features):
        """
        Predict based on performance trends and trajectory.
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
                print(f"LSTM model prediction error, using fallback: {e}")

        # Fallback: heuristic calculation
        # Get form metrics
        home_points = features.get("home_points_last10", 15)
        away_points = features.get("away_points_last10", 15)

        # Get league position as proxy for season trajectory
        home_rank = features.get("home_league_pos", 10)
        away_rank = features.get("away_league_pos", 10)

        # Calculate performance relative to position
        # Top teams should have high points, bottom teams low
        # Overperformance = good recent form despite low rank
        home_expected_points = 30 - (home_rank * 1.5)  # 1st = 28.5, 20th = 0
        away_expected_points = 30 - (away_rank * 1.5)

        home_overperformance = (home_points - home_expected_points) / 30
        away_overperformance = (away_points - away_expected_points) / 30

        # Detect positive/negative trends
        # Positive trend = overperforming = team improving
        # Negative trend = underperforming = team declining
        trend_advantage = home_overperformance - away_overperformance

        # Get goal trends
        home_gf = features.get("home_goals_for_last10", 10)
        home_ga = features.get("home_goals_against_last10", 10)
        away_gf = features.get("away_goals_for_last10", 10)
        away_ga = features.get("away_goals_against_last10", 10)

        home_goal_trend = (home_gf - home_ga) / 10  # Goals per match difference
        away_goal_trend = (away_gf - away_ga) / 10

        goal_momentum = home_goal_trend - away_goal_trend

        # Combine trends (60% points, 40% goals)
        overall_momentum = 0.6 * trend_advantage + 0.4 * goal_momentum

        # Convert momentum to probabilities
        # Strong positive momentum = high home win probability
        # Strong negative momentum = high away win probability
        base_home = 0.46  # Home advantage baseline

        # Momentum swing: ±0.5 momentum = ±20% probability
        momentum_swing = np.tanh(overall_momentum * 2) * 0.25  #  ±25% max swing

        home_win_prob = base_home + momentum_swing

        # Distribute remaining probability
        remaining = 1 - home_win_prob

        # Draw probability decreases when momentum is strong (decisive matches)
        momentum_strength = abs(overall_momentum)
        draw_base = 0.27
        if momentum_strength > 0.3:  # Strong momentum either way
            draw_base *= 0.85  # Fewer draws

        draw_prob = remaining * (draw_base / (1 - base_home + draw_base))
        away_win_prob = remaining - draw_prob

        # Ensure valid probabilities
        home_win_prob = max(0.15, min(0.75, home_win_prob))
        draw_prob = max(0.10, min(0.35, draw_prob))
        away_win_prob = max(0.15, away_win_prob)

        # Final normalization
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
