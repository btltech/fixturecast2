
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
        p = np.array([
            probs.get('home_win', 0.33),
            probs.get('draw', 0.33),
            probs.get('away_win', 0.33)
        ])
        
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
            "away_win_prob": float(calibrated_p[2])
        }
