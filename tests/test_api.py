#!/usr/bin/env python3
"""
Unit tests for FastAPI endpoints.
Tests API routes, response formats, and error handling.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from ml_api_impl import app

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestModelEndpoints:
    """Tests for model-related endpoints"""

    @pytest.fixture
    def client(self):
        from ml_api_impl import app

        return TestClient(app)

    def test_models_info_endpoint(self, client):
        """Test models info endpoint"""
        response = client.get("/models/info")
        assert response.status_code == 200
        data = response.json()
        assert "base_models" in data
        assert "ensemble_weights" in data

    def test_model_stats_endpoint(self, client):
        """Test model stats endpoint"""
        response = client.get("/api/model-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_predictions" in data
        assert "models" in data


class TestPredictionEndpoints:
    """Tests for prediction endpoints"""

    @pytest.fixture
    def client(self):
        from ml_api_impl import app

        return TestClient(app)

    def test_predict_endpoint_with_valid_features(self, client):
        """Test prediction with valid features"""
        features = {
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
        }

        response = client.post("/predict", json=features)
        assert response.status_code == 200
        data = response.json()
        assert "home_win_prob" in data
        assert "draw_prob" in data
        assert "away_win_prob" in data
        assert "predicted_scoreline" in data

    def test_predict_endpoint_with_minimal_features(self, client):
        """Test prediction with minimal required features"""
        features = {
            "home_id": 1,
            "away_id": 2,
            "home_name": "Team A",
            "away_name": "Team B",
        }

        response = client.post("/predict", json=features)
        # Should work with defaults
        assert response.status_code == 200


class TestBackendAPI:
    """Tests for backend API endpoints"""

    @pytest.fixture
    def client(self):
        from backend_api import app

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "FixtureCast Backend API"


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.fixture
    def client(self):
        from ml_api_impl import app

        return TestClient(app)

    def test_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            "/predict", content="not valid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Validation error

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields"""
        response = client.post("/predict", json={})
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
