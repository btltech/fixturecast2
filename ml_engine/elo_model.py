import numpy as np


class EloGlickoModel:
    """
    Elo Rating System - trained with actual Elo ratings from historical data.
    Also includes ML classifier trained on Elo-derived features.
    """

    def __init__(self):
        self.base_rating = 1500  # Average team rating
        self.k_factor = 32  # How much ratings change per match
        self.home_advantage = 100  # Elo points for home team
        self.team_ratings = {}  # Actual Elo ratings from training
        self.model = None  # ML classifier
        self.feature_keys = None
        self.trained = False

    def train(self, X, y):
        """Train Elo ratings from historical matches and build ML classifier"""
        print("Training Elo/Glicko model (SVM + Elo rating updates)...")
        from sklearn.svm import SVC

        # Handle both numpy arrays and list of dicts
        if isinstance(X, np.ndarray):
            # For numpy array input, just train the classifier
            X_matrix = X
            self.n_features = X.shape[1]
            self.feature_keys = None

            y_array = np.array(y)
            self.model = SVC(
                kernel="rbf", probability=True, random_state=45, class_weight="balanced"
            )
            self.model.fit(X_matrix, y_array)
            self.trained = True
            print(f"Elo model trained on {len(y_array)} samples with {self.n_features} features.")
            return

        # Step 1: Update Elo ratings from match outcomes
        print("  Updating Elo ratings from historical matches...")
        for i, features in enumerate(X):
            home_id = features.get("home_id", 0)
            away_id = features.get("away_id", 0)
            outcome = y[i]  # 0=home, 1=draw, 2=away

            if home_id and away_id:
                # Initialize if needed
                if home_id not in self.team_ratings:
                    self.team_ratings[home_id] = self.base_rating
                if away_id not in self.team_ratings:
                    self.team_ratings[away_id] = self.base_rating

                # Get current ratings
                home_elo = self.team_ratings[home_id]
                away_elo = self.team_ratings[away_id]

                # Calculate expected scores
                home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - self.home_advantage) / 400))
                away_expected = 1 - home_expected

                # Actual scores
                if outcome == 0:  # Home win
                    home_actual, away_actual = 1.0, 0.0
                elif outcome == 2:  # Away win
                    home_actual, away_actual = 0.0, 1.0
                else:  # Draw
                    home_actual, away_actual = 0.5, 0.5

                # Update ratings
                self.team_ratings[home_id] += self.k_factor * (home_actual - home_expected)
                self.team_ratings[away_id] += self.k_factor * (away_actual - away_expected)

        print(f"  Updated ratings for {len(self.team_ratings)} teams")

        # Step 2: Train ML classifier on Elo-derived features
        self.feature_keys = [
            "home_league_pos",
            "away_league_pos",
            "home_points_last10",
            "away_points_last10",
            "home_goals_for_last5",
            "home_goals_against_last5",
            "away_goals_for_last5",
            "away_goals_against_last5",
            "home_gd_per_game",
            "away_gd_per_game",
            "position_diff",
            "points_diff",
            "home_win_rate",
            "away_win_rate",
            "home_home_win_rate",
            "away_away_win_rate",
            "home_ppg",
            "away_ppg",
        ]

        X_matrix = np.array([[sample.get(k, 0) for k in self.feature_keys] for sample in X])
        y_array = np.array(y)

        self.model = SVC(kernel="rbf", probability=True, random_state=45, class_weight="balanced")
        self.model.fit(X_matrix, y_array)
        self.trained = True
        self.n_features = len(self.feature_keys)
        print(f"Elo model trained on {len(X)} samples with {len(self.feature_keys)} features.")

    def predict_proba(self, X):
        """Return probabilities for batch prediction during training"""
        if self.trained and self.model is not None:
            if isinstance(X, np.ndarray):
                return self.model.predict_proba(X)
        raise ValueError("predict_proba requires trained model with numpy array input")

    def predict(self, features_or_home_id=None, away_id=None, features=None):
        """
        Calculate win probabilities using Elo ratings.
        Uses trained ML model if available, otherwise heuristic.
        """
        # Handle different call patterns
        if isinstance(features_or_home_id, dict):
            features = features_or_home_id
            home_id = features.get("home_id")
            away_id_local = features.get("away_id")
        else:
            home_id = features_or_home_id
            away_id_local = away_id

        # Use trained ML model if available
        if self.trained and self.model is not None and self.feature_keys is not None:
            try:
                X = np.array([[features.get(k, 0) for k in self.feature_keys]])
                probs = self.model.predict_proba(X)[0]

                # Get actual Elo ratings if we have them
                home_rating = self.team_ratings.get(
                    home_id, self._estimate_rating_from_form(features, "home")
                )
                away_rating = self.team_ratings.get(
                    away_id_local, self._estimate_rating_from_form(features, "away")
                )

                return {
                    "home_win": round(float(probs[0]), 4),
                    "draw": round(float(probs[1]), 4),
                    "away_win": round(float(probs[2]), 4),
                    "home_rating": round(home_rating, 1),
                    "away_rating": round(away_rating, 1),
                    "rating_diff": round(home_rating - away_rating, 1),
                }
            except Exception as e:
                print(f"Elo model prediction error, using fallback: {e}")

        # Fallback: heuristic Elo calculation
        # Use stored ratings if available, else estimate
        if home_id and home_id in self.team_ratings:
            home_rating = self.team_ratings[home_id]
        else:
            home_rating = self._estimate_rating_from_form(features, "home")

        if away_id_local and away_id_local in self.team_ratings:
            away_rating = self.team_ratings[away_id_local]
        else:
            away_rating = self._estimate_rating_from_form(features, "away")

        # Add home advantage
        home_rating_adjusted = home_rating + self.home_advantage

        # Calculate expected scores using Elo formula
        # E = 1 / (1 + 10^((opponent_rating - your_rating) / 400))
        expected_home = 1 / (1 + 10 ** ((away_rating - home_rating_adjusted) / 400))
        expected_away = 1 / (1 + 10 ** ((home_rating_adjusted - away_rating) / 400))

        # Convert expected scores to win/draw/loss probabilities
        # In Elo, expected score is P(win) + 0.5*P(draw)
        # We need to distribute to get individual probabilities

        # Use league average draw rate
        draw_rate = 0.27

        # Adjust draw rate based on rating difference
        rating_diff = abs(home_rating_adjusted - away_rating)
        if rating_diff > 200:  # Big mismatch = fewer draws
            draw_rate *= 0.8
        elif rating_diff < 50:  # Close match = more draws
            draw_rate *= 1.2

        draw_rate = min(draw_rate, 0.35)  # Cap at 35%

        # Calculate win probabilities
        # expected_home = P(home_win) + 0.5 * P(draw)
        # expected_home = P(home_win) = expected_home - 0.5 * draw_rate

        home_win = max(0, expected_home - 0.5 * draw_rate)
        away_win = max(0, expected_away - 0.5 * draw_rate)

        # Normalize to ensure they sum to 1
        total = home_win + draw_rate + away_win

        return {
            "home_win": round(home_win / total, 4),
            "draw": round(draw_rate / total, 4),
            "away_win": round(away_win / total, 4),
        }

    def _estimate_rating_from_form(self, features, team_prefix):
        """
        Estimate Elo rating from recent performance metrics.
        Uses league position, form, and goals.
        """
        if not features:
            return self.base_rating

        # Base rating from league position
        rank = features.get(f"{team_prefix}_league_pos", 10)
        # 1st place ≈ 1800, 10th place ≈ 1500, 20th place ≈ 1200
        position_rating = 1900 - (rank * 35)

        # Adjust for recent form
        points = features.get(f"{team_prefix}_points_last10", 15)
        # 30 points (perfect) = +100, 0 points = -100
        form_adjustment = (points - 15) * 6.67  # Scale to ±100

        # Adjust for goal difference
        gf = features.get(f"{team_prefix}_goals_for_last10", 10)
        ga = features.get(f"{team_prefix}_goals_against_last10", 10)
        goal_diff = gf - ga
        # ±10 goals = ±50 rating points
        goals_adjustment = goal_diff * 5

        # Combine adjustments
        estimated_rating = position_rating + form_adjustment + goals_adjustment

        # Keep within reasonable bounds
        estimated_rating = max(1000, min(2200, estimated_rating))

        return estimated_rating

    def save(self, path):
        import joblib

        joblib.dump(self, path)

    def load(self, path):
        import joblib

        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
