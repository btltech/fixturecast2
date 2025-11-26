import numpy as np


class CatBoostModel:
    """
    Goals-Based Prediction Model (replacing CatBoost placeholder)
    Focuses on expected goals and scoring patterns.
    """

    def __init__(self):
        self.league_avg_goals = 2.7  # Average goals per match

    def train(self, X, y):
        print("Training CatBoost Model (using LogisticRegression as proxy)...")
        from sklearn.linear_model import LogisticRegression

        # Handle both numpy arrays and list of dicts
        if isinstance(X, np.ndarray):
            X_matrix = X
            self.n_features = X.shape[1]
        else:
            if len(X) == 0:
                raise ValueError("Training data X cannot be empty")
            # Filter out non-numeric features
            exclude_keys = ["home_id", "away_id", "home_name", "away_name"]
            feature_keys = [
                k
                for k in X[0].keys()
                if k not in exclude_keys and isinstance(X[0].get(k), (int, float))
            ]
            self.feature_keys = feature_keys
            X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
            self.n_features = len(feature_keys)

        y_array = np.array(y)
        self.model = LogisticRegression(max_iter=1000, random_state=42, multi_class="multinomial")
        self.model.fit(X_matrix, y_array)
        print(f"CatBoost training complete. Used {self.n_features} features.")

    def predict_proba(self, X):
        """Return probabilities for batch prediction during training"""
        if hasattr(self, "model"):
            if isinstance(X, np.ndarray):
                return self.model.predict_proba(X)
        raise ValueError("predict_proba requires trained model with numpy array input")

    def predict(self, features):
        """
        Predict based on goals scoring and conceding patterns.
        Uses both season averages and recent form.
        """
        # Season-long goal averages
        home_gf_avg = features.get("home_goals_for_avg", 1.3)
        home_ga_avg = features.get("home_goals_against_avg", 1.2)
        away_gf_avg = features.get("away_goals_for_avg", 1.1)
        away_ga_avg = features.get("away_goals_against_avg", 1.3)

        # Recent form goals (last 10 matches)
        home_gf_recent = features.get("home_goals_for_last10", 10) / 10
        home_ga_recent = features.get("home_goals_against_last10", 10) / 10
        away_gf_recent = features.get("away_goals_for_last10", 10) / 10
        away_ga_recent = features.get("away_goals_against_last10", 10) / 10

        # Weight recent form more heavily (70% recent, 30% season)
        home_attack = 0.7 * home_gf_recent + 0.3 * home_gf_avg
        home_defense = 0.7 * home_ga_recent + 0.3 * home_ga_avg
        away_attack = 0.7 * away_gf_recent + 0.3 * away_gf_avg
        away_defense = 0.7 * away_ga_recent + 0.3 * away_ga_avg

        # Calculate expected goals using attack vs defense
        # Home xG = home attack strength × away defensive weakness
        league_avg = self.league_avg_goals / 2

        home_xg = (
            (home_attack / league_avg) * (away_defense / league_avg) * league_avg * 1.2
        )  # Home boost
        away_xg = (away_attack / league_avg) * (home_defense / league_avg) * league_avg

        # Convert xG difference to win probabilities
        xg_diff = home_xg - away_xg

        # Use a logistic function to convert goal difference to win probability
        # +1 goal advantage ≈ 60-65% win probability
        # +2 goals ≈ 75-80% win probability
        home_win_prob = 1 / (1 + np.exp(-1.5 * xg_diff))

        # Adjust for defensive solidity (clean sheets increase draw probability)
        home_cs_rate = features.get("home_clean_sheets", 5) / max(
            features.get("home_total_matches", 20), 1
        )
        away_cs_rate = features.get("away_clean_sheets", 5) / max(
            features.get("away_total_matches", 20), 1
        )

        # More clean sheets = more draws (tight games)
        avg_cs_rate = (home_cs_rate + away_cs_rate) / 2
        draw_base = 0.25 + (avg_cs_rate * 0.15)  # 25-40% draw rate based on defense

        # Low scoring games have more draws
        total_xg = home_xg + away_xg
        if total_xg < 2.0:  # Low scoring expected
            draw_base *= 1.3
        elif total_xg > 3.5:  # High scoring expected
            draw_base *= 0.8

        draw_base = min(draw_base, 0.40)  # Cap at 40%

        # Distribute probabilities
        remaining = 1 - home_win_prob
        draw_prob = remaining * (draw_base / (draw_base + (1 - home_win_prob - draw_base)))
        away_win_prob = remaining - draw_prob

        # Ensure non-negative
        draw_prob = max(0.05, min(draw_prob, 0.40))
        away_win_prob = max(0.05, away_win_prob)

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
