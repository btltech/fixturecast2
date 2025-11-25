
import numpy as np
from scipy.optimize import minimize_scalar

def calculate_brier_score(predictions, outcomes):
    """
    Calculate Brier Score for probability predictions.
    
    Brier Score = mean((predicted_prob - actual)^2)
    Lower is better. Perfect prediction = 0.0, worst = 1.0
    
    Args:
        predictions: List of dicts with {' home_win_prob', 'draw_prob', 'away_win_prob'}
        outcomes: List of dicts with {'result': 'home_win'/'draw'/'away_win'}
    
    Returns:
        float: Brier score (0-1, lower = better)
    """
    if not predictions or not outcomes or len(predictions) != len(outcomes):
        raise ValueError("Predictions and outcomes must have same length")
    
    total_score = 0.0
    
    for pred, outcome in zip(predictions, outcomes):
        # Create actual outcome vector [home, draw, away]
        outcome_map = {
            'home_win': [1, 0, 0],
            'draw': [0, 1, 0],
            'away_win': [0, 0, 1]
        }
        
        actual = outcome_map.get(outcome['result'])
        if actual is None:
            continue
        
        # Create prediction vector
        predicted = [
            pred.get('home_win_prob', 0),
            pred.get('draw_prob', 0),
            pred.get('away_win_prob', 0)
        ]
        
        # Calculate squared error for each outcome
        score = sum((a - p)**2 for a, p in zip(actual, predicted))
        total_score += score
    
    return total_score / len(predictions)


def find_optimal_temperature(predictions, outcomes, initial_temp=1.15):
    """
    Find optimal calibration temperature using Brier score minimization.
    
    Temperature scaling: prob' = prob^(1/T) / sum(prob^(1/T))
    - T > 1: Softer predictions (less confident)
    - T < 1: Sharper predictions (more confident)
    - T = 1: No calibration
    
    Args:
        predictions: List of raw prediction dicts (before calibration)
        outcomes: List of actual outcome dicts
        initial_temp: Starting temperature value
    
    Returns:
        dict with optimal_temp, brier_score, improvement
    """
    
    def apply_temperature(probs_list, T):
        """Apply temperature scaling to all predictions"""
        calibrated = []
        for probs in probs_list:
            # Extract probabilities
            h = probs.get('home_win_prob', probs.get('home_win', 0))
            d = probs.get('draw_prob', probs.get('draw', 0))
            a = probs.get('away_win_prob', probs.get('away_win', 0))
            
            # Apply temperature
            h_scaled = h ** (1/T) if h > 0 else 0
            d_scaled = d ** (1/T) if d > 0 else 0
            a_scaled = a ** (1/T) if a > 0 else 0
            
            # Normalize
            total = h_scaled + d_scaled + a_scaled
            if total > 0:
                calibrated.append({
                    'home_win_prob': h_scaled / total,
                    'draw_prob': d_scaled / total,
                    'away_win_prob': a_scaled / total
                })
            else:
                # Fallback if all zeros
                calibrated.append({
                    'home_win_prob': 1/3,
                    'draw_prob': 1/3,
                    'away_win_prob': 1/3
                })
        
        return calibrated
    
    def objective(T):
        """Objective function: Brier score with temperature T"""
        calibrated_preds = apply_temperature(predictions, T)
        return calculate_brier_score(calibrated_preds, outcomes)
    
    # Optimize temperature between 0.5 and 2.0
    result = minimize_scalar(objective, bounds=(0.5, 2.0), method='bounded')
    
    # Calculate baseline (no calibration, T=1.0)
    baseline_score = objective(1.0)
    
    # Calculate improvement
    improvement = baseline_score - result.fun
    improvement_pct = (improvement / baseline_score) * 100 if baseline_score > 0 else 0
    
    return {
        'optimal_temperature': round(result.x, 3),
        'optimal_brier_score': round(result.fun, 4),
        'baseline_brier_score': round(baseline_score, 4),
        'improvement': round(improvement, 4),
        'improvement_pct': round(improvement_pct, 2),
        'recommendation': 'apply' if improvement > 0.001 else 'keep_current',
        'message': f"Optimal T={result.x:.3f} improves Brier score by {improvement_pct:.1f}%" if improvement > 0.001 
                   else f"Current calibration is already optimal (within 0.1%)"
    }


def validate_calibration(prediction_log_file):
    """
    Validate calibration temperature using historical predictions.
    
    Reads predictions from a JSON log file with format:
    [
        {
            "prediction": {"home_win_prob": 0.6, "draw_prob": 0.2, "away_win_prob": 0.2},
            "outcome": {"result": "home_win"}
        },
        ...
    ]
    
    Returns validation results and recommendation.
    """
    import json
    
    try:
        with open(prediction_log_file, 'r') as f:
            data = json.load(f)
        
        if not data:
            return {'error': 'No prediction data found'}
        
        predictions = [item['prediction'] for item in data if 'prediction' in item and 'outcome' in item]
        outcomes = [item['outcome'] for item in data if 'prediction' in item and 'outcome' in item]
        
        if len(predictions) < 10:
            return {
                'error': 'Insufficient data',
                'message': f'Need at least 10 completed predictions, found {len(predictions)}'
            }
        
        result = find_optimal_temperature(predictions, outcomes)
        result['data_points'] = len(predictions)
        
        return result
        
    except FileNotFoundError:
        return {'error': f'Prediction log file not found: {prediction_log_file}'}
    except Exception as e:
        return {'error': f'Validation failed: {str(e)}'}

# Example usage:
"""
# After collecting 50+ finished matches with predictions:
from ml_engine.calibration_validator import validate_calibration

results = validate_calibration('data/prediction_log.json')

if 'optimal_temperature' in results:
    print(f"Current T: 1.15")
    print(f"Optimal T: {results['optimal_temperature']}")
    print(f"Improvement: {results['improvement_pct']}%")
    print(f"Recommendation: {results['recommendation']}")
    
    if results['recommendation'] == 'apply':
        # Update calibration.py with new temperature
        pass
"""
