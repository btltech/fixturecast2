"""
Metrics API endpoints for FixtureCast Performance Monitoring.
Provides endpoints for logging predictions, recording results, and fetching analytics.
"""

from datetime import datetime
from typing import Dict, List, Optional

from database import PredictionDB
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# Request/Response Models
class PredictionLog(BaseModel):
    fixture_id: int
    home_team: str
    away_team: str
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    league_id: int
    league_name: Optional[str] = None
    match_date: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_scoreline: Optional[str] = None
    btts_prob: Optional[float] = None
    over25_prob: Optional[float] = None
    model_breakdown: Optional[Dict] = None


class ResultRecord(BaseModel):
    fixture_id: int
    home_goals: int
    away_goals: int
    status: str = "FT"


class BulkResultRecord(BaseModel):
    results: List[ResultRecord]


# Endpoints
@router.post("/log-prediction")
async def log_prediction(prediction: PredictionLog):
    """Log a new prediction to the database."""
    success = PredictionDB.log_prediction(
        fixture_id=prediction.fixture_id,
        home_team=prediction.home_team,
        away_team=prediction.away_team,
        home_team_id=prediction.home_team_id,
        away_team_id=prediction.away_team_id,
        league_id=prediction.league_id,
        league_name=prediction.league_name,
        match_date=prediction.match_date,
        prediction={
            "home_win_prob": prediction.home_win_prob,
            "draw_prob": prediction.draw_prob,
            "away_win_prob": prediction.away_win_prob,
            "predicted_scoreline": prediction.predicted_scoreline,
            "btts_prob": prediction.btts_prob,
            "over25_prob": prediction.over25_prob,
        },
        model_breakdown=prediction.model_breakdown,
    )

    if success:
        return {
            "status": "success",
            "message": "Prediction logged",
            "fixture_id": prediction.fixture_id,
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to log prediction")


@router.post("/record-result")
async def record_result(result: ResultRecord):
    """Record match result and evaluate the prediction."""
    evaluation = PredictionDB.record_result(
        fixture_id=result.fixture_id,
        home_goals=result.home_goals,
        away_goals=result.away_goals,
        status=result.status,
    )

    if evaluation:
        return {"status": "success", "evaluation": evaluation}
    else:
        return {
            "status": "not_found",
            "message": f"No prediction found for fixture {result.fixture_id}",
        }


@router.post("/record-results-bulk")
async def record_results_bulk(bulk: BulkResultRecord):
    """Record multiple match results at once."""
    results = []
    for r in bulk.results:
        evaluation = PredictionDB.record_result(
            fixture_id=r.fixture_id,
            home_goals=r.home_goals,
            away_goals=r.away_goals,
            status=r.status,
        )
        results.append({"fixture_id": r.fixture_id, "evaluation": evaluation})

    success_count = sum(1 for r in results if r["evaluation"])
    return {
        "status": "success",
        "processed": len(results),
        "evaluated": success_count,
        "results": results,
    }


@router.get("/pending")
async def get_pending_results():
    """Get predictions that haven't been evaluated yet."""
    pending = PredictionDB.get_pending_results()
    return {"count": len(pending), "predictions": pending}


@router.get("/summary")
async def get_metrics_summary(days: int = Query(7, description="Number of days to look back")):
    """Get performance metrics summary."""
    # Get period-specific metrics
    period_metrics = PredictionDB.get_metrics_summary(days)

    # Also get 30-day and all-time for comparison
    thirty_day = PredictionDB.get_metrics_summary(30)
    all_time = PredictionDB.get_all_time_stats()

    return {
        f"{days}_day": period_metrics,
        "30_day": {
            "total_predictions": thirty_day.get("total_predictions", 0),
            "correct_predictions": thirty_day.get("correct_predictions", 0),
            "accuracy": thirty_day.get("accuracy", 0),
            "avg_confidence": thirty_day.get("avg_confidence", 0),
        },
        "all_time": all_time,
        "model_comparison": period_metrics.get("model_comparison", {}),
        "by_confidence": period_metrics.get("by_confidence", {}),
        "by_league": period_metrics.get("by_league", {}),
        "last_updated": datetime.now().isoformat(),
    }


@router.get("/daily-trend")
async def get_daily_trend(days: int = Query(30, description="Number of days of history")):
    """Get daily accuracy trend for charts."""
    trend = PredictionDB.get_daily_trend(days)
    return {"days": days, "trend": trend}


@router.get("/recent")
async def get_recent_predictions(
    limit: int = Query(50, description="Number of predictions to return")
):
    """Get recent predictions with evaluations."""
    predictions = PredictionDB.get_recent_predictions(limit)
    return {"count": len(predictions), "predictions": predictions}


@router.get("/history")
async def get_prediction_history(
    limit: int = Query(50, description="Number of predictions to return")
):
    """Get prediction history with status for live dashboard."""
    predictions = PredictionDB.get_recent_predictions(limit)

    # Transform for frontend consumption
    formatted = []
    for p in predictions:
        # Determine predicted result string
        pred_outcome = p.get("predicted_outcome", "")
        if pred_outcome == "home":
            predicted_result = f"{p['home_team']} Win"
        elif pred_outcome == "away":
            predicted_result = f"{p['away_team']} Win"
        else:
            predicted_result = "Draw"

        # Determine actual result string
        actual_result = None
        if p.get("actual_outcome"):
            if p["actual_outcome"] == "home":
                actual_result = f"{p['home_team']} Win"
            elif p["actual_outcome"] == "away":
                actual_result = f"{p['away_team']} Win"
            else:
                actual_result = "Draw"

        formatted.append(
            {
                "fixture_id": p["fixture_id"],
                "home_team": p["home_team"],
                "away_team": p["away_team"],
                "league_name": p.get("league_name"),
                "match_date": p.get("match_date"),
                "predicted_result": predicted_result,
                "predicted_scoreline": p.get("predicted_scoreline"),
                "confidence": p.get("confidence", 0),
                "actual_result": actual_result,
                "actual_score": (
                    f"{p['result_home_goals']}-{p['result_away_goals']}"
                    if p.get("result_home_goals") is not None
                    else None
                ),
                "is_correct": bool(p.get("outcome_correct")),
                "evaluated": bool(p.get("evaluated")),
                "created_at": p.get("match_date"),
            }
        )

    return {"count": len(formatted), "predictions": formatted}


@router.get("/model-performance")
async def get_model_performance(days: int = Query(30, description="Number of days to look back")):
    """Get detailed model-by-model performance."""
    metrics = PredictionDB.get_metrics_summary(days)
    model_data = metrics.get("model_comparison", {})

    # Calculate relative performance
    if model_data:
        avg_accuracy = sum(m["accuracy"] for m in model_data.values()) / len(model_data)
        for model in model_data.values():
            model["relative_performance"] = model["accuracy"] - avg_accuracy

    return {
        "period_days": days,
        "models": model_data,
        "best_model": (
            max(model_data.items(), key=lambda x: x[1]["accuracy"])[0] if model_data else None
        ),
        "worst_model": (
            min(model_data.items(), key=lambda x: x[1]["accuracy"])[0] if model_data else None
        ),
    }


@router.get("/league-performance")
async def get_league_performance(days: int = Query(30, description="Number of days to look back")):
    """Get performance by league."""
    metrics = PredictionDB.get_metrics_summary(days)
    return {"period_days": days, "leagues": metrics.get("by_league", {})}


@router.get("/calibration")
async def get_calibration_data(days: int = Query(30, description="Number of days to look back")):
    """Get calibration data for reliability diagrams."""
    # This would need more complex query to bin by confidence
    # For now, return confidence level breakdown
    metrics = PredictionDB.get_metrics_summary(days)
    by_conf = metrics.get("by_confidence", {})

    calibration = []
    for level, data in by_conf.items():
        if data["total"] > 0:
            # Map confidence levels to approximate confidence ranges
            conf_ranges = {
                "high": {"min": 0.65, "max": 1.0, "expected": 0.75},
                "medium": {"min": 0.45, "max": 0.65, "expected": 0.55},
                "low": {"min": 0.33, "max": 0.45, "expected": 0.40},
            }
            range_data = conf_ranges.get(level, {"expected": 0.5})

            calibration.append(
                {
                    "confidence_level": level,
                    "expected_accuracy": range_data["expected"],
                    "actual_accuracy": data["accuracy"],
                    "calibration_error": abs(range_data["expected"] - data["accuracy"]),
                    "sample_size": data["total"],
                }
            )

    return {
        "period_days": days,
        "calibration": calibration,
        "avg_calibration_error": (
            sum(c["calibration_error"] for c in calibration) / len(calibration)
            if calibration
            else 0
        ),
    }


@router.get("/health")
async def metrics_health():
    """Health check for metrics system."""
    try:
        all_time = PredictionDB.get_all_time_stats()
        pending = PredictionDB.get_pending_results()

        return {
            "status": "healthy",
            "total_predictions_tracked": all_time.get("total_predictions", 0),
            "pending_evaluations": len(pending),
            "database": "connected",
            "last_check": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "last_check": datetime.now().isoformat()}
