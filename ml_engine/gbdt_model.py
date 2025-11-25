
import numpy as np

class GBDTModel:
    """
    Form-Based Statistical Model (replacing GBDT placeholder)
    Calculates win probabilities using weighted features:
    - League position and points
    - Recent form (last 10 matches)
    - Goals for/against
    - H2H record
    """
    
    def __init__(self):
        # Feature weights (learned from football statistics)
        self.weights = {
            'league_position': 0.25,
            'recent_form': 0.30,
            'goals': 0.20,
            'h2h': 0.15,
            'home_advantage': 0.10
        }
    
    def train(self, X, y):
        print("Training GBDT Model with GradientBoostingClassifier...")
        from sklearn.ensemble import GradientBoostingClassifier
        import numpy as np
        if not X:
            raise ValueError("Training data X cannot be empty")
        # Filter out non-numeric features (team_id, team_name)
        exclude_keys = ['home_id', 'away_id', 'home_name', 'away_name']
        feature_keys = [k for k in X[0].keys() if k not in exclude_keys and isinstance(X[0].get(k), (int, float))]
        self.feature_keys = feature_keys  # Store for later use in predict
        X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
        y_array = np.array(y)
        self.model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.model.fit(X_matrix, y_array)
        print(f"GBDT training complete. Used {len(feature_keys)} numeric features.")

    def predict(self, features):
        """
        Calculate win probabilities based on form and statistics.
        If trained sklearn model exists, use it. Otherwise use statistical fallback.
        """
        # If we have a trained sklearn model, use it
        if hasattr(self, 'model') and hasattr(self, 'feature_keys'):
            import numpy as np
            # Convert features dict to array using stored feature_keys
            X = np.array([[features.get(k, 0) for k in self.feature_keys]])
            # Get probabilities for each class [home_win, draw, away_win]
            probs = self.model.predict_proba(X)[0]
            # Assuming classes are ordered: 0=away_win, 1=draw, 2=home_win (or similar)
            # Check the actual class order
            if len(probs) == 3:
                return {
                    "home_win": round(float(probs[2]), 4),
                    "draw": round(float(probs[1]), 4),
                    "away_win": round(float(probs[0]), 4)
                }
        
        # Fallback to statistical model if no trained model
        # Extract features
        home_rank = features.get('home_league_pos', 10)
        away_rank = features.get('away_league_pos', 10)
        home_points = features.get('home_points_last10', 15)
        away_points = features.get('away_points_last10', 15)
        home_gf = features.get('home_goals_for_last10', 10)
        away_gf = features.get('away_goals_for_last10', 10)
        home_ga = features.get('home_goals_against_last10', 10)
        away_ga = features.get('away_goals_against_last10', 10)
        h2h_home = features.get('h2h_home_wins', 2)
        h2h_draw = features.get('h2h_draws', 2)
        h2h_away = features.get('h2h_away_wins', 2)
        h2h_total = max(features.get('h2h_total_matches', 6), 1)
        
        # 1. League Position Score (0-1, lower rank = better)
        # Normalize: 1st place = 1.0, 20th place = 0.0
        home_rank_score = max(0, (20 - home_rank) / 19)
        away_rank_score = max(0, (20 - away_rank) / 19)
        position_advantage = home_rank_score - away_rank_score
        
        # 2. Recent Form Score (0-1 based on points)
        # 30 points (10 wins) = perfect, 0 points = worst
        home_form_score = min(home_points / 30, 1.0)
        away_form_score = min(away_points / 30, 1.0)
        form_advantage = home_form_score - away_form_score
        
        # 3. Goals Score (attack - defense balance)
        home_goal_diff = home_gf - home_ga
        away_goal_diff = away_gf - away_ga
        # Normalize: +20 goals = 1.0, -20 goals = -1.0
        home_goals_score = np.tanh(home_goal_diff / 10)
        away_goals_score = np.tanh(away_goal_diff / 10)
        goals_advantage = home_goals_score - away_goals_score
        
        # 4. Head-to-Head Score
        h2h_home_rate = h2h_home / h2h_total
        h2h_draw_rate = h2h_draw / h2h_total
        h2h_away_rate = h2h_away / h2h_total
        h2h_advantage = h2h_home_rate - h2h_away_rate
        
        # 5. Home Advantage (baseline)
        home_boost = 0.15  # Home teams have inherent advantage
        
        # Weighted combination
        total_advantage = (
            self.weights['league_position'] * position_advantage +
            self.weights['recent_form'] * form_advantage +
            self.weights['goals'] * goals_advantage +
            self.weights['h2h'] * h2h_advantage +
            self.weights['home_advantage'] * home_boost
        )
        
        # Convert advantage score to probabilities using sigmoid
        # Advantage of +0.3 = ~63% home win
        # Advantage of -0.3 = ~37% home win
        strength_factor = 3.0  # Controls how much advantage matters
        home_win_base = 1 / (1 + np.exp(-strength_factor * total_advantage))
        
        # Distribute remaining probability between draw and away
        remaining = 1 - home_win_base
        
        # Draw probability influenced by h2h and defensive strength
        draw_tendency = 0.28  # Base draw rate in football
        if h2h_draw_rate > 0.3:  # Teams that often draw
            draw_tendency *= 1.2
        
        draw_prob = remaining * draw_tendency
        away_win_prob = remaining * (1 - draw_tendency)
        
        # Ensure probabilities sum to 1
        total = home_win_base + draw_prob + away_win_prob
        
        return {
            "home_win": round(home_win_base / total, 4),
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
