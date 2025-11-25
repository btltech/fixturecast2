import numpy as np

class BayesianModel:
    """
    Bayesian Inference Model for match prediction.
    Uses betting odds as priors and updates with team statistics.
    """
    
    def __init__(self):
        pass
    
    def train(self, data):
        print("Training Bayesian Model...")
        pass
    
    def predict(self, features):
        """
        Bayesian prediction using odds as priors.
        Updates probabilities based on team performance data.
        """
        # Get betting odds if available
        odds_home = features.get('odds_home_win', 0)
        odds_draw = features.get('odds_draw', 0)
        odds_away = features.get('odds_away_win', 0)
        odds_available = features.get('odds_available', False)
        
        if odds_available and odds_home > 0 and odds_draw > 0 and odds_away > 0:
            # Convert odds to probabilities (remove bookmaker margin)
            # Implied probability = 1 / decimal_odds
            prob_home = 1 / odds_home
            prob_draw = 1 / odds_draw
            prob_away = 1 / odds_away
            
            # Normalize (remove overround/vig)
            total = prob_home + prob_draw + prob_away
            prior_home = prob_home / total
            prior_draw = prob_draw / total
            prior_away = prob_away / total
        else:
            # No odds available, use league averages as priors
            prior_home = 0.46  # Home win rate
            prior_draw = 0.27  # Draw rate
            prior_away = 0.27  # Away win rate
        
        # Calculate likelihood from team statistics
        # Use recent form as evidence
        home_wins = features.get('home_wins_last10', 5)
        home_draws = features.get('home_draws_last10', 3)
        home_losses = features.get('home_losses_last10', 2)
        
        away_wins = features.get('away_wins_last10', 5)
        away_draws = features.get('away_draws_last10', 3)
        away_losses = features.get('away_losses_last10', 2)
        
        # Likelihood: what's the probability of this form given home/draw/away outcome?
        # Calculate rates first
        home_win_rate = home_wins / max(home_wins + home_draws + home_losses, 1)
        home_draw_rate = home_draws / max(home_wins + home_draws + home_losses, 1)
        home_loss_rate = home_losses / max(home_wins + home_draws + home_losses, 1)
        
        away_win_rate = away_wins / max(away_wins + away_draws + away_losses, 1)
        away_draw_rate = away_draws / max(away_wins + away_draws + away_losses, 1)
        away_loss_rate = away_losses / max(away_wins + away_draws + away_losses, 1)
        
        # Likelihood: what's the probability of this form given home/draw/away outcome?
        # P(form | home_win) ∝ home winning rate * away losing rate
        likelihood_home = home_win_rate * away_loss_rate
        
        # P(form | draw) ∝ both teams' draw rates
        likelihood_draw = (home_draw_rate + away_draw_rate) / 2
        
        # P(form | away_win) ∝ away winning rate * home losing rate
        likelihood_away = away_win_rate * home_loss_rate
        
        # Bayes' theorem: P(outcome | form) ∝ P(form | outcome) * P(outcome)
        posterior_home = likelihood_home * prior_home
        posterior_draw = likelihood_draw * prior_draw
        posterior_away = likelihood_away * prior_away
        
        posterior_total = posterior_home + posterior_draw + posterior_away
        if posterior_total == 0:
            posterior_total = 1e-9  # Prevent division by zero
            
        # Add prior weight (don't deviate too much from odds)
        weight_prior = 0.6  # 60% weight on odds, 40% on form evidence
        weight_likelihood = 0.4
        
        bayesian_home = weight_prior * prior_home + weight_likelihood * (posterior_home / posterior_total)
        bayesian_draw = weight_prior * prior_draw + weight_likelihood * (posterior_draw / posterior_total)
        bayesian_away = weight_prior * prior_away + weight_likelihood * (posterior_away / posterior_total)
        
        # Normalize
        total = bayesian_home + bayesian_draw + bayesian_away
        
        return {
            "home_win": round(bayesian_home / total, 4),
            "draw": round(bayesian_draw / total, 4),
            "away_win": round(bayesian_away / total, 4)
        }
    
    def save(self, path):
        import joblib
        joblib.dump(self, path)
    
    def load(self, path):
        import joblib
        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
