#!/usr/bin/env python3
"""
Prediction Metrics Tracker
Logs and tracks prediction accuracy, calibration, and performance metrics.
Enables data-driven model monitoring and improvement.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

METRICS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "metrics")
Path(METRICS_DIR).mkdir(parents=True, exist_ok=True)


class MetricsTracker:
    """Track prediction vs actual results for model performance analysis."""

    def __init__(self):
        self.metrics_file = os.path.join(METRICS_DIR, "predictions_log.jsonl")
        self.summary_file = os.path.join(METRICS_DIR, "summary.json")

    def log_prediction(
        self,
        fixture_id: int,
        home_team: str,
        away_team: str,
        home_pred: float,
        draw_pred: float,
        away_pred: float,
        predicted_score: str,
        model_breakdown: Optional[Dict] = None,
    ) -> None:
        """Log a prediction made by the model."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "fixture_id": fixture_id,
            "home_team": home_team,
            "away_team": away_team,
            "predictions": {
                "home_win": round(home_pred, 4),
                "draw": round(draw_pred, 4),
                "away_win": round(away_pred, 4),
            },
            "predicted_score": predicted_score,
            "model_breakdown": model_breakdown or {},
            "actual_result": None,
            "actual_score": None,
            "accuracy_metrics": None,
        }

        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"Logged prediction for fixture {fixture_id}: {record}")

    def log_actual_result(self, fixture_id: int, actual_result: str, actual_score: str) -> None:
        """Update prediction with actual match result (H/D/A)."""
        updated = False
        temp_file = self.metrics_file + ".tmp"

        with open(self.metrics_file, "r") as f_in, open(temp_file, "w") as f_out:
            for line in f_in:
                record = json.loads(line)
                if record["fixture_id"] == fixture_id:
                    record["actual_result"] = actual_result
                    record["actual_score"] = actual_score
                    record["accuracy_metrics"] = self._calculate_accuracy(
                        record["predictions"], actual_result
                    )
                    updated = True

                f_out.write(json.dumps(record) + "\n")

        if updated:
            os.replace(temp_file, self.metrics_file)
            logger.info(f"Updated fixture {fixture_id} with result {actual_result} {actual_score}")
        else:
            os.remove(temp_file)

    def _calculate_accuracy(self, predictions: Dict, actual_result: str) -> Dict:
        """Calculate accuracy metrics for a prediction."""
        predicted_winner = max(
            [
                ("home", predictions["home_win"]),
                ("draw", predictions["draw"]),
                ("away", predictions["away_win"]),
            ],
            key=lambda x: x[1],
        )[0]

        result_map = {"H": "home", "D": "draw", "A": "away"}
        actual = result_map.get(actual_result, "unknown")

        correct = predicted_winner == actual

        # Map actual result to prediction key
        pred_key_map = {"home": "home_win", "draw": "draw", "away": "away_win"}
        pred_key = pred_key_map.get(actual, "draw")
        confidence = predictions.get(pred_key, 0.0)

        return {
            "predicted_winner": predicted_winner,
            "actual_result": actual,
            "correct": correct,
            "confidence": round(confidence, 4),
            "calibration_error": abs(confidence - (1.0 if correct else 0.0)),
        }

    def get_summary_metrics(self, days: int = 7) -> Dict:
        """Calculate summary metrics for past N days."""
        cutoff = datetime.now() - timedelta(days=days)
        predictions = []
        results = []

        with open(self.metrics_file, "r") as f:
            for line in f:
                record = json.loads(line)
                ts = datetime.fromisoformat(record["timestamp"])

                if ts > cutoff and record["accuracy_metrics"]:
                    predictions.append(record)
                    results.append(record["accuracy_metrics"])

        if not results:
            return {"error": "No data for period", "days": days}

        correct = sum(1 for r in results if r["correct"])
        total = len(results)
        accuracy = correct / total if total > 0 else 0

        confidences = [r["confidence"] for r in results]
        calibration_errors = [r["calibration_error"] for r in results]

        return {
            "period_days": days,
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": round(accuracy, 4),
            "avg_confidence": round(np.mean(confidences), 4),
            "min_confidence": round(np.min(confidences), 4),
            "max_confidence": round(np.max(confidences), 4),
            "avg_calibration_error": round(np.mean(calibration_errors), 4),
            "max_calibration_error": round(np.max(calibration_errors), 4),
            "timestamp": datetime.now().isoformat(),
        }

    def get_model_comparison(self) -> Dict:
        """Compare performance of different models in ensemble."""
        model_stats = {}

        with open(self.metrics_file, "r") as f:
            for line in f:
                record = json.loads(line)
                if not record.get("model_breakdown") or not record.get("accuracy_metrics"):
                    continue

                for model_name, probs in record["model_breakdown"].items():
                    if model_name not in model_stats:
                        model_stats[model_name] = {
                            "predictions": [],
                            "accuracies": [],
                        }

                    # Handle both key formats: "home"/"draw"/"away" or "home_win"/"draw"/"away_win"
                    home_key = "home_win" if "home_win" in probs else "home"
                    away_key = "away_win" if "away_win" in probs else "away"

                    predicted = max(
                        [
                            ("home", probs.get(home_key, 0.0)),
                            ("draw", probs.get("draw", 0.0)),
                            ("away", probs.get(away_key, 0.0)),
                        ],
                        key=lambda x: x[1],
                    )[0]

                    actual = record["accuracy_metrics"]["actual_result"]
                    correct = predicted == actual

                    model_stats[model_name]["predictions"].append(
                        {
                            "predicted": predicted,
                            "actual": actual,
                            "correct": correct,
                        }
                    )
                    model_stats[model_name]["accuracies"].append(correct)

        # Calculate per-model accuracy
        result = {}
        for model_name, stats in model_stats.items():
            accuracies = stats["accuracies"]
            if accuracies:
                result[model_name] = {
                    "total": len(accuracies),
                    "correct": sum(accuracies),
                    "accuracy": round(sum(accuracies) / len(accuracies), 4),
                }

        return result

    def export_summary(self) -> None:
        """Export summary metrics to file."""
        summary = {
            "7_day": self.get_summary_metrics(7),
            "30_day": self.get_summary_metrics(30),
            "all_time": self.get_summary_metrics(365),
            "model_comparison": self.get_model_comparison(),
            "last_updated": datetime.now().isoformat(),
        }

        with open(self.summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Exported metrics summary")
        return summary


# Global instance
metrics_tracker = MetricsTracker()
