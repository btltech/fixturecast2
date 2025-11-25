
import numpy as np

class LSTMSequenceModel:
    """
    Performance Trend Model (replacing LSTM placeholder)
    Analyzes trajectory and momentum of team performance.
    """
    
    def __init__(self):
        pass
    
    def train(self, data):
        print("Training Performance Trend Model...")
        pass

    def predict(self, features):
        """
        Predict based on performance trends and trajectory.
        Detects teams on the rise or decline.
        """
        # Get form metrics
        home_points = features.get('home_points_last10', 15)
        away_points = features.get('away_points_last10', 15)
        
        # Get league position as proxy for season trajectory
        home_rank = features.get('home_league_pos', 10)
        away_rank = features.get('away_league_pos', 10)
        
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
        home_gf = features.get('home_goals_for_last10', 10)
        home_ga = features.get('home_goals_against_last10', 10)
        away_gf = features.get('away_goals_for_last10', 10)
        away_ga = features.get('away_goals_against_last10', 10)
        
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
            "away_win": round(away_win_prob / total, 4)
        }

    def save(self, path):
        import joblib
        joblib.dump(self, path)

    def load(self, path):
        import joblib
        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
