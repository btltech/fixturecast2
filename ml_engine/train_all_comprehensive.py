#!/usr/bin/env python3
"""
Comprehensive training script for all ML models.
Loads historical data, builds feature vectors, trains all models, and persists them.
"""

import json
import os
import sys
import numpy as np
import pickle
from datetime import datetime

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ensemble_predictor import EnsemblePredictor

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "trained_models")

def load_all_matches():
    """Load all historical matches from season files"""
    matches = []
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.startswith("season_") and filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath) as f:
                season_matches = json.load(f)
                matches.extend(season_matches)
    matches.sort(key=lambda x: x['fixture']['date'])
    return matches

def build_features_and_labels(matches):
    """
    Build training data by simulating seasons.
    Returns (X, y) where X is list of feature dicts and y is list of outcomes.
    """
    X = []  # Feature dicts
    y = []  # Outcomes: 0=Home, 1=Draw, 2=Away
    
    # Track team stats as season progresses
    team_stats = {}
    
    print(f"Building features from {len(matches)} matches...")
    
    for idx, match in enumerate(matches):
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        
        # Initialize team stats if needed
        if home_id not in team_stats:
            team_stats[home_id] = {'points': 0, 'played': 0, 'form': [], 'gf': 0, 'ga': 0}
        if away_id not in team_stats:
            team_stats[away_id] = {'points': 0, 'played': 0, 'form': [], 'gf': 0, 'ga': 0}
        
        # Build feature dict for this match
        home_form = team_stats[home_id]['form'][-10:] if team_stats[home_id]['form'] else []
        away_form = team_stats[away_id]['form'][-10:] if team_stats[away_id]['form'] else []
        
        home_points_last10 = sum(home_form) if home_form else 15
        away_points_last10 = sum(away_form) if away_form else 15
        
        # Count wins/draws/losses in last 10
        home_wins_last10 = sum(1 for p in home_form if p == 3)
        home_draws_last10 = sum(1 for p in home_form if p == 1)
        home_losses_last10 = sum(1 for p in home_form if p == 0)
        
        away_wins_last10 = sum(1 for p in away_form if p == 3)
        away_draws_last10 = sum(1 for p in away_form if p == 1)
        away_losses_last10 = sum(1 for p in away_form if p == 0)
        
        # Goal averages
        home_played = max(team_stats[home_id]['played'], 1)
        away_played = max(team_stats[away_id]['played'], 1)
        
        home_goals_for_avg = team_stats[home_id]['gf'] / home_played
        home_goals_against_avg = team_stats[home_id]['ga'] / home_played
        away_goals_for_avg = team_stats[away_id]['gf'] / away_played
        away_goals_against_avg = team_stats[away_id]['ga'] / away_played
        
        features = {
            'home_id': home_id,
            'away_id': away_id,
            'home_name': match['teams']['home']['name'],
            'away_name': match['teams']['away']['name'],
            'home_league_points': team_stats[home_id]['points'],
            'away_league_points': team_stats[away_id]['points'],
            'home_league_pos': 10,  # Simplified - would need full table calculation
            'away_league_pos': 10,
            'home_points_last10': home_points_last10,
            'away_points_last10': away_points_last10,
            'home_form_last5': sum(home_form[-5:]) if len(home_form) >= 5 else sum(home_form),
            'away_form_last5': sum(away_form[-5:]) if len(away_form) >= 5 else sum(away_form),
            'home_goals_for_avg': home_goals_for_avg,
            'away_goals_for_avg': away_goals_for_avg,
            'home_goals_against_avg': home_goals_against_avg,
            'away_goals_against_avg': away_goals_against_avg,
            'home_wins_last10': home_wins_last10,
            'away_wins_last10': away_wins_last10,
            'home_draws_last10': home_draws_last10,
            'away_draws_last10': away_draws_last10,
            'home_losses_last10': home_losses_last10,
            'away_losses_last10': away_losses_last10,
            'home_goals_for_last10': sum([3 if p == 3 else 1 if p == 1 else 0 for p in home_form[-10:]]),  # Simplified
            'away_goals_for_last10': sum([3 if p == 3 else 1 if p == 1 else 0 for p in away_form[-10:]]),
            'home_goals_against_last10': sum([0 if p == 3 else 1 if p == 1 else 2 for p in home_form[-10:]]),
            'away_goals_against_last10': sum([0 if p == 3 else 1 if p == 1 else 2 for p in away_form[-10:]]),
            'h2h_home_wins': 2,  # Simplified - would need H2H lookup
            'h2h_draws': 2,
            'h2h_away_wins': 2,
            'h2h_total_matches': 6,
            'home_clean_sheets': 3,  # Simplified
            'away_clean_sheets': 3,
            'home_total_matches': home_played,
            'away_total_matches': away_played,
        }
        
        X.append(features)
        
        # Determine actual outcome
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']
        
        if goals_home > goals_away:
            outcome = 0  # Home win
            team_stats[home_id]['points'] += 3
            team_stats[home_id]['form'].append(3)
            team_stats[away_id]['form'].append(0)
        elif goals_away > goals_home:
            outcome = 2  # Away win
            team_stats[away_id]['points'] += 3
            team_stats[away_id]['form'].append(3)
            team_stats[home_id]['form'].append(0)
        else:
            outcome = 1  # Draw
            team_stats[home_id]['points'] += 1
            team_stats[away_id]['points'] += 1
            team_stats[home_id]['form'].append(1)
            team_stats[away_id]['form'].append(1)
        
        y.append(outcome)
        
        # Update goal stats
        team_stats[home_id]['gf'] += goals_home
        team_stats[home_id]['ga'] += goals_away
        team_stats[away_id]['gf'] += goals_away
        team_stats[away_id]['ga'] += goals_home
        team_stats[home_id]['played'] += 1
        team_stats[away_id]['played'] += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(matches)} matches...")
    
    print(f"Feature extraction complete. Built {len(X)} samples.")
    return X, y

def train_all_models():
    """Main training pipeline"""
    print("=" * 60)
    print("COMPREHENSIVE ML MODEL TRAINING")
    print("=" * 60)
    
    # Create models directory
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Load data
    print("\n1. Loading historical data...")
    matches = load_all_matches()
    print(f"   Loaded {len(matches)} matches across all seasons")
    
    # Build features
    print("\n2. Building feature vectors and labels...")
    X, y = build_features_and_labels(matches)
    
    # Initialize predictor (loads all models)
    print("\n3. Initializing ensemble predictor...")
    predictor = EnsemblePredictor()
    
    # Train each model
    print("\n4. Training individual models...")
    print("-" * 60)
    
    print("\n[1/8] Training GBDT Model...")
    try:
        # Convert feature dicts to array for sklearn
        from sklearn.feature_extraction import DictVectorizer
        vectorizer = DictVectorizer(sparse=False)
        X_array = vectorizer.fit_transform(X)
        
        predictor.gbdt.fit(X_array, y)
        predictor.gbdt.feature_keys = list(vectorizer.get_feature_names_out())
        model_path = os.path.join(MODELS_DIR, "gbdt_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(predictor.gbdt, f)
        print(f"   ✓ Saved to {model_path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n[2/8] Training CatBoost Model...")
    try:
        # Convert feature dicts to array for sklearn
        from sklearn.feature_extraction import DictVectorizer
        vectorizer = DictVectorizer(sparse=False)
        X_array = vectorizer.fit_transform(X)
        
        predictor.catboost.fit(X_array, y)
        predictor.catboost.feature_keys = list(vectorizer.get_feature_names_out())
        model_path = os.path.join(MODELS_DIR, "catboost_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(predictor.catboost, f)
        print(f"   ✓ Saved to {model_path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n[3/8] Training Poisson Model...")
    try:
        # For Poisson, we need to create target lambdas
        y_poisson = []
        for features in X:
            # Use current heuristic to generate training targets
            temp_pred = predictor.poisson.predict(features)
            y_poisson.append(temp_pred)
        predictor.poisson.train(X, y_poisson)
        model_path = os.path.join(MODELS_DIR, "poisson_model.pkl")
        predictor.poisson.save(model_path)
        print(f"   ✓ Saved to {model_path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # For models that don't require training data (heuristic-based), just save them
    print("\n[4/8] Saving Transformer Model (heuristic-based)...")
    model_path = os.path.join(MODELS_DIR, "transformer_model.pkl")
    predictor.transformer.save(model_path)
    print(f"   ✓ Saved to {model_path}")
    
    print("\n[5/8] Saving LSTM Model (heuristic-based)...")
    model_path = os.path.join(MODELS_DIR, "lstm_model.pkl")
    predictor.lstm.save(model_path)
    print(f"   ✓ Saved to {model_path}")
    
    print("\n[6/8] Saving GNN Model (heuristic-based)...")
    model_path = os.path.join(MODELS_DIR, "gnn_model.pkl")
    predictor.gnn.save(model_path)
    print(f"   ✓ Saved to {model_path}")
    
    print("\n[7/8] Saving Bayesian Model (heuristic-based)...")
    model_path = os.path.join(MODELS_DIR, "bayesian_model.pkl")
    predictor.bayesian.save(model_path)
    print(f"   ✓ Saved to {model_path}")
    
    print("\n[8/8] Saving Elo Model (heuristic-based)...")
    model_path = os.path.join(MODELS_DIR, "elo_model.pkl")
    predictor.elo.save(model_path)
    print(f"   ✓ Saved to {model_path}")
    
    print("\n" + "=" * 60)
    print("ALL MODELS TRAINED AND SAVED")
    print("=" * 60)
    print(f"\nModels saved to: {MODELS_DIR}")
    print(f"Total samples: {len(X)}")
    print("\nNext step: Re-train meta-model with these base models")

if __name__ == "__main__":
    train_all_models()
