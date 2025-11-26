import numpy as np


class PoissonModel:
    """
    Poisson regression model for predicting goal distributions.
    Uses attack/defense strengths to calculate lambda (expected goals).
    """

    def __init__(self):
        self.home_advantage = 1.25  # Home teams score ~25% more
        self.league_avg_goals = 2.8  # Average goals per match in top leagues
        self.home_model = None
        self.away_model = None
        self.trained = False
        self.feature_keys = None

    def train(self, X, y):
        print("Training Poisson Model (simple linear regression for lambda)...")
        from sklearn.linear_model import LinearRegression

        if not X:
            print("No training data provided.")
            return

        # Feature keys for predicting goals
        self.feature_keys = [
            "home_goals_for_avg",
            "away_goals_for_avg",
            "home_form_last5",
            "away_form_last5",
        ]

        # For list of dicts
        if isinstance(X, list) and len(X) > 0 and isinstance(X[0], dict):
            X_matrix = np.array([[sample.get(k, 0) for k in self.feature_keys] for sample in X])

            # Check if y contains lambda values or outcomes
            if isinstance(y, list) and len(y) > 0:
                if isinstance(y[0], dict):
                    # y is list of {home_lambda, away_lambda}
                    home_lambda = np.array([target.get("home_lambda", 1.3) for target in y])
                    away_lambda = np.array([target.get("away_lambda", 1.1) for target in y])
                else:
                    # y is list of outcomes - estimate lambdas from features
                    home_lambda = np.array([sample.get("home_goals_for_avg", 1.3) for sample in X])
                    away_lambda = np.array([sample.get("away_goals_for_avg", 1.1) for sample in X])
        else:
            # Numpy array input - use simple defaults
            print("  Using default lambdas for numpy array input")
            X_matrix = X if isinstance(X, np.ndarray) else np.array(X)
            n_samples = X_matrix.shape[0]
            home_lambda = np.ones(n_samples) * 1.3
            away_lambda = np.ones(n_samples) * 1.1

        self.home_model = LinearRegression()
        self.away_model = LinearRegression()
        self.home_model.fit(X_matrix[:, :4] if X_matrix.shape[1] >= 4 else X_matrix, home_lambda)
        self.away_model.fit(X_matrix[:, :4] if X_matrix.shape[1] >= 4 else X_matrix, away_lambda)
        self.trained = True
        print("Poisson model training complete.")

    def predict_match_proba(self, features):
        """Return [P(home), P(draw), P(away)] for a single match"""
        preds = self.predict(features)
        home_lambda = preds.get("home_lambda", 1.3)
        away_lambda = preds.get("away_lambda", 1.1)

        # Calculate Poisson probabilities for different scorelines
        probs = self._calculate_outcome_probs(home_lambda, away_lambda)
        return np.array([probs["home_win"], probs["draw"], probs["away_win"]])

    def predict(self, features):
        """
        Calculate expected goals using team statistics.
        Returns lambda values for Poisson distribution.

        If trained, uses LinearRegression models.
        Otherwise, falls back to heuristic calculation.
        """
        # Try using trained models first
        if self.trained and self.home_model is not None and self.away_model is not None:
            try:
                feature_keys = [
                    "home_goals_for_avg",
                    "away_goals_for_avg",
                    "home_form_last5",
                    "away_form_last5",
                ]
                X = np.array([[features.get(k, 0) for k in feature_keys]])
                home_lambda = float(self.home_model.predict(X)[0])
                away_lambda = float(self.away_model.predict(X)[0])
                # Ensure reasonable bounds
                home_lambda = max(0.5, min(4.0, home_lambda))
                away_lambda = max(0.5, min(4.0, away_lambda))
                return {"home_lambda": round(home_lambda, 2), "away_lambda": round(away_lambda, 2)}
            except Exception as e:
                print(f"Poisson trained model error, falling back to heuristic: {e}")

        # Fallback: heuristic calculation
        # Get goal averages - use actual data or realistic defaults
        home_goals_for = features.get("home_goals_for_avg", 1.4)
        home_goals_against = features.get("home_goals_against_avg", 1.1)
        away_goals_for = features.get("away_goals_for_avg", 1.3)
        away_goals_against = features.get("away_goals_against_avg", 1.2)

        # Get xG if available (more predictive than actual goals)
        home_xg = features.get("home_xg_avg", None)
        away_xg = features.get("away_xg_avg", None)

        # If we have xG, blend it with actual goals (xG is more predictive)
        if home_xg is not None and away_xg is not None:
            home_goals_for = 0.6 * home_xg + 0.4 * home_goals_for
            away_goals_for = 0.6 * away_xg + 0.4 * away_goals_for

        # League average per team per game
        league_avg = self.league_avg_goals / 2  # 1.4 goals per team

        # Calculate attack and defense strengths relative to league average
        # Strong attack = goals_for / league_avg > 1.0
        # Weak defense = goals_against / league_avg > 1.0
        home_attack = max(0.5, home_goals_for / league_avg) if league_avg > 0 else 1.0
        home_defense = max(0.5, home_goals_against / league_avg) if league_avg > 0 else 1.0
        away_attack = max(0.5, away_goals_for / league_avg) if league_avg > 0 else 1.0
        away_defense = max(0.5, away_goals_against / league_avg) if league_avg > 0 else 1.0

        # Calculate base expected goals
        # Home lambda = (home team's attack) * (away team's defensive weakness) * league_avg * home_advantage
        home_lambda = home_attack * away_defense * league_avg * self.home_advantage

        # Away lambda = (away team's attack) * (home team's defensive weakness) * league_avg
        away_lambda = away_attack * home_defense * league_avg

        # Apply Elo-based modifier for team quality differentiation
        # Higher Elo = better team = score more / concede less
        home_elo = features.get("home_elo_rating", features.get("home_elo", 1500))
        away_elo = features.get("away_elo_rating", features.get("away_elo", 1500))

        # Elo modifier: +/- 10% per 100 Elo difference from 1500
        home_elo_mod = 1.0 + (home_elo - 1500) / 1000
        away_elo_mod = 1.0 + (away_elo - 1500) / 1000

        # Apply Elo modifier to attack strength
        home_lambda *= home_elo_mod
        away_lambda *= away_elo_mod

        # Inverse Elo modifier affects defense (higher Elo = concede less)
        home_lambda *= 2 - away_elo_mod  # Away team's quality reduces home scoring
        away_lambda *= 2 - home_elo_mod  # Home team's quality reduces away scoring

        # Apply recent form modifier
        home_form = features.get("home_points_last10", features.get("home_form_points", 15))
        away_form = features.get("away_points_last10", features.get("away_form_points", 15))

        # Form modifier: 0-30 points maps to 0.7-1.3 multiplier
        home_form_mult = 0.7 + (min(30, max(0, home_form)) / 30) * 0.6
        away_form_mult = 0.7 + (min(30, max(0, away_form)) / 30) * 0.6

        home_lambda *= home_form_mult
        away_lambda *= away_form_mult

        # Consider H2H history if available
        h2h_home_goals = features.get("h2h_home_goals_avg", None)
        h2h_away_goals = features.get("h2h_away_goals_avg", None)

        if h2h_home_goals is not None and h2h_away_goals is not None:
            # Blend in H2H data (20% weight)
            home_lambda = 0.8 * home_lambda + 0.2 * h2h_home_goals
            away_lambda = 0.8 * away_lambda + 0.2 * h2h_away_goals

        # Ensure reasonable bounds (0.5 to 4.0 goals expected)
        home_lambda = max(0.5, min(4.0, home_lambda))
        away_lambda = max(0.5, min(4.0, away_lambda))

        return {"home_lambda": round(home_lambda, 2), "away_lambda": round(away_lambda, 2)}

    def _calculate_outcome_probs(self, home_lambda, away_lambda, max_goals=7):
        """Calculate outcome probabilities from Poisson lambdas"""
        from math import exp, factorial

        def poisson_prob(k, lam):
            return (lam**k) * exp(-lam) / factorial(k)

        home_win = draw = away_win = 0.0

        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = poisson_prob(h, home_lambda) * poisson_prob(a, away_lambda)
                if h > a:
                    home_win += prob
                elif h == a:
                    draw += prob
                else:
                    away_win += prob

        # Normalize
        total = home_win + draw + away_win
        if total > 0:
            home_win /= total
            draw /= total
            away_win /= total

        return {"home_win": home_win, "draw": draw, "away_win": away_win}

    def save(self, path):
        import joblib

        joblib.dump(self, path)

    def load(self, path):
        import joblib

        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
