#!/usr/bin/env python3
"""
Model Performance Tracker
Tracks Brier score, log loss, calibration, and accuracy metrics.
"""

import json
import os
import numpy as np
from datetime import datetime
from collections import defaultdict


class ModelPerformanceTracker:
    """
    Tracks and evaluates prediction performance.
    """
    
    def __init__(self):
        self.predictions = []  # List of (prediction, actual_outcome)
        self.model_predictions = defaultdict(list)  # model_name -> predictions
        
    def add_prediction(self, prediction, actual_outcome, model_name='ensemble'):
        """
        Add a prediction for tracking.
        
        Args:
            prediction: dict with home_win, draw, away_win probabilities
            actual_outcome: 0 (home), 1 (draw), 2 (away)
            model_name: identifier for the model
        """
        self.predictions.append({
            'probs': prediction,
            'actual': actual_outcome,
            'model': model_name,
            'timestamp': datetime.now().isoformat()
        })
        self.model_predictions[model_name].append({
            'probs': prediction,
            'actual': actual_outcome
        })
    
    def calculate_brier_score(self, predictions=None):
        """
        Calculate Brier score (lower is better, 0 is perfect).
        Measures accuracy of probabilistic predictions.
        """
        if predictions is None:
            predictions = self.predictions
        
        if not predictions:
            return None
        
        brier_sum = 0
        for pred in predictions:
            probs = pred['probs']
            actual = pred['actual']
            
            # One-hot encode actual outcome
            actual_vec = [0, 0, 0]
            actual_vec[actual] = 1
            
            # Get predicted probabilities in order [home, draw, away]
            pred_vec = [
                probs.get('home_win', probs.get('home_win_prob', 0.33)),
                probs.get('draw', probs.get('draw_prob', 0.33)),
                probs.get('away_win', probs.get('away_win_prob', 0.33))
            ]
            
            # Brier score = mean squared error
            brier_sum += sum((p - a) ** 2 for p, a in zip(pred_vec, actual_vec))
        
        return brier_sum / len(predictions)
    
    def calculate_log_loss(self, predictions=None, eps=1e-15):
        """
        Calculate log loss (lower is better).
        More sensitive to confident wrong predictions.
        """
        if predictions is None:
            predictions = self.predictions
        
        if not predictions:
            return None
        
        log_loss_sum = 0
        for pred in predictions:
            probs = pred['probs']
            actual = pred['actual']
            
            # Get predicted probabilities
            pred_vec = [
                probs.get('home_win', probs.get('home_win_prob', 0.33)),
                probs.get('draw', probs.get('draw_prob', 0.33)),
                probs.get('away_win', probs.get('away_win_prob', 0.33))
            ]
            
            # Clip to avoid log(0)
            prob_actual = max(eps, min(1 - eps, pred_vec[actual]))
            log_loss_sum -= np.log(prob_actual)
        
        return log_loss_sum / len(predictions)
    
    def calculate_accuracy(self, predictions=None):
        """
        Calculate prediction accuracy (highest probability = prediction).
        """
        if predictions is None:
            predictions = self.predictions
        
        if not predictions:
            return None
        
        correct = 0
        for pred in predictions:
            probs = pred['probs']
            actual = pred['actual']
            
            pred_vec = [
                probs.get('home_win', probs.get('home_win_prob', 0.33)),
                probs.get('draw', probs.get('draw_prob', 0.33)),
                probs.get('away_win', probs.get('away_win_prob', 0.33))
            ]
            
            predicted = np.argmax(pred_vec)
            if predicted == actual:
                correct += 1
        
        return correct / len(predictions)
    
    def get_calibration_data(self, predictions=None, n_bins=10):
        """
        Get calibration data for reliability diagram.
        Groups predictions by confidence and compares to actual frequency.
        """
        if predictions is None:
            predictions = self.predictions
        
        if not predictions:
            return None
        
        # Group by confidence bins
        bins = defaultdict(lambda: {'count': 0, 'correct': 0, 'sum_conf': 0})
        
        for pred in predictions:
            probs = pred['probs']
            actual = pred['actual']
            
            pred_vec = [
                probs.get('home_win', probs.get('home_win_prob', 0.33)),
                probs.get('draw', probs.get('draw_prob', 0.33)),
                probs.get('away_win', probs.get('away_win_prob', 0.33))
            ]
            
            # Get max confidence and prediction
            confidence = max(pred_vec)
            predicted = np.argmax(pred_vec)
            
            # Determine bin
            bin_idx = min(int(confidence * n_bins), n_bins - 1)
            
            bins[bin_idx]['count'] += 1
            bins[bin_idx]['sum_conf'] += confidence
            if predicted == actual:
                bins[bin_idx]['correct'] += 1
        
        # Calculate accuracy and average confidence per bin
        calibration = []
        for i in range(n_bins):
            if bins[i]['count'] > 0:
                avg_conf = bins[i]['sum_conf'] / bins[i]['count']
                accuracy = bins[i]['correct'] / bins[i]['count']
                calibration.append({
                    'bin': i,
                    'avg_confidence': round(avg_conf, 3),
                    'accuracy': round(accuracy, 3),
                    'count': bins[i]['count']
                })
        
        return calibration
    
    def get_accuracy_by_confidence(self, predictions=None):
        """
        Get accuracy grouped by confidence level.
        """
        if predictions is None:
            predictions = self.predictions
        
        if not predictions:
            return None
        
        confidence_groups = {
            'high': {'min': 0.5, 'correct': 0, 'total': 0},
            'medium': {'min': 0.4, 'correct': 0, 'total': 0},
            'low': {'min': 0.0, 'correct': 0, 'total': 0}
        }
        
        for pred in predictions:
            probs = pred['probs']
            actual = pred['actual']
            
            pred_vec = [
                probs.get('home_win', probs.get('home_win_prob', 0.33)),
                probs.get('draw', probs.get('draw_prob', 0.33)),
                probs.get('away_win', probs.get('away_win_prob', 0.33))
            ]
            
            confidence = max(pred_vec)
            predicted = np.argmax(pred_vec)
            correct = 1 if predicted == actual else 0
            
            if confidence >= 0.5:
                confidence_groups['high']['correct'] += correct
                confidence_groups['high']['total'] += 1
            elif confidence >= 0.4:
                confidence_groups['medium']['correct'] += correct
                confidence_groups['medium']['total'] += 1
            else:
                confidence_groups['low']['correct'] += correct
                confidence_groups['low']['total'] += 1
        
        results = {}
        for level, data in confidence_groups.items():
            if data['total'] > 0:
                results[level] = {
                    'accuracy': round(data['correct'] / data['total'], 3),
                    'count': data['total']
                }
            else:
                results[level] = {'accuracy': None, 'count': 0}
        
        return results
    
    def get_full_report(self):
        """Generate comprehensive performance report."""
        return {
            'total_predictions': len(self.predictions),
            'brier_score': round(self.calculate_brier_score() or 0, 4),
            'log_loss': round(self.calculate_log_loss() or 0, 4),
            'accuracy': round(self.calculate_accuracy() or 0, 4),
            'accuracy_by_confidence': self.get_accuracy_by_confidence(),
            'calibration': self.get_calibration_data()
        }
    
    def save(self, path):
        """Save predictions to file."""
        data = {
            'predictions': self.predictions,
            'report': self.get_full_report()
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path):
        """Load predictions from file."""
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.predictions = data.get('predictions', [])
            return True
        return False


def evaluate_model_on_holdout(predictor, test_matches):
    """
    Evaluate a trained predictor on holdout test matches.
    """
    tracker = ModelPerformanceTracker()
    
    for match in test_matches:
        features = match['features']
        actual_home = match['goals']['home']
        actual_away = match['goals']['away']
        
        # Determine actual outcome
        if actual_home > actual_away:
            actual = 0  # Home win
        elif actual_home < actual_away:
            actual = 2  # Away win
        else:
            actual = 1  # Draw
        
        # Get prediction
        try:
            prediction = predictor.predict_fixture(features)
            tracker.add_prediction({
                'home_win': prediction['home_win_prob'],
                'draw': prediction['draw_prob'],
                'away_win': prediction['away_win_prob']
            }, actual)
        except Exception as e:
            print(f"Error predicting match: {e}")
    
    return tracker.get_full_report()
