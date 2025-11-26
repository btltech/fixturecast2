#!/usr/bin/env python3
"""
Unit tests for EnsemblePredictor.
Tests prediction consistency, model loading, and feature handling.
"""

import os
import sys

import numpy as np
import pytest

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml_engine.ensemble_predictor import EnsemblePredictor


class TestEnsemblePredictor:
    """Tests for the EnsemblePredictor class"""

    @pytest.fixture
    def predictor(self):
        """Create a predictor instance for testing"""
        return EnsemblePredictor(load_trained=True)

    @pytest.fixture
    def sample_features(self):
        """Sample feature dict for testing"""
        return {
            "home_id": 50,
            "away_id": 42,
            "home_name": "Manchester City",
            "away_name": "Arsenal",
            "home_league_points": 45,
            "away_league_points": 42,
            "home_league_pos": 1,
            "away_league_pos": 3,
            "home_points_last10": 24,
            "away_points_last10": 21,
            "home_form_last5": 12,
            "away_form_last5": 10,
            "home_goals_for_avg": 2.5,
            "away_goals_for_avg": 2.1,
            "home_goals_against_avg": 0.8,
            "away_goals_against_avg": 1.0,
            "home_wins_last10": 7,
            "away_wins_last10": 6,
            "home_draws_last10": 2,
            "away_draws_last10": 2,
            "home_losses_last10": 1,
            "away_losses_last10": 2,
            "home_goals_for_last10": 22,
            "away_goals_for_last10": 18,
            "home_goals_against_last10": 8,
            "away_goals_against_last10": 10,
            "h2h_home_wins": 8,
            "h2h_draws": 4,
            "h2h_away_wins": 5,
            "h2h_total_matches": 17,
            "home_clean_sheets": 10,
            "away_clean_sheets": 8,
            "home_total_matches": 20,
            "away_total_matches": 20,
            "odds_available": False,
        }

    def test_predictor_initialization(self, predictor):
        """Test that predictor initializes correctly"""
        assert predictor is not None
        assert hasattr(predictor, "gbdt")
        assert hasattr(predictor, "catboost")
        assert hasattr(predictor, "transformer")
        assert hasattr(predictor, "lstm")
        assert hasattr(predictor, "gnn")
        assert hasattr(predictor, "bayesian")
        assert hasattr(predictor, "elo")
        assert hasattr(predictor, "poisson")
        assert hasattr(predictor, "mc")
        assert hasattr(predictor, "calibration")

    def test_vectorizers_loaded(self, predictor):
        """Test that vectorizers are loaded"""
        assert hasattr(predictor, "vectorizers")
        assert isinstance(predictor.vectorizers, dict)
        # Should have at least some vectorizers if models are trained
        if os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "ml_engine", "trained_models")
        ):
            assert len(predictor.vectorizers) > 0

    def test_prediction_returns_required_keys(self, predictor, sample_features):
        """Test that prediction returns all required keys"""
        result = predictor.predict_fixture(sample_features)

        required_keys = [
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "predicted_scoreline",
            "btts_prob",
            "over25_prob",
            "model_breakdown",
        ]

        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_probabilities_sum_to_one(self, predictor, sample_features):
        """Test that win probabilities sum to approximately 1"""
        result = predictor.predict_fixture(sample_features)

        total_prob = result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]

        assert 0.95 <= total_prob <= 1.05, f"Probabilities sum to {total_prob}, expected ~1.0"

    def test_probabilities_in_valid_range(self, predictor, sample_features):
        """Test that all probabilities are between 0 and 1"""
        result = predictor.predict_fixture(sample_features)

        probs = [
            result["home_win_prob"],
            result["draw_prob"],
            result["away_win_prob"],
            result["btts_prob"],
            result["over25_prob"],
        ]

        for prob in probs:
            assert 0 <= prob <= 1, f"Probability {prob} out of range [0, 1]"

    def test_prediction_consistency(self, predictor, sample_features):
        """Test that same features produce consistent predictions"""
        result1 = predictor.predict_fixture(sample_features)
        result2 = predictor.predict_fixture(sample_features)

        # Allow small floating point differences
        assert abs(result1["home_win_prob"] - result2["home_win_prob"]) < 0.01
        assert abs(result1["draw_prob"] - result2["draw_prob"]) < 0.01
        assert abs(result1["away_win_prob"] - result2["away_win_prob"]) < 0.01

    def test_model_breakdown_structure(self, predictor, sample_features):
        """Test that model breakdown has expected structure"""
        result = predictor.predict_fixture(sample_features)
        breakdown = result["model_breakdown"]

        expected_models = ["gbdt", "catboost", "transformer", "lstm", "gnn", "bayesian", "elo"]

        for model in expected_models:
            assert model in breakdown, f"Missing model in breakdown: {model}"
            model_pred = breakdown[model]
            assert "home_win" in model_pred
            assert "draw" in model_pred
            assert "away_win" in model_pred

    def test_scoreline_format(self, predictor, sample_features):
        """Test that predicted scoreline is in correct format"""
        result = predictor.predict_fixture(sample_features)
        scoreline = result["predicted_scoreline"]

        assert "-" in scoreline
        parts = scoreline.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_different_inputs_different_outputs(self, predictor, sample_features):
        """Test that different inputs produce different outputs"""
        result1 = predictor.predict_fixture(sample_features)

        # Create modified features (weaker home team)
        modified_features = sample_features.copy()
        modified_features["home_league_pos"] = 15
        modified_features["home_goals_for_avg"] = 0.8
        modified_features["home_wins_last10"] = 2

        result2 = predictor.predict_fixture(modified_features)

        # Results should differ
        assert result1["home_win_prob"] != result2["home_win_prob"]

    def test_extreme_features_handling(self, predictor):
        """Test handling of extreme feature values"""
        extreme_features = {
            "home_id": 1,
            "away_id": 2,
            "home_name": "Team A",
            "away_name": "Team B",
            "home_league_points": 0,
            "away_league_points": 100,
            "home_league_pos": 20,
            "away_league_pos": 1,
            "home_goals_for_avg": 0.0,
            "away_goals_for_avg": 5.0,
            "home_goals_against_avg": 5.0,
            "away_goals_against_avg": 0.0,
            "home_wins_last10": 0,
            "away_wins_last10": 10,
            "h2h_home_wins": 0,
            "h2h_away_wins": 10,
            "h2h_draws": 0,
            "h2h_total_matches": 10,
            "home_clean_sheets": 0,
            "away_clean_sheets": 15,
            "home_total_matches": 20,
            "away_total_matches": 20,
        }

        # Should not raise an exception
        result = predictor.predict_fixture(extreme_features)

        # Away team should be heavily favored
        assert result["away_win_prob"] > result["home_win_prob"]


class TestVectorization:
    """Tests for feature vectorization"""

    @pytest.fixture
    def predictor(self):
        return EnsemblePredictor(load_trained=True)

    def test_vectorize_features(self, predictor):
        """Test that features can be vectorized"""
        if "main" in predictor.vectorizers:
            features = {"home_id": 1, "away_id": 2, "home_league_pos": 5}
            result = predictor._vectorize_features(features, "main")
            assert result is not None
            assert hasattr(result, "shape")

    def test_missing_vectorizer_handling(self, predictor):
        """Test handling of missing vectorizer"""
        features = {"home_id": 1}
        result = predictor._vectorize_features(features, "nonexistent")
        assert result is None


class TestSafePrediction:
    """Tests for safe prediction with fallbacks"""

    @pytest.fixture
    def predictor(self):
        return EnsemblePredictor(load_trained=True)

    def test_safe_predict_returns_valid_format(self, predictor):
        """Test that _safe_predict returns correct format"""
        features = {
            "home_id": 50,
            "away_id": 42,
            "home_league_pos": 1,
            "away_league_pos": 3,
        }

        result = predictor._safe_predict(predictor.gbdt, features, "main")

        assert "home_win" in result
        assert "draw" in result
        assert "away_win" in result
        assert isinstance(result["home_win"], float)
        assert isinstance(result["draw"], float)
        assert isinstance(result["away_win"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
