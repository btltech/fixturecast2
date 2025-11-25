
import numpy as np

class GNNModel:
    """
    League Context Model (replacing GNN placeholder)
    Analyzes team relative to league context and competitive environment.
    """
    
    def __init__(self):
        pass
    
    def train(self, data):
        print("Training League Context Model...")
        pass

    def predict(self, features):
        """
        Predict using league standings context.
        Considers competitive tier and relative strength.
        """
        # Get league positions
        home_rank = features.get('home_league_pos', 10)
        away_rank = features.get('away_league_pos', 10)
        
        home_points_season = features.get('home_league_points', 30)
        away_points_season = features.get('away_league_points', 30)
        
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
            "away_win": round(away_win_prob / total, 4)
        }

    def save(self, path):
        import joblib
        joblib.dump(self, path)

    def load(self, path):
        import joblib
        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
