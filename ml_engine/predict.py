
import sys
import json
from .ensemble_predictor import EnsemblePredictor

# Simple CLI wrapper for prediction if needed
if __name__ == "__main__":
    # In a real scenario, we might read features from stdin or args
    predictor = EnsemblePredictor()
    # Mock features
    features = {"home_id": 1, "away_id": 2} 
    result = predictor.predict_fixture(features)
    print(json.dumps(result, indent=2))
