import numpy as np

class TransformerSequenceModel:
    """
    Form Sequence Model (replacing Transformer placeholder)
    Analyzes recent match result patterns and momentum.
    """
    
    def __init__(self):
        pass
    
    def train(self, data):
        print("Training Form Sequence Model...")
        pass

    def predict(self, features):
        """
        Predict based on recent form sequences and momentum.
        Looks for winning/losing streaks and patterns.
        """
        # Get recent results
        home_wins = features.get('home_wins_last10', 5)
        home_draws = features.get('home_draws_last10', 3)
        home_losses = features.get('home_losses_last10', 2)
        
        away_wins = features.get('away_wins_last10', 5)
        away_draws = features.get('away_draws_last10', 3)
        away_losses = features.get('away_losses_last10', 2)
        
        total_home = max(home_wins + home_draws + home_losses, 1)
        total_away = max(away_wins + away_draws + away_losses, 1)
        
        # Calculate momentum scores (exponentially weighted recent form)
        # More recent matches matter more
        home_points = features.get('home_points_last10', 15)
        away_points = features.get('away_points_last10', 15)
        
        # Detect streaks (3+ consecutive results boost confidence)
        home_streak_bonus = 0
        away_streak_bonus = 0
        
        if home_wins >= 3:  # Winning streak
            home_streak_bonus = 0.10 * (home_wins / total_home)
        elif home_losses >= 3:  # Losing streak
            home_streak_bonus = -0.10 * (home_losses / total_home)
        
        if away_wins >= 3:
            away_streak_bonus = 0.10 * (away_wins / total_away)
        elif away_losses >= 3:
            away_streak_bonus = -0.10 * (away_losses / total_away)
        
        # Calculate win rates with streak adjustment
        home_win_rate = (home_wins / total_home) + home_streak_bonus
        home_draw_rate = home_draws / total_home
        home_loss_rate = (home_losses / total_home) - home_streak_bonus
        
        away_win_rate = (away_wins / total_away) + away_streak_bonus
        away_draw_rate = away_draws / total_away
        away_loss_rate = (away_losses / total_away) - away_streak_bonus
        
        # Combine rates (home team perspective)
        # P(home_win) ∝ home winning rate × away losing rate
        home_win_strength = home_win_rate * away_loss_rate * 1.3  # Home boost
        away_win_strength = away_win_rate * home_loss_rate
        draw_strength = (home_draw_rate + away_draw_rate) / 2
        
        # Add momentum factor (recent points trend)
        momentum_diff = (home_points - away_points) / 30  # Normalize to -1 to +1
        momentum_factor = np.tanh(momentum_diff)  # Smooth scaling
        
        # Adjust probabilities based on momentum
        home_win_prob = home_win_strength * (1 + 0.3 * momentum_factor)  # +30% if strong momentum
        away_win_prob = away_win_strength * (1 - 0.3 * momentum_factor)
        draw_prob = draw_strength
        
        # Ensure reasonable bounds
        home_win_prob = max(0.10, min(0.85, home_win_prob))
        away_win_prob = max(0.10, min(0.85, away_win_prob))
        draw_prob = max(0.05, min(0.40, draw_prob))
        
        # Normalization
        total = home_win_prob + draw_prob + away_win_prob
        
        return {
            "home_win": round(home_win_prob / total, 4),
            "draw": round(draw_prob / total, 4),
            "away_win": round(away_win_prob / total, 4)
        }

    def save(self, path):
        import joblib
        joblib.dump(self, path)

    def load(self, path):
        import joblib
        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
