import numpy as np


class MonteCarloSimulator:
    def simulate(self, home_lambda, away_lambda, n_sims=10000):
        """
        Run Monte Carlo simulations using Poisson distribution.
        Calculate win probabilities, score distribution, BTTS, and over/under.

        Uses 10,000 simulations for better statistical accuracy.
        """
        home_wins = 0
        draws = 0
        away_wins = 0
        btts_count = 0  # Both teams to score
        over25_count = 0  # Over 2.5 goals
        over15_count = 0  # Over 1.5 goals
        scores = {}

        # Add small random variance to lambdas for each simulation batch
        # This models uncertainty in the expected goals estimates
        lambda_variance = 0.15  # +/- 15% variance

        for i in range(n_sims):
            # Add slight noise to lambda for each simulation
            # This creates more varied scorelines
            noise_home = 1 + (np.random.random() - 0.5) * lambda_variance * 2
            noise_away = 1 + (np.random.random() - 0.5) * lambda_variance * 2

            sim_home_lambda = home_lambda * noise_home
            sim_away_lambda = away_lambda * noise_away

            # Ensure lambdas stay positive
            sim_home_lambda = max(0.3, sim_home_lambda)
            sim_away_lambda = max(0.3, sim_away_lambda)

            # Sample from Poisson distribution
            h_goals = np.random.poisson(sim_home_lambda)
            a_goals = np.random.poisson(sim_away_lambda)

            # Cap at reasonable max (8 goals is very rare)
            h_goals = min(h_goals, 8)
            a_goals = min(a_goals, 8)

            # Count outcomes
            if h_goals > a_goals:
                home_wins += 1
            elif h_goals == a_goals:
                draws += 1
            else:
                away_wins += 1

            # BTTS - both teams score at least 1
            if h_goals >= 1 and a_goals >= 1:
                btts_count += 1

            # Goal totals
            total_goals = h_goals + a_goals
            if total_goals > 2.5:
                over25_count += 1
            if total_goals > 1.5:
                over15_count += 1

            # Track score distribution
            score_key = f"{h_goals}-{a_goals}"
            scores[score_key] = scores.get(score_key, 0) + 1

        return {
            "home_win": round(home_wins / n_sims, 3),
            "draw": round(draws / n_sims, 3),
            "away_win": round(away_wins / n_sims, 3),
            "score_dist": scores,
            "btts_prob": round(btts_count / n_sims, 3),
            "over25_prob": round(over25_count / n_sims, 3),
            "over15_prob": round(over15_count / n_sims, 3),
            "home_lambda": round(home_lambda, 2),
            "away_lambda": round(away_lambda, 2),
        }

    def build_from_matches(self, X):
        """Configure Monte Carlo from training matches"""
        if not X:
            self.avg_home_goals = 1.35
            self.avg_away_goals = 1.05
            return

        # Calculate average goals from training data
        home_goals = []
        away_goals = []
        for match in X:
            hg = match.get("home_goals_for_avg", match.get("home_gf_home_avg", 1.35))
            ag = match.get("away_goals_for_avg", match.get("away_gf_away_avg", 1.05))
            if hg and ag:
                home_goals.append(hg)
                away_goals.append(ag)

        if home_goals:
            self.avg_home_goals = np.mean(home_goals)
            self.avg_away_goals = np.mean(away_goals)
        else:
            self.avg_home_goals = 1.35
            self.avg_away_goals = 1.05

        print(
            f"  Monte Carlo configured: avg home λ={self.avg_home_goals:.2f}, avg away λ={self.avg_away_goals:.2f}"
        )

    def save(self, path):
        import joblib

        joblib.dump(self, path)

    def load(self, path):
        import joblib

        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
