import numpy as np


class CalibrationModel:
    """
    Probability Calibration Model.
    Uses Temperature Scaling to sharpen or soften probability distributions.
    """

    def __init__(self, temperature=0.8):
        # Temperature < 1.0 sharpens predictions (more confident)
        # Temperature > 1.0 softens predictions (more conservative)
        self.temperature = temperature

    def calibrate(self, probs):
        """
        Calibrate probabilities using temperature scaling.
        Input: dict with 'home_win', 'draw', 'away_win'
        Output: calibrated dict
        """
        # Extract probabilities
        p = np.array(
            [probs.get("home_win", 0.33), probs.get("draw", 0.33), probs.get("away_win", 0.33)]
        )

        # Avoid log(0)
        p = np.clip(p, 1e-9, 1.0)

        # Apply temperature scaling (Softmax with temperature)
        # log_p / T
        log_p = np.log(p) / self.temperature

        # Softmax
        exp_p = np.exp(log_p)
        calibrated_p = exp_p / np.sum(exp_p)

        return {
            "home_win_prob": float(calibrated_p[0]),
            "draw_prob": float(calibrated_p[1]),
            "away_win_prob": float(calibrated_p[2]),
        }


class ProbabilityCalibrator:
    """
    Trainable probability calibrator using Platt scaling.
    Learns optimal temperature from training predictions vs outcomes.
    """

    def __init__(self):
        self.temperature = 1.0
        self.trained = False

    def train(self, probs, y):
        """
        Train calibrator on predicted probabilities and actual outcomes.
        probs: numpy array of shape (n_samples, 3) - predicted [home, draw, away]
        y: numpy array of actual outcomes (0=home, 1=draw, 2=away)
        """
        print("Training probability calibrator...")

        # Simple grid search for optimal temperature
        best_temp = 1.0
        best_score = float("inf")

        for temp in np.arange(0.5, 2.0, 0.1):
            # Apply temperature scaling
            scaled = self._apply_temperature(probs, temp)

            # Calculate negative log-likelihood
            nll = 0
            for i, outcome in enumerate(y):
                prob = max(scaled[i, outcome], 1e-9)
                nll -= np.log(prob)

            if nll < best_score:
                best_score = nll
                best_temp = temp

        self.temperature = best_temp
        self.trained = True
        print(f"  Calibrator trained. Optimal temperature: {self.temperature:.2f}")

    def _apply_temperature(self, probs, temp):
        """Apply temperature scaling to probability matrix"""
        probs = np.clip(probs, 1e-9, 1.0)
        log_probs = np.log(probs) / temp
        exp_probs = np.exp(log_probs)
        return exp_probs / exp_probs.sum(axis=1, keepdims=True)

    def calibrate(self, probs):
        """Calibrate a single prediction"""
        if isinstance(probs, dict):
            p = np.array(
                [
                    [
                        probs.get("home_win", 0.33),
                        probs.get("draw", 0.33),
                        probs.get("away_win", 0.33),
                    ]
                ]
            )
        else:
            p = np.array([probs]) if len(probs.shape) == 1 else probs

        calibrated = self._apply_temperature(p, self.temperature)

        return {
            "home_win_prob": float(calibrated[0, 0]),
            "draw_prob": float(calibrated[0, 1]),
            "away_win_prob": float(calibrated[0, 2]),
        }

    def save(self, path):
        import joblib

        joblib.dump(self, path)

    def load(self, path):
        import joblib

        loaded = joblib.load(path)
        self.__dict__.update(loaded.__dict__)
