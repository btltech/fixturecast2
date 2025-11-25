#!/usr/bin/env python3
"""
Fine-tuned training script with hyperparameter optimization.
Uses GridSearchCV to find optimal parameters for GBDT and CatBoost models.
"""

import json
import os
import sys
import numpy as np
from datetime import datetime
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.ensemble_predictor import EnsemblePredictor

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "trained_models")

def load_all_matches():
    """Load all historical matches"""
    matches = []
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.startswith("season_") and filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath) as f:
                matches.extend(json.load(f))
    matches.sort(key=lambda x: x['fixture']['date'])
    return matches

def extract_numeric_features(X):
    """Extract numeric features from feature dicts"""
    if not X:
        raise ValueError("Training data X cannot be empty")
    exclude_keys = ['home_id', 'away_id', 'home_name', 'away_name']
    feature_keys = [k for k in X[0].keys() if k not in exclude_keys and isinstance(X[0].get(k), (int, float))]
    X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
    return X_matrix, feature_keys

def build_features_and_labels(matches):
    """Build training data from matches"""
    X = []
    y = []
    team_stats = {}
    
    print(f"Building features from {len(matches)} matches...")
    
    for idx, match in enumerate(matches):
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        
        if home_id not in team_stats:
            team_stats[home_id] = {'points': 0, 'played': 0, 'form': [], 'gf': 0, 'ga': 0}
        if away_id not in team_stats:
            team_stats[away_id] = {'points': 0, 'played': 0, 'form': [], 'gf': 0, 'ga': 0}
        
        home_form = team_stats[home_id]['form'][-10:]
        away_form = team_stats[away_id]['form'][-10:]
        
        home_points_last10 = sum(home_form) if home_form else 15
        away_points_last10 = sum(away_form) if away_form else 15
        
        home_wins_last10 = sum(1 for p in home_form if p == 3)
        home_draws_last10 = sum(1 for p in home_form if p == 1)
        home_losses_last10 = sum(1 for p in home_form if p == 0)
        
        away_wins_last10 = sum(1 for p in away_form if p == 3)
        away_draws_last10 = sum(1 for p in away_form if p == 1)
        away_losses_last10 = sum(1 for p in away_form if p == 0)
        
        home_played = max(team_stats[home_id]['played'], 1)
        away_played = max(team_stats[away_id]['played'], 1)
        
        features = {
            'home_id': home_id,
            'away_id': away_id,
            'home_name': match['teams']['home']['name'],
            'away_name': match['teams']['away']['name'],
            'home_league_points': team_stats[home_id]['points'],
            'away_league_points': team_stats[away_id]['points'],
            'home_league_pos': 10,
            'away_league_pos': 10,
            'home_points_last10': home_points_last10,
            'away_points_last10': away_points_last10,
            'home_form_last5': sum(home_form[-5:]) if len(home_form) >= 5 else sum(home_form),
            'away_form_last5': sum(away_form[-5:]) if len(away_form) >= 5 else sum(away_form),
            'home_goals_for_avg': team_stats[home_id]['gf'] / home_played,
            'away_goals_for_avg': team_stats[away_id]['gf'] / away_played,
            'home_goals_against_avg': team_stats[home_id]['ga'] / home_played,
            'away_goals_against_avg': team_stats[away_id]['ga'] / away_played,
            'home_wins_last10': home_wins_last10,
            'away_wins_last10': away_wins_last10,
            'home_draws_last10': home_draws_last10,
            'away_draws_last10': away_draws_last10,
            'home_losses_last10': home_losses_last10,
            'away_losses_last10': away_losses_last10,
            'home_goals_for_last10': sum([3 if p == 3 else 1 if p == 1 else 0 for p in home_form[-10:]]),
            'away_goals_for_last10': sum([3 if p == 3 else 1 if p == 1 else 0 for p in away_form[-10:]]),
            'home_goals_against_last10': sum([0 if p == 3 else 1 if p == 1 else 2 for p in home_form[-10:]]),
            'away_goals_against_last10': sum([0 if p == 3 else 1 if p == 1 else 2 for p in away_form[-10:]]),
            'h2h_home_wins': 2,
            'h2h_draws': 2,
            'h2h_away_wins': 2,
            'h2h_total_matches': 6,
            'home_clean_sheets': 3,
            'away_clean_sheets': 3,
            'home_total_matches': home_played,
            'away_total_matches': away_played,
        }
        
        X.append(features)
        
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']
        
        if goals_home > goals_away:
            outcome = 0
            team_stats[home_id]['points'] += 3
            team_stats[home_id]['form'].append(3)
            team_stats[away_id]['form'].append(0)
        elif goals_away > goals_home:
            outcome = 2
            team_stats[away_id]['points'] += 3
            team_stats[away_id]['form'].append(3)
            team_stats[home_id]['form'].append(0)
        else:
            outcome = 1
            team_stats[home_id]['points'] += 1
            team_stats[away_id]['points'] += 1
            team_stats[home_id]['form'].append(1)
            team_stats[away_id]['form'].append(1)
        
        y.append(outcome)
        
        team_stats[home_id]['gf'] += goals_home
        team_stats[home_id]['ga'] += goals_away
        team_stats[away_id]['gf'] += goals_away
        team_stats[away_id]['ga'] += goals_home
        team_stats[home_id]['played'] += 1
        team_stats[away_id]['played'] += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(matches)} matches...")
    
    return X, y

def fine_tune_models():
    """Fine-tune models with hyperparameter optimization"""
    print("=" * 60)
    print("FINE-TUNING ML MODELS WITH HYPERPARAMETER OPTIMIZATION")
    print("=" * 60)
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("\n1. Loading historical data...")
    matches = load_all_matches()
    print(f"   Loaded {len(matches)} matches")
    
    print("\n2. Building features...")
    X, y = build_features_and_labels(matches)
    X_matrix, feature_keys = extract_numeric_features(X)
    y_array = np.array(y)
    
    print(f"\n3. Fine-tuning GBDT Model...")
    print("-" * 60)
    
    # Define hyperparameter grid for GBDT
    gbdt_param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.01, 0.1, 0.2],
        'min_samples_split': [2, 5, 10],
        'subsample': [0.8, 1.0]
    }
    
    gbdt_base = GradientBoostingClassifier(random_state=42)
    gbdt_grid = GridSearchCV(
        gbdt_base,
        gbdt_param_grid,
        cv=5,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1
    )
    
    print("Running grid search (this may take a few minutes)...")
    gbdt_grid.fit(X_matrix, y_array)
    
    print(f"\nBest GBDT parameters: {gbdt_grid.best_params_}")
    print(f"Best cross-validation score: {gbdt_grid.best_score_:.4f}")
    
    # Save best model
    best_gbdt = gbdt_grid.best_estimator_
    best_gbdt.feature_keys = feature_keys
    
    import joblib
    joblib.dump(best_gbdt, os.path.join(MODELS_DIR, "gbdt_model.pkl"))
    print("✓ Saved fine-tuned GBDT model")
    
    print(f"\n4. Fine-tuning CatBoost Model (LogisticRegression)...")
    print("-" * 60)
    
    # Define hyperparameter grid for Logistic Regression
    lr_param_grid = {
        'C': [0.01, 0.1, 1.0, 10.0],
        'solver': ['lbfgs', 'saga'],
        'max_iter': [500, 1000, 2000]
    }
    
    lr_base = LogisticRegression(random_state=42, multi_class='multinomial')
    lr_grid = GridSearchCV(
        lr_base,
        lr_param_grid,
        cv=5,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1
    )
    
    print("Running grid search...")
    lr_grid.fit(X_matrix, y_array)
    
    print(f"\nBest LogisticRegression parameters: {lr_grid.best_params_}")
    print(f"Best cross-validation score: {lr_grid.best_score_:.4f}")
    
    # Save best model
    best_lr = lr_grid.best_estimator_
    best_lr.feature_keys = feature_keys
    
    joblib.dump(best_lr, os.path.join(MODELS_DIR, "catboost_model.pkl"))
    print("✓ Saved fine-tuned CatBoost model")
    
    print("\n" + "=" * 60)
    print("FINE-TUNING COMPLETE")
    print("=" * 60)
    print(f"\nGBDT cross-val accuracy: {gbdt_grid.best_score_:.4f}")
    print(f"LogReg cross-val accuracy: {lr_grid.best_score_:.4f}")
    print(f"\nModels saved to: {MODELS_DIR}")
    print("\nNext: Re-run train_meta_model.py to update the ensemble")

if __name__ == "__main__":
    fine_tune_models()
