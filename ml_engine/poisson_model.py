
import numpy as np

class PoissonModel:
    """
    Poisson regression model for predicting goal distributions.
    Uses attack/defense strengths to calculate lambda (expected goals).
    """
    
    def __init__(self):
        self.home_advantage = 1.25  # Home teams score ~25% more
        self.league_avg_goals = 2.8  # Average goals per match in top leagues
    
    def train(self, X, y):
        print("Training Poisson Model (simple linear regression for lambda)...")
        from sklearn.linear_model import LinearRegression
        import numpy as np
        # Expect X as list of feature dicts, y as list of dicts with 'home_lambda','away_lambda'
        if not X:
            print("No training data provided.")
            return
        # Use simple features: home_goals_for_avg, away_goals_for_avg, home_form_last5, away_form_last5
        feature_keys = ['home_goals_for_avg', 'away_goals_for_avg', 'home_form_last5', 'away_form_last5']
        X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
        home_lambda = np.array([target['home_lambda'] for target in y])
        away_lambda = np.array([target['away_lambda'] for target in y])
        self.home_model = LinearRegression()
        self.away_model = LinearRegression()
        self.home_model.fit(X_matrix, home_lambda)
        self.away_model.fit(X_matrix, away_lambda)
        print("Poisson model training complete.")

    def predict(self, features):
        """
        Calculate expected goals using team statistics.
        Returns lambda values for Poisson distribution.
        
        Key improvements:
        1. Uses actual goals scored/conceded from features
        2. Applies Elo-based strength modifier for better differentiation
        3. Uses expected goals (xG) if available
        """
        # Get goal averages - use actual data or realistic defaults
        home_goals_for = features.get('home_goals_for_avg', 1.4)
        home_goals_against = features.get('home_goals_against_avg', 1.1)
        away_goals_for = features.get('away_goals_for_avg', 1.3)
        away_goals_against = features.get('away_goals_against_avg', 1.2)
        
        # Get xG if available (more predictive than actual goals)
        home_xg = features.get('home_xg_avg', None)
        away_xg = features.get('away_xg_avg', None)
        
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
        home_elo = features.get('home_elo_rating', features.get('home_elo', 1500))
        away_elo = features.get('away_elo_rating', features.get('away_elo', 1500))
        
        # Elo modifier: +/- 10% per 100 Elo difference from 1500
        home_elo_mod = 1.0 + (home_elo - 1500) / 1000
        away_elo_mod = 1.0 + (away_elo - 1500) / 1000
        
        # Apply Elo modifier to attack strength
        home_lambda *= home_elo_mod
        away_lambda *= away_elo_mod
        
        # Inverse Elo modifier affects defense (higher Elo = concede less)
        home_lambda *= (2 - away_elo_mod)  # Away team's quality reduces home scoring
        away_lambda *= (2 - home_elo_mod)  # Home team's quality reduces away scoring
        
        # Apply recent form modifier
        home_form = features.get('home_points_last10', features.get('home_form_points', 15))
        away_form = features.get('away_points_last10', features.get('away_form_points', 15))
        
        # Form modifier: 0-30 points maps to 0.7-1.3 multiplier
        home_form_mult = 0.7 + (min(30, max(0, home_form)) / 30) * 0.6
        away_form_mult = 0.7 + (min(30, max(0, away_form)) / 30) * 0.6
        
        home_lambda *= home_form_mult
        away_lambda *= away_form_mult
        
        # Consider H2H history if available
        h2h_home_goals = features.get('h2h_home_goals_avg', None)
        h2h_away_goals = features.get('h2h_away_goals_avg', None)
        
        if h2h_home_goals is not None and h2h_away_goals is not None:
            # Blend in H2H data (20% weight)
            home_lambda = 0.8 * home_lambda + 0.2 * h2h_home_goals
            away_lambda = 0.8 * away_lambda + 0.2 * h2h_away_goals
        
        # Ensure reasonable bounds (0.5 to 4.0 goals expected)
        home_lambda = max(0.5, min(4.0, home_lambda))
        away_lambda = max(0.5, min(4.0, away_lambda))
        
        return {
            "home_lambda": round(home_lambda, 2),
            "away_lambda": round(away_lambda, 2)
        }

    def save(self, path):
        import joblib
        joblib.dump(self, path)

    def load(self, path):
        import joblib
        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
