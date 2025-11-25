import json
import os
from ml_engine.ensemble_predictor import EnsemblePredictor

# Load data (same as in train_meta_model)
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")

def load_data():
    matches = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("season_") and filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename)) as f:
                matches.extend(json.load(f))
    matches.sort(key=lambda x: x['fixture']['date'])
    return matches

matches = load_data()
print(f"Loaded {len(matches)} matches for training all models.")

# Initialize predictor (which loads all models)
predictor = EnsemblePredictor()

# Dummy data for training (placeholders)
X_dummy = []
y_dummy = []

# Train each model (using placeholder train methods)
print("Training GBDTModel...")
predictor.gbdt.train(X_dummy, y_dummy)
print("Training CatBoostModel...")
predictor.catboost.train(X_dummy, y_dummy)
print("Training PoissonModel...")
predictor.poisson.train(matches)  # expects data
print("Training TransformerSequenceModel...")
predictor.transformer.train(matches)
print("Training LSTMSequenceModel...")
predictor.lstm.train(matches)
print("Training GNNModel...")
predictor.gnn.train(matches)
print("Training BayesianModel...")
predictor.bayesian.train(matches)
print("Training EloGlickoModel...")
predictor.elo.train(matches)
print("All models trained (placeholder).")
