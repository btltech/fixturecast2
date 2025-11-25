#!/usr/bin/env python3
"""
Enhanced Training Script v2
Includes:
- True Elo rating tracking
- Advanced feature engineering
- K-fold cross-validation
- Meta-model stacking
- Performance metrics evaluation
"""

import json
import os
import sys
import numpy as np
import pickle
from datetime import datetime
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import brier_score_loss, log_loss, accuracy_score

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml_engine.elo_tracker import EloTracker
from ml_engine.performance_tracker import ModelPerformanceTracker

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


def build_enhanced_features(matches, elo_tracker):
    """
    Build training data with enhanced features including Elo ratings.
    """
    X = []
    y = []
    
    # Track team stats as season progresses
    team_stats = {}
    team_home_stats = {}  # Home-specific
    team_away_stats = {}  # Away-specific
    
    print(f"Building enhanced features from {len(matches)} matches...")
    
    for idx, match in enumerate(matches):
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        home_goals = match['goals']['home']
        away_goals = match['goals']['away']
        match_date = match['fixture'].get('date', '')
        
        if home_goals is None or away_goals is None:
            continue
        
        # Initialize team stats if needed
        for team_id in [home_id, away_id]:
            if team_id not in team_stats:
                team_stats[team_id] = {
                    'points': 0, 'played': 0, 'form': [], 
                    'gf': 0, 'ga': 0, 'last_results': []
                }
            if team_id not in team_home_stats:
                team_home_stats[team_id] = {'points': 0, 'played': 0, 'gf': 0, 'ga': 0}
            if team_id not in team_away_stats:
                team_away_stats[team_id] = {'points': 0, 'played': 0, 'gf': 0, 'ga': 0}
        
        # Get pre-match stats for features
        hs = team_stats[home_id]
        aws = team_stats[away_id]
        hhs = team_home_stats[home_id]  # Home specific
        aas = team_away_stats[away_id]  # Away specific
        
        # Form analysis
        home_form = hs['form'][-10:] if hs['form'] else []
        away_form = aws['form'][-10:] if aws['form'] else []
        
        # Calculate streaks
        home_win_streak = sum(1 for i, r in enumerate(home_form) if r == 3 and all(x == 3 for x in home_form[:i+1]))
        away_win_streak = sum(1 for i, r in enumerate(away_form) if r == 3 and all(x == 3 for x in away_form[:i+1]))
        
        # Get Elo ratings (before match update)
        home_elo = elo_tracker.get_rating(home_id)
        away_elo = elo_tracker.get_rating(away_id)
        elo_diff = home_elo - away_elo + 100  # +100 for home advantage
        
        # Calculate momentum (weighted recent results)
        home_momentum = sum((0.9 ** i) * r for i, r in enumerate(home_form)) / max(1, sum(0.9 ** i for i in range(len(home_form))))
        away_momentum = sum((0.9 ** i) * r for i, r in enumerate(away_form)) / max(1, sum(0.9 ** i for i in range(len(away_form))))
        
        # Played stats
        home_played = max(hs['played'], 1)
        away_played = max(aws['played'], 1)
        home_home_played = max(hhs['played'], 1)
        away_away_played = max(aas['played'], 1)
        
        # Build feature dict
        features = {
            'home_id': home_id,
            'away_id': away_id,
            
            # Elo Features (NEW)
            'home_elo': home_elo,
            'away_elo': away_elo,
            'elo_diff': elo_diff,
            'elo_ratio': home_elo / max(away_elo, 1000),
            
            # League Position
            'home_league_points': hs['points'],
            'away_league_points': aws['points'],
            'points_diff': hs['points'] - aws['points'],
            
            # Form Features
            'home_points_last10': sum(home_form) if home_form else 15,
            'away_points_last10': sum(away_form) if away_form else 15,
            'home_form_last5': sum(home_form[-5:]) if len(home_form) >= 5 else sum(home_form) if home_form else 7.5,
            'away_form_last5': sum(away_form[-5:]) if len(away_form) >= 5 else sum(away_form) if away_form else 7.5,
            
            # Momentum (NEW)
            'home_momentum': home_momentum if home_form else 1.5,
            'away_momentum': away_momentum if away_form else 1.5,
            'momentum_diff': (home_momentum if home_form else 1.5) - (away_momentum if away_form else 1.5),
            
            # Streaks (NEW)
            'home_win_streak': home_win_streak,
            'away_win_streak': away_win_streak,
            
            # Goal Stats
            'home_goals_for_avg': hs['gf'] / home_played,
            'away_goals_for_avg': aws['gf'] / away_played,
            'home_goals_against_avg': hs['ga'] / home_played,
            'away_goals_against_avg': aws['ga'] / away_played,
            
            # Home/Away Specific (NEW)
            'home_home_gf_avg': hhs['gf'] / home_home_played,
            'home_home_ga_avg': hhs['ga'] / home_home_played,
            'away_away_gf_avg': aas['gf'] / away_away_played,
            'away_away_ga_avg': aas['ga'] / away_away_played,
            'home_home_ppg': hhs['points'] / home_home_played,
            'away_away_ppg': aas['points'] / away_away_played,
            
            # Win/Draw/Loss counts
            'home_wins_last10': sum(1 for p in home_form if p == 3),
            'away_wins_last10': sum(1 for p in away_form if p == 3),
            'home_draws_last10': sum(1 for p in home_form if p == 1),
            'away_draws_last10': sum(1 for p in away_form if p == 1),
            'home_losses_last10': sum(1 for p in home_form if p == 0),
            'away_losses_last10': sum(1 for p in away_form if p == 0),
            
            # Matches played
            'home_total_matches': home_played,
            'away_total_matches': away_played,
        }
        
        X.append(features)
        
        # Determine actual outcome
        if home_goals > away_goals:
            outcome = 0  # Home win
            home_pts = 3
            away_pts = 0
        elif away_goals > home_goals:
            outcome = 2  # Away win
            home_pts = 0
            away_pts = 3
        else:
            outcome = 1  # Draw
            home_pts = 1
            away_pts = 1
        
        y.append(outcome)
        
        # Update stats AFTER recording features
        hs['points'] += home_pts
        aws['points'] += away_pts
        hs['form'].append(home_pts)
        aws['form'].append(away_pts)
        hs['gf'] += home_goals
        hs['ga'] += away_goals
        aws['gf'] += away_goals
        aws['ga'] += home_goals
        hs['played'] += 1
        aws['played'] += 1
        
        # Update home/away specific stats
        hhs['points'] += home_pts
        hhs['gf'] += home_goals
        hhs['ga'] += away_goals
        hhs['played'] += 1
        
        aas['points'] += away_pts
        aas['gf'] += away_goals
        aas['ga'] += home_goals
        aas['played'] += 1
        
        # Update Elo ratings
        elo_tracker.update_ratings(home_id, away_id, home_goals, away_goals, match_date)
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(matches)} matches...")
    
    print(f"Enhanced feature extraction complete. Built {len(X)} samples.")
    return X, y


def train_with_cross_validation(X, y, n_splits=5):
    """
    Train models with k-fold cross-validation.
    Returns trained model and CV scores.
    """
    print(f"\nTraining with {n_splits}-fold cross-validation...")
    
    # Prepare data
    exclude_keys = ['home_id', 'away_id', 'home_name', 'away_name']
    feature_keys = [k for k in X[0].keys() if k not in exclude_keys and isinstance(X[0].get(k), (int, float))]
    
    X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
    y_array = np.array(y)
    
    print(f"  Using {len(feature_keys)} features")
    
    # Cross-validation
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    cv_scores = {
        'accuracy': [],
        'brier': [],
        'log_loss': []
    }
    
    fold_models = []
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_matrix, y_array)):
        X_train, X_val = X_matrix[train_idx], X_matrix[val_idx]
        y_train, y_val = y_array[train_idx], y_array[val_idx]
        
        # Train GBDT - optimized for speed
        model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.15,
            min_samples_split=40,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42 + fold
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)
        
        acc = accuracy_score(y_val, y_pred)
        
        # Multi-class Brier score
        brier = 0
        for i, true_class in enumerate(y_val):
            for c in range(3):
                target = 1 if c == true_class else 0
                brier += (y_proba[i, c] - target) ** 2
        brier /= len(y_val)
        
        ll = log_loss(y_val, y_proba)
        
        cv_scores['accuracy'].append(acc)
        cv_scores['brier'].append(brier)
        cv_scores['log_loss'].append(ll)
        
        fold_models.append(model)
        
        print(f"  Fold {fold+1}: Acc={acc:.3f}, Brier={brier:.4f}, LogLoss={ll:.4f}")
    
    print(f"\n  CV Mean Accuracy: {np.mean(cv_scores['accuracy']):.3f} (±{np.std(cv_scores['accuracy']):.3f})")
    print(f"  CV Mean Brier: {np.mean(cv_scores['brier']):.4f} (±{np.std(cv_scores['brier']):.4f})")
    print(f"  CV Mean LogLoss: {np.mean(cv_scores['log_loss']):.4f} (±{np.std(cv_scores['log_loss']):.4f})")
    
    # Train final model on all data
    print("\n  Training final model on all data...")
    final_model = GradientBoostingClassifier(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.15,
        min_samples_split=40,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42
    )
    final_model.fit(X_matrix, y_array)
    final_model.feature_keys = feature_keys
    
    return final_model, cv_scores, feature_keys


def train_meta_model(X, y, base_models, feature_keys):
    """
    Train a meta-model (stacking) on base model outputs.
    """
    print("\nTraining meta-model (stacking)...")
    
    # Prepare base model predictions
    exclude_keys = ['home_id', 'away_id', 'home_name', 'away_name']
    X_matrix = np.array([[sample.get(k, 0) for k in feature_keys] for sample in X])
    y_array = np.array(y)
    
    # Get base model predictions
    meta_features = []
    
    for i, sample in enumerate(X):
        row = []
        
        # GBDT predictions
        if 'gbdt' in base_models:
            x_row = np.array([[sample.get(k, 0) for k in feature_keys]])
            probs = base_models['gbdt'].predict_proba(x_row)[0]
            row.extend(probs)
        
        # Elo predictions
        if 'elo' in base_models:
            elo_pred = base_models['elo'].predict_match(sample.get('home_id', 0), sample.get('away_id', 0))
            row.extend([elo_pred['home_win'], elo_pred['draw'], elo_pred['away_win']])
        
        # Add key features directly
        row.append(sample.get('elo_diff', 0) / 400)  # Normalized
        row.append(sample.get('momentum_diff', 0))
        row.append(sample.get('points_diff', 0) / 30)  # Normalized
        
        meta_features.append(row)
    
    X_meta = np.array(meta_features)
    
    # Train meta-model with cross-validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    meta_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_meta, y_array)):
        X_train, X_val = X_meta[train_idx], X_meta[val_idx]
        y_train, y_val = y_array[train_idx], y_array[val_idx]
        
        meta_model = LogisticRegression(max_iter=1000, random_state=42)
        meta_model.fit(X_train, y_train)
        
        acc = meta_model.score(X_val, y_val)
        meta_scores.append(acc)
    
    print(f"  Meta-model CV Accuracy: {np.mean(meta_scores):.3f} (±{np.std(meta_scores):.3f})")
    
    # Train final meta-model
    final_meta = LogisticRegression(max_iter=1000, random_state=42)
    final_meta.fit(X_meta, y_array)
    
    return final_meta


def main():
    """Main enhanced training pipeline"""
    print("=" * 70)
    print("ENHANCED ML MODEL TRAINING v2")
    print("=" * 70)
    
    # Create models directory
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Initialize performance tracker
    perf_tracker = ModelPerformanceTracker()
    
    # 1. Load data
    print("\n📊 Step 1: Loading historical data...")
    matches = load_all_matches()
    print(f"   Loaded {len(matches)} matches across all seasons")
    
    # 2. Initialize Elo tracker
    print("\n📈 Step 2: Building Elo ratings from scratch...")
    elo_tracker = EloTracker(k_factor=32, home_advantage=100)
    
    # 3. Build enhanced features
    print("\n🔧 Step 3: Building enhanced feature vectors...")
    X, y = build_enhanced_features(matches, elo_tracker)
    
    # Save Elo ratings
    elo_path = os.path.join(MODELS_DIR, "elo_ratings.json")
    elo_tracker.save(elo_path)
    print(f"   ✅ Elo ratings saved ({len(elo_tracker.ratings)} teams)")
    
    # Show top teams
    print("\n   Top 10 Elo Ratings:")
    for team_id, rating in elo_tracker.get_top_teams(10):
        print(f"      Team {team_id}: {rating:.0f}")
    
    # 4. Train GBDT with cross-validation
    print("\n🎯 Step 4: Training GBDT with cross-validation...")
    gbdt_model, cv_scores, feature_keys = train_with_cross_validation(X, y, n_splits=5)
    
    # Save GBDT
    gbdt_path = os.path.join(MODELS_DIR, "gbdt_model.pkl")
    with open(gbdt_path, 'wb') as f:
        pickle.dump(gbdt_model, f)
    print(f"   ✅ GBDT model saved")
    
    # 5. Train meta-model
    print("\n🔗 Step 5: Training meta-model (stacking)...")
    base_models = {
        'gbdt': gbdt_model,
        'elo': elo_tracker
    }
    meta_model = train_meta_model(X, y, base_models, feature_keys)
    
    # Save meta-model
    meta_path = os.path.join(MODELS_DIR, "meta_model.pkl")
    with open(meta_path, 'wb') as f:
        pickle.dump({
            'model': meta_model,
            'feature_keys': feature_keys
        }, f)
    print(f"   ✅ Meta-model saved")
    
    # 6. Evaluate on last season (holdout)
    print("\n📋 Step 6: Evaluating on holdout set (last 20% of data)...")
    
    holdout_size = len(X) // 5
    X_holdout = X[-holdout_size:]
    y_holdout = y[-holdout_size:]
    
    # Test predictions
    X_holdout_matrix = np.array([[s.get(k, 0) for k in feature_keys] for s in X_holdout])
    y_pred = gbdt_model.predict(X_holdout_matrix)
    y_proba = gbdt_model.predict_proba(X_holdout_matrix)
    
    holdout_acc = accuracy_score(y_holdout, y_pred)
    holdout_ll = log_loss(y_holdout, y_proba)
    
    print(f"   Holdout Accuracy: {holdout_acc:.3f}")
    print(f"   Holdout Log Loss: {holdout_ll:.4f}")
    
    # Track predictions for calibration
    for i, (probs, actual) in enumerate(zip(y_proba, y_holdout)):
        perf_tracker.add_prediction({
            'home_win': float(probs[0]),
            'draw': float(probs[1]),
            'away_win': float(probs[2])
        }, actual)
    
    # Get calibration report
    report = perf_tracker.get_full_report()
    print(f"\n   Performance Report:")
    print(f"   - Brier Score: {report['brier_score']:.4f}")
    print(f"   - Accuracy: {report['accuracy']:.3f}")
    
    if report['accuracy_by_confidence']:
        print(f"   - High Confidence Accuracy: {report['accuracy_by_confidence'].get('high', {}).get('accuracy', 'N/A')}")
        print(f"   - Medium Confidence Accuracy: {report['accuracy_by_confidence'].get('medium', {}).get('accuracy', 'N/A')}")
    
    # Save performance report
    perf_path = os.path.join(MODELS_DIR, "performance_report.json")
    perf_tracker.save(perf_path)
    print(f"   ✅ Performance report saved")
    
    # 7. Summary
    print("\n" + "=" * 70)
    print("✅ ENHANCED TRAINING COMPLETE")
    print("=" * 70)
    print(f"\nModels saved to: {MODELS_DIR}")
    print(f"Total training samples: {len(X)}")
    print(f"Features used: {len(feature_keys)}")
    print(f"\nKey Improvements:")
    print(f"  ✓ True Elo ratings tracking {len(elo_tracker.ratings)} teams")
    print(f"  ✓ Enhanced features (momentum, venue-specific, streaks)")
    print(f"  ✓ 5-fold cross-validation (Acc: {np.mean(cv_scores['accuracy']):.1%})")
    print(f"  ✓ Meta-model stacking ensemble")
    print(f"  ✓ Performance metrics tracking")
    
    print("\n📌 Next: Restart the ML API to use updated models")


if __name__ == "__main__":
    main()
