# FixtureCast Metrics Dashboard - Implementation Guide

## Overview

The metrics dashboard provides real-time tracking of model prediction accuracy, calibration, and per-model performance. This enables continuous monitoring and data-driven model improvements.

## Architecture

### Backend Components

#### `metrics_tracker.py`
The core metrics tracking system that:
- **Logs predictions** when the ensemble makes predictions
- **Records actual results** after matches complete
- **Calculates accuracy** and calibration metrics
- **Exports summaries** for dashboard consumption

**Key Methods:**
- `log_prediction()` - Record a prediction with model breakdown
- `log_actual_result()` - Update with actual match result
- `get_summary_metrics(days)` - Get 7/30/all-time accuracy stats
- `get_model_comparison()` - Compare individual model performance
- `export_summary()` - Write metrics to `data/metrics/summary.json`

**Data Storage:**
- **JSONL log**: `data/metrics/predictions_log.jsonl` (append-only, one prediction per line)
- **JSON summary**: `data/metrics/summary.json` (regenerated on each export)

### API Endpoints

Added to `ml_api_impl.py`:

```python
# Get summary metrics (7-day, 30-day, all-time)
GET /api/metrics/summary
Response: {
  "7_day": {...accuracy, calibration...},
  "30_day": {...},
  "all_time": {...},
  "model_comparison": {
    "model_name": {"total": N, "correct": M, "accuracy": 0.XX}
  }
}

# Compare individual model performance
GET /api/metrics/model-comparison
Response: {
  "gbdt": {...stats...},
  "catboost": {...stats...},
  ...
}

# Log a prediction (call when making predictions)
POST /api/metrics/log-prediction
{
  "fixture_id": 12345,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "home_pred": 0.52,
  "draw_pred": 0.28,
  "away_pred": 0.20,
  "predicted_score": "2-1",
  "model_breakdown": {
    "gbdt": {"home": 0.51, "draw": 0.29, "away": 0.20},
    "catboost": {"home": 0.53, "draw": 0.27, "away": 0.20}
  }
}

# Log actual result (call when match finishes)
POST /api/metrics/log-result
{
  "fixture_id": 12345,
  "actual_result": "H",  # or "D" or "A"
  "actual_score": "2-1"
}
```

### Frontend Component

**`AdminMetrics.svelte`**
The admin dashboard displays:
- **7-day accuracy** card with color coding (green ≥65%, blue 55-65%, amber <55%)
- **Average confidence** with min/max range
- **Calibration error** (how well confidence matches correctness)
- **30-day accuracy** comparison
- **Individual model performance** table
- **All-time summary** statistics
- Auto-refresh every 60 seconds

Access at: `/admin/metrics` (or add link to admin nav)

## Integration Workflow

### 1. During Prediction

When `/api/predict-fixture` is called, also call `/api/metrics/log-prediction`:

```python
# In predict_fixture() or similar
prediction_data = {
    "fixture_id": fixture_id,
    "home_team": home_team,
    "away_team": away_team,
    "home_pred": home_prob,
    "draw_pred": draw_prob,
    "away_pred": away_prob,
    "predicted_score": "2-1",
    "model_breakdown": ensemble_breakdown  # Per-model probabilities
}

# Log the prediction
POST /api/metrics/log-prediction with prediction_data
```

### 2. After Match Completion

When match results are fetched/updated, call `/api/metrics/log-result`:

```python
# In update_results() or similar
result_data = {
    "fixture_id": fixture_id,
    "actual_result": "H",  # or "D" or "A"
    "actual_score": "3-2"
}

# Log the result
POST /api/metrics/log-result with result_data
```

### 3. Dashboard Access

Admin users can view metrics at: `/pages/AdminMetrics`

The dashboard automatically:
- Fetches summary from `/api/metrics/summary`
- Fetches model comparison from `/api/metrics/model-comparison`
- Refreshes every 60 seconds
- Shows 7-day, 30-day, and all-time accuracy trends

## Metrics Explained

### Accuracy
- **Definition**: Percentage of predictions where the predicted outcome matched the actual result
- **Target**: >65% indicates strong model performance
- **7-day vs 30-day**: Shows recent vs longer-term performance trends

### Confidence
- **Definition**: The predicted probability assigned to the actual outcome
- **Interpretation**: Higher confidence = model was more certain, lower = less certain
- **Use**: Identify if model is calibrated (confidence matches accuracy)

### Calibration Error
- **Definition**: |confidence - correctness|
- **Interpretation**:
  - ~0% = perfectly calibrated (confidence matches accuracy)
  - High error = miscalibrated (over/under-confident)
- **Example**: If model predicts 70% confidence but is only 40% accurate, calibration error is 30%

### Model Breakdown
- **Shows**: Individual accuracy of each model in the 11-model ensemble
- **Use**: Identify which models perform better/worse
- **Action**: Could lead to model weighting adjustments or retraining

## Testing

Run the integration test:
```bash
cd backend
python test_metrics_integration.py
```

This verifies:
- Prediction logging works
- Actual result recording works
- Accuracy calculation is correct
- Summary export generates valid JSON
- Model comparison calculation works

## Next Steps

1. **Integrate into prediction flow**: Modify prediction endpoints to call `/api/metrics/log-prediction`
2. **Integrate into result updates**: Modify result update functions to call `/api/metrics/log-result`
3. **Add to navigation**: Link AdminMetrics from main navbar for admin users
4. **Set up automated alerts**: Monitor calibration error, alert if >15%
5. **Historical data migration**: If you have historical predictions, import them with `/api/metrics/log-prediction`

## Data Structure Reference

### Prediction Log Entry (JSONL)
```json
{
  "timestamp": "2025-11-28T08:14:50.904090",
  "fixture_id": 1,
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "predictions": {
    "home_win": 0.52,
    "draw": 0.28,
    "away_win": 0.20
  },
  "predicted_score": "2-1",
  "model_breakdown": {
    "gbdt": {"home": 0.51, "draw": 0.29, "away": 0.20},
    "catboost": {"home": 0.53, "draw": 0.27, "away": 0.20}
  },
  "actual_result": "H",
  "actual_score": "2-1",
  "accuracy_metrics": {
    "predicted_winner": "home",
    "actual_result": "home",
    "correct": true,
    "confidence": 0.52,
    "calibration_error": 0.48
  }
}
```

### Summary Export (JSON)
```json
{
  "7_day": {
    "period_days": 7,
    "total_predictions": 150,
    "correct_predictions": 98,
    "accuracy": 0.653,
    "avg_confidence": 0.62,
    "min_confidence": 0.33,
    "max_confidence": 0.89,
    "avg_calibration_error": 0.085,
    "max_calibration_error": 0.45,
    "timestamp": "2025-11-28T08:14:50.904090"
  },
  ...
  "model_comparison": {
    "gbdt": {
      "total": 150,
      "correct": 101,
      "accuracy": 0.673
    },
    ...
  }
}
```
