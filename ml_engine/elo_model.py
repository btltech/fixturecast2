import numpy as np

class EloGlickoModel:
    """
    Elo Rating System for football prediction.
    Estimates team strength and calculates match probabilities.
    """
    
    def __init__(self):
        self.base_rating = 1500  # Average team rating
        self.k_factor = 32  # How much ratings change per match
        self.home_advantage = 100  # Elo points for home team
    
    def train(self, data):
        print("Training Elo/Glicko model...")
        # Would update ratings from historical matches
        pass
    
    def predict(self, home_id, away_id, features=None):
        """
        Calculate win probabilities using Elo ratings.
        If we don't have stored ratings, estimate from recent form.
        """
        # Estimate Elo ratings from recent performance
        home_rating = self._estimate_rating_from_form(features, 'home')
        away_rating = self._estimate_rating_from_form(features, 'away')
        
        # Add home advantage
        home_rating_adjusted = home_rating + self.home_advantage
        
        # Calculate expected scores using Elo formula
        # E = 1 / (1 + 10^((opponent_rating - your_rating) / 400))
        expected_home = 1 / (1 + 10**((away_rating - home_rating_adjusted) / 400))
        expected_away = 1 / (1 + 10**((home_rating_adjusted - away_rating) / 400))
        
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
            "away_win": round(away_win / total, 4)
        }
    
    def _estimate_rating_from_form(self, features, team_prefix):
        """
        Estimate Elo rating from recent performance metrics.
        Uses league position, form, and goals.
        """
        if not features:
            return self.base_rating
        
        # Base rating from league position
        rank = features.get(f'{team_prefix}_league_pos', 10)
        # 1st place ≈ 1800, 10th place ≈ 1500, 20th place ≈ 1200
        position_rating = 1900 - (rank * 35)
        
        # Adjust for recent form
        points = features.get(f'{team_prefix}_points_last10', 15)
        # 30 points (perfect) = +100, 0 points = -100
        form_adjustment = (points - 15) * 6.67  # Scale to ±100
        
        # Adjust for goal difference
        gf = features.get(f'{team_prefix}_goals_for_last10', 10)
        ga = features.get(f'{team_prefix}_goals_against_last10', 10)
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
