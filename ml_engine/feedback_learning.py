"""
Feedback Learning System
========================
Tracks predictions vs actual results and enables model improvement through:
1. Recording predictions before matches
2. Capturing actual results after matches
3. Analyzing prediction accuracy over time
4. Retraining models with new data
5. Adjusting model weights based on performance
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# Path to store feedback data
FEEDBACK_DIR = os.path.join(os.path.dirname(__file__), "trained_models", "feedback")
PREDICTIONS_FILE = os.path.join(FEEDBACK_DIR, "predictions_log.json")
RESULTS_FILE = os.path.join(FEEDBACK_DIR, "results_log.json")
MODEL_PERFORMANCE_FILE = os.path.join(FEEDBACK_DIR, "model_performance.json")

# Ensure feedback directory exists
os.makedirs(FEEDBACK_DIR, exist_ok=True)


class FeedbackLearningSystem:
    """
    Tracks predictions vs actual results to improve models over time.
    """

    def __init__(self):
        self.predictions_log = self._load_json(PREDICTIONS_FILE, default=[])
        self.results_log = self._load_json(RESULTS_FILE, default=[])
        self.model_performance = self._load_json(
            MODEL_PERFORMANCE_FILE,
            default={
                "overall": {"correct": 0, "total": 0, "accuracy": 0.0},
                "by_model": {},
                "by_confidence": {
                    "high": {"correct": 0, "total": 0},
                    "medium": {"correct": 0, "total": 0},
                    "low": {"correct": 0, "total": 0},
                },
                "by_league": {},
                "recent_trend": [],  # Last 50 predictions
                "calibration": {"bins": {}, "samples": 0},
            },
        )

    def _load_json(self, filepath: str, default=None):
        """Load JSON file or return default"""
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
        return default if default is not None else {}

    def _save_json(self, filepath: str, data):
        """Save data to JSON file"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")

    def log_prediction(
        self,
        fixture_id: int,
        home_team: str,
        away_team: str,
        league_id: int,
        league_name: str,
        match_date: str,
        prediction: Dict,
        model_breakdown: Dict = None,
    ) -> Dict:
        """
        Log a prediction before a match starts.

        Args:
            fixture_id: Unique fixture identifier
            home_team: Home team name
            away_team: Away team name
            league_id: League identifier
            league_name: League name
            match_date: Match date/time
            prediction: Full prediction dict with probabilities
            model_breakdown: Individual model predictions

        Returns:
            Logged prediction entry
        """
        # Determine predicted outcome
        home_prob = prediction.get("home_win_prob", 0)
        draw_prob = prediction.get("draw_prob", 0)
        away_prob = prediction.get("away_win_prob", 0)

        if home_prob >= draw_prob and home_prob >= away_prob:
            predicted_outcome = "home"
        elif away_prob >= draw_prob:
            predicted_outcome = "away"
        else:
            predicted_outcome = "draw"

        # Calculate confidence level
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob >= 0.65:
            confidence_level = "high"
        elif max_prob >= 0.45:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        entry = {
            "fixture_id": fixture_id,
            "home_team": home_team,
            "away_team": away_team,
            "league_id": league_id,
            "league_name": league_name,
            "match_date": match_date,
            "logged_at": datetime.now().isoformat(),
            "prediction": {
                "home_win_prob": home_prob,
                "draw_prob": draw_prob,
                "away_win_prob": away_prob,
                "predicted_outcome": predicted_outcome,
                "confidence": max_prob,
                "confidence_level": confidence_level,
                "predicted_scoreline": prediction.get("predicted_scoreline"),
                "btts_prob": prediction.get("btts_prob"),
                "over25_prob": prediction.get("over25_prob"),
            },
            "model_breakdown": model_breakdown or {},
            "result": None,  # To be filled after match
            "evaluated": False,
        }

        # Check if prediction already exists for this fixture
        existing_idx = next(
            (i for i, p in enumerate(self.predictions_log) if p["fixture_id"] == fixture_id), None
        )

        if existing_idx is not None:
            # Update existing prediction
            self.predictions_log[existing_idx] = entry
        else:
            self.predictions_log.append(entry)

        self._save_json(PREDICTIONS_FILE, self.predictions_log)

        return entry

    def record_result(
        self, fixture_id: int, home_goals: int, away_goals: int, status: str = "FT"
    ) -> Optional[Dict]:
        """
        Record the actual result of a match and evaluate prediction.

        Args:
            fixture_id: Unique fixture identifier
            home_goals: Goals scored by home team
            away_goals: Goals scored by away team
            status: Match status (FT = Full Time)

        Returns:
            Evaluation result or None if prediction not found
        """
        # Find the prediction for this fixture
        pred_entry = next((p for p in self.predictions_log if p["fixture_id"] == fixture_id), None)

        if pred_entry is None:
            print(f"No prediction found for fixture {fixture_id}")
            return None

        if pred_entry.get("evaluated"):
            print(f"Fixture {fixture_id} already evaluated")
            return pred_entry.get("evaluation")

        # Determine actual outcome
        if home_goals > away_goals:
            actual_outcome = "home"
        elif away_goals > home_goals:
            actual_outcome = "away"
        else:
            actual_outcome = "draw"

        # Calculate if prediction was correct
        predicted_outcome = pred_entry["prediction"]["predicted_outcome"]
        is_correct = predicted_outcome == actual_outcome

        # Calculate Brier score for this prediction
        actual_probs = {"home": 0, "draw": 0, "away": 0}
        actual_probs[actual_outcome] = 1

        brier_score = (
            (pred_entry["prediction"]["home_win_prob"] - actual_probs["home"]) ** 2
            + (pred_entry["prediction"]["draw_prob"] - actual_probs["draw"]) ** 2
            + (pred_entry["prediction"]["away_win_prob"] - actual_probs["away"]) ** 2
        ) / 3

        # Check secondary predictions
        btts_actual = home_goals > 0 and away_goals > 0
        btts_correct = (pred_entry["prediction"].get("btts_prob", 0.5) >= 0.5) == btts_actual

        over25_actual = (home_goals + away_goals) > 2.5
        over25_correct = (pred_entry["prediction"].get("over25_prob", 0.5) >= 0.5) == over25_actual

        # Score prediction accuracy
        predicted_score = pred_entry["prediction"].get("predicted_scoreline", "0-0")
        try:
            pred_home, pred_away = map(int, predicted_score.split("-"))
            exact_score = pred_home == home_goals and pred_away == away_goals
            score_diff = abs(pred_home - home_goals) + abs(pred_away - away_goals)
        except (ValueError, AttributeError):
            exact_score = False
            score_diff = 99

        # Store result
        result = {
            "home_goals": home_goals,
            "away_goals": away_goals,
            "actual_outcome": actual_outcome,
            "status": status,
            "recorded_at": datetime.now().isoformat(),
        }

        evaluation = {
            "outcome_correct": is_correct,
            "brier_score": brier_score,
            "btts_correct": btts_correct,
            "over25_correct": over25_correct,
            "exact_score": exact_score,
            "score_diff": score_diff,
            "confidence_level": pred_entry["prediction"]["confidence_level"],
            "confidence": pred_entry["prediction"]["confidence"],
        }

        # Update the prediction entry
        pred_entry["result"] = result
        pred_entry["evaluation"] = evaluation
        pred_entry["evaluated"] = True

        # Also log the result separately
        self.results_log.append(
            {
                "fixture_id": fixture_id,
                "result": result,
                "evaluation": evaluation,
                "recorded_at": datetime.now().isoformat(),
            }
        )

        # Update model performance stats
        self._update_performance_stats(pred_entry, evaluation)

        # Save all updates
        self._save_json(PREDICTIONS_FILE, self.predictions_log)
        self._save_json(RESULTS_FILE, self.results_log)
        self._save_json(MODEL_PERFORMANCE_FILE, self.model_performance)

        return evaluation

    def _update_performance_stats(self, pred_entry: Dict, evaluation: Dict):
        """Update cumulative performance statistics"""
        perf = self.model_performance

        # Overall stats
        perf["overall"]["total"] += 1
        if evaluation["outcome_correct"]:
            perf["overall"]["correct"] += 1
        perf["overall"]["accuracy"] = perf["overall"]["correct"] / perf["overall"]["total"]

        # By confidence level
        conf_level = evaluation["confidence_level"]
        perf["by_confidence"][conf_level]["total"] += 1
        if evaluation["outcome_correct"]:
            perf["by_confidence"][conf_level]["correct"] += 1

        # By league
        league_id = str(pred_entry["league_id"])
        if league_id not in perf["by_league"]:
            perf["by_league"][league_id] = {
                "name": pred_entry["league_name"],
                "correct": 0,
                "total": 0,
                "brier_sum": 0,
            }
        perf["by_league"][league_id]["total"] += 1
        perf["by_league"][league_id]["brier_sum"] += evaluation["brier_score"]
        if evaluation["outcome_correct"]:
            perf["by_league"][league_id]["correct"] += 1

        # By individual model (if breakdown available)
        if pred_entry.get("model_breakdown"):
            for model_name, model_pred in pred_entry["model_breakdown"].items():
                if model_name not in perf["by_model"]:
                    perf["by_model"][model_name] = {"correct": 0, "total": 0}

                # Determine what this model predicted
                model_home = model_pred.get("home_win", 0)
                model_draw = model_pred.get("draw", 0)
                model_away = model_pred.get("away_win", 0)

                if model_home >= model_draw and model_home >= model_away:
                    model_predicted = "home"
                elif model_away >= model_draw:
                    model_predicted = "away"
                else:
                    model_predicted = "draw"

                perf["by_model"][model_name]["total"] += 1
                if model_predicted == pred_entry["result"]["actual_outcome"]:
                    perf["by_model"][model_name]["correct"] += 1

        # Recent trend (keep last 50)
        perf["recent_trend"].append(
            {
                "fixture_id": pred_entry["fixture_id"],
                "correct": evaluation["outcome_correct"],
                "confidence": evaluation["confidence"],
                "brier": evaluation["brier_score"],
                "date": pred_entry["match_date"],
            }
        )
        if len(perf["recent_trend"]) > 50:
            perf["recent_trend"] = perf["recent_trend"][-50:]

        # Calibration bins (group by predicted probability)
        conf = evaluation["confidence"]
        bin_key = f"{int(conf * 10) * 10}-{int(conf * 10) * 10 + 10}"
        if bin_key not in perf["calibration"]["bins"]:
            perf["calibration"]["bins"][bin_key] = {"predicted_sum": 0, "actual_sum": 0, "count": 0}
        perf["calibration"]["bins"][bin_key]["predicted_sum"] += conf
        perf["calibration"]["bins"][bin_key]["actual_sum"] += (
            1 if evaluation["outcome_correct"] else 0
        )
        perf["calibration"]["bins"][bin_key]["count"] += 1
        perf["calibration"]["samples"] += 1

    def get_performance_report(self) -> Dict:
        """Get a comprehensive performance report"""
        perf = self.model_performance

        # Calculate derived metrics
        report = {
            "overall": {
                **perf["overall"],
                "total_predictions": perf["overall"]["total"],
                "accuracy_pct": f"{perf['overall']['accuracy'] * 100:.1f}%",
            },
            "by_confidence": {},
            "by_league": {},
            "by_model": {},
            "recent_form": {},
            "calibration": {},
        }

        # Confidence breakdown
        for level, stats in perf["by_confidence"].items():
            if stats["total"] > 0:
                report["by_confidence"][level] = {
                    **stats,
                    "accuracy": stats["correct"] / stats["total"],
                    "accuracy_pct": f"{stats['correct'] / stats['total'] * 100:.1f}%",
                }

        # League breakdown
        for league_id, stats in perf["by_league"].items():
            if stats["total"] > 0:
                report["by_league"][league_id] = {
                    **stats,
                    "accuracy": stats["correct"] / stats["total"],
                    "avg_brier": stats["brier_sum"] / stats["total"],
                }

        # Model breakdown
        for model_name, stats in perf["by_model"].items():
            if stats["total"] > 0:
                report["by_model"][model_name] = {
                    **stats,
                    "accuracy": stats["correct"] / stats["total"],
                    "accuracy_pct": f"{stats['correct'] / stats['total'] * 100:.1f}%",
                }

        # Recent form (last 10, 20, 50)
        recent = perf["recent_trend"]
        for n in [10, 20, 50]:
            last_n = recent[-n:] if len(recent) >= n else recent
            if last_n:
                correct = sum(1 for r in last_n if r["correct"])
                report["recent_form"][f"last_{n}"] = {
                    "correct": correct,
                    "total": len(last_n),
                    "accuracy": correct / len(last_n) if last_n else 0,
                }

        # Calibration analysis
        for bin_key, stats in perf["calibration"]["bins"].items():
            if stats["count"] > 0:
                avg_predicted = stats["predicted_sum"] / stats["count"]
                avg_actual = stats["actual_sum"] / stats["count"]
                report["calibration"][bin_key] = {
                    "avg_predicted": avg_predicted,
                    "avg_actual": avg_actual,
                    "calibration_error": abs(avg_predicted - avg_actual),
                    "count": stats["count"],
                }

        return report

    def get_recommended_weight_adjustments(self) -> Dict[str, float]:
        """
        Based on individual model performance, recommend weight adjustments.
        Models that perform better get higher weights.
        """
        perf = self.model_performance
        model_stats = perf.get("by_model", {})

        if not model_stats:
            return {}

        # Calculate accuracy for each model
        accuracies = {}
        for model_name, stats in model_stats.items():
            if stats["total"] >= 10:  # Need at least 10 samples
                accuracies[model_name] = stats["correct"] / stats["total"]

        if not accuracies:
            return {}

        # Normalize to sum to 1.0
        total_acc = sum(accuracies.values())
        if total_acc == 0:
            return {}

        recommended_weights = {model: acc / total_acc for model, acc in accuracies.items()}

        return recommended_weights

    def get_pending_results(self) -> List[Dict]:
        """Get predictions that haven't been evaluated yet"""
        return [p for p in self.predictions_log if not p.get("evaluated")]

    def export_training_data(self) -> List[Dict]:
        """
        Export evaluated predictions as training data for model retraining.
        Returns data in a format suitable for supervised learning.
        """
        training_data = []

        for pred in self.predictions_log:
            if pred.get("evaluated") and pred.get("result"):
                # Convert to training format
                training_data.append(
                    {
                        "fixture_id": pred["fixture_id"],
                        "home_team": pred["home_team"],
                        "away_team": pred["away_team"],
                        "league_id": pred["league_id"],
                        # Features (what we predicted)
                        "home_win_prob": pred["prediction"]["home_win_prob"],
                        "draw_prob": pred["prediction"]["draw_prob"],
                        "away_win_prob": pred["prediction"]["away_win_prob"],
                        # Target (what actually happened)
                        "actual_outcome": pred["result"]["actual_outcome"],
                        "home_goals": pred["result"]["home_goals"],
                        "away_goals": pred["result"]["away_goals"],
                        # For analysis
                        "was_correct": pred["evaluation"]["outcome_correct"],
                        "brier_score": pred["evaluation"]["brier_score"],
                    }
                )

        return training_data


# Global instance
feedback_system = FeedbackLearningSystem()


def log_prediction(
    fixture_id: int,
    home_team: str,
    away_team: str,
    league_id: int,
    league_name: str,
    match_date: str,
    prediction: Dict,
    model_breakdown: Dict = None,
) -> Dict:
    """Convenience function to log a prediction"""
    return feedback_system.log_prediction(
        fixture_id,
        home_team,
        away_team,
        league_id,
        league_name,
        match_date,
        prediction,
        model_breakdown,
    )


def record_result(
    fixture_id: int, home_goals: int, away_goals: int, status: str = "FT"
) -> Optional[Dict]:
    """Convenience function to record a result"""
    return feedback_system.record_result(fixture_id, home_goals, away_goals, status)


def get_performance_report() -> Dict:
    """Convenience function to get performance report"""
    return feedback_system.get_performance_report()


def get_recommended_weights() -> Dict[str, float]:
    """Convenience function to get recommended model weights"""
    return feedback_system.get_recommended_weight_adjustments()


if __name__ == "__main__":
    # Demo usage
    print("Feedback Learning System")
    print("=" * 50)

    # Example: Log a prediction
    sample_prediction = {
        "home_win_prob": 0.65,
        "draw_prob": 0.20,
        "away_win_prob": 0.15,
        "predicted_scoreline": "2-1",
        "btts_prob": 0.55,
        "over25_prob": 0.60,
    }

    sample_breakdown = {
        "gbdt": {"home_win": 0.60, "draw": 0.22, "away_win": 0.18},
        "elo": {"home_win": 0.70, "draw": 0.18, "away_win": 0.12},
        "gnn": {"home_win": 0.65, "draw": 0.20, "away_win": 0.15},
    }

    # Log it
    logged = log_prediction(
        fixture_id=999999,
        home_team="Test Home",
        away_team="Test Away",
        league_id=39,
        league_name="Premier League",
        match_date="2025-12-01T15:00:00",
        prediction=sample_prediction,
        model_breakdown=sample_breakdown,
    )
    print(
        f"Logged prediction: {logged['prediction']['predicted_outcome']} "
        f"({logged['prediction']['confidence']:.1%} confidence)"
    )

    # Simulate recording a result
    # eval_result = record_result(999999, home_goals=2, away_goals=0)
    # print(f"Evaluation: Correct={eval_result['outcome_correct']}, Brier={eval_result['brier_score']:.3f}")

    # Show current performance
    report = get_performance_report()
    print(f"\nOverall Performance: {report['overall']}")

    # Show pending predictions
    pending = feedback_system.get_pending_results()
    print(f"\nPending evaluations: {len(pending)} predictions")
