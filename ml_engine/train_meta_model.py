
import json
import os
import sys
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
import joblib

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ensemble_predictor import EnsemblePredictor

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "meta_model.pkl")

def load_data():
    matches = []
    # Load all season files
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("season_") and filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename)) as f:
                matches.extend(json.load(f))
    
    # Sort by date
    matches.sort(key=lambda x: x['fixture']['date'])
    return matches

def train_meta_model():
    print("Loading historical data...")
    matches = load_data()
    print(f"Loaded {len(matches)} matches.")
    
    predictor = EnsemblePredictor()
    
    X = [] # Model predictions
    y = [] # Actual results (0=Home, 1=Draw, 2=Away)
    
    # Team state tracking for feature generation
    # We need to simulate the season to get accurate "form" features
    # For simplicity in this v1 script, we will rely on the raw stats 
    # available in the match object if possible, or skip complex form features
    # and focus on the ensemble weighting.
    
    # Actually, to get valid predictions from our models, we need valid features.
    # Our models rely on 'home_points_last10', 'league_pos', etc.
    # We must simulate the season state.
    
    team_stats = {} # {team_id: {points: 0, matches: [], goals_for: 0...}}
    
    print("Simulating seasons and generating predictions...")
    
    processed = 0
    for match in matches:
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        
        # Initialize stats if new season or new team
        # (Simplified: we just accumulate forever for now, or reset on long gaps)
        if home_id not in team_stats: team_stats[home_id] = {'points': 0, 'played': 0, 'form': []}
        if away_id not in team_stats: team_stats[away_id] = {'points': 0, 'played': 0, 'form': []}
        
        # Build features from current state
        # This is a mini-FeatureBuilder
        features = {
            'home_id': home_id,
            'away_id': away_id,
            'home_name': match['teams']['home']['name'],
            'away_name': match['teams']['away']['name'],
            'home_league_points': team_stats[home_id]['points'],
            'away_league_points': team_stats[away_id]['points'],
            'home_league_pos': 10, # Mock rank (hard to calc efficiently without full table)
            'away_league_pos': 10,
            'home_points_last10': sum(team_stats[home_id]['form'][-5:]) * 2, # Approx
            'away_points_last10': sum(team_stats[away_id]['form'][-5:]) * 2,
            # New features: recent form sums (last 5 matches) and Poisson expected goals
            'home_form_last5': sum(team_stats[home_id]['form'][-5:]),
            'away_form_last5': sum(team_stats[away_id]['form'][-5:]),
            # Add other required keys with defaults to avoid errors
            'home_goals_for_avg': 1.5, 'away_goals_for_avg': 1.2,
            'home_goals_against_avg': 1.2, 'away_goals_against_avg': 1.5,
            'home_wins_last10': 3, 'away_wins_last10': 3,
            'home_draws_last10': 2, 'away_draws_last10': 2,
            'home_losses_last10': 3, 'away_losses_last10': 3,
        }
        # Compute Poisson expected goal lambdas and add to features
        poisson_res = predictor.poisson.predict(features)
        features.update(poisson_res)  # adds 'home_lambda' and 'away_lambda'
        
        # Get predictions from all 8 models
        # We access the models directly to get raw probs
        try:
            p_gbdt = predictor.gbdt.predict(features)
            p_cat = predictor.catboost.predict(features)
            p_trans = predictor.transformer.predict(features)
            p_lstm = predictor.lstm.predict(features)
            p_gnn = predictor.gnn.predict(features)
            p_bayes = predictor.bayesian.predict(features)
            p_elo = predictor.elo.predict(home_id, away_id, features)
            
            # Poisson/MC is expensive, let's skip or use simplified
            # We'll use the average of others as a proxy for MC to speed up training
            p_mc = p_gbdt # Placeholder
            
            # Feature vector for Meta-Model:
            # [Home_Prob_GBDT, Draw_Prob_GBDT, Away_Prob_GBDT, Home_Prob_Cat...]
            row = []
            for p in [p_gbdt, p_cat, p_trans, p_lstm, p_gnn, p_bayes, p_elo]:
                row.extend([p['home_win'], p['draw'], p['away_win']])
            
            X.append(row)
            
            # Actual result
            goals_home = match['goals']['home']
            goals_away = match['goals']['away']
            if goals_home > goals_away:
                y.append(0) # Home Win
                # Update stats
                team_stats[home_id]['points'] += 3
                team_stats[home_id]['form'].append(3)
                team_stats[away_id]['form'].append(0)
            elif goals_away > goals_home:
                y.append(2) # Away Win
                team_stats[away_id]['points'] += 3
                team_stats[away_id]['form'].append(3)
                team_stats[home_id]['form'].append(0)
            else:
                y.append(1) # Draw
                team_stats[home_id]['points'] += 1
                team_stats[away_id]['points'] += 1
                team_stats[home_id]['form'].append(1)
                team_stats[away_id]['form'].append(1)
                
            team_stats[home_id]['played'] += 1
            team_stats[away_id]['played'] += 1
            
            processed += 1
            if processed % 100 == 0:
                print(f"Processed {processed} matches...")
                
        except Exception as e:
            print(f"Error processing match: {e}")
            continue

    print(f"Training Meta-Model on {len(X)} samples...")
    
    # Train Logistic Regression
    # Multi-class (Home, Draw, Away)
    clf = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    clf.fit(X, y)
    
    print(f"Training Score: {clf.score(X, y):.4f}")
    
    # Save model
    joblib.dump(clf, MODEL_PATH)
    print(f"Meta-model saved to {MODEL_PATH}")
    
    # Print weights (Coefficients)
    print("\nLearned Weights (Importance of each model):")
    models = ['GBDT', 'CatBoost', 'Transformer', 'LSTM', 'GNN', 'Bayesian', 'Elo']
    # Coef shape is (3, n_features). We can average importance.
    avg_coefs = np.mean(np.abs(clf.coef_), axis=0)
    
    # Reshape to (n_models, 3) since we have 3 probs per model
    reshaped = avg_coefs.reshape(len(models), 3)
    model_importance = np.sum(reshaped, axis=1)
    
    # Normalize
    model_importance = model_importance / np.sum(model_importance)
    
    for m, imp in zip(models, model_importance):
        print(f"{m}: {imp:.1%}")

if __name__ == "__main__":
    train_meta_model()
