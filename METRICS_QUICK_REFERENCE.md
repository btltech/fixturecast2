# Metrics Dashboard - Quick Reference

## Accessing the Dashboard
- **URL**: `http://localhost:5173/admin/metrics` (or production URL)
- **Admin Only**: Should be restricted to admin users
- **Auto-refresh**: Updates every 60 seconds automatically

## What You See

### Accuracy Cards (7-Day)
- **Green (≥65%)**: Strong model performance ✅
- **Blue (55-65%)**: Acceptable performance ⚠️
- **Amber (<55%)**: Below target performance ❌
- Shows: Number correct / Total predictions

### Confidence & Calibration
- **Average Confidence**: How certain the model was on average
- **Confidence Range**: Min and max confidence values seen
- **Calibration Error**: How well-calibrated the model is
  - ~0%: Perfectly calibrated (confidence matches correctness)
  - High value: Model is over/under-confident

### 30-Day Comparison
- Longer-term accuracy trend
- Total predictions in 30-day window
- Calibration error over longer period

### Model Comparison Table
- Shows accuracy for each of the 11 models:
  - GBDT, CatBoost, Poisson, Transformer, LSTM, GNN
  - Bayesian, Elo, Monte Carlo, Calibration, Meta-Model
- Predictions: Total predictions made by that model
- Correct: Number of correct predictions
- Accuracy: Model-specific accuracy percentage

## API Integration Points

### When Making Predictions
```bash
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
```

### When Match Completes
```bash
POST /api/metrics/log-result
{
  "fixture_id": 12345,
  "actual_result": "H",  # H = Home win, D = Draw, A = Away win
  "actual_score": "2-1"
}
```

## Troubleshooting

### Dashboard Shows "No data available yet"
- Metrics are newly initialized
- First predictions need to be logged with `/api/metrics/log-prediction`
- Then matches need to complete and results logged with `/api/metrics/log-result`
- Dashboard will populate after first metrics are recorded

### Calibration Error Too High
- Model is not well-calibrated (over/under-confident)
- Solution: Adjust model confidence scaling or recalibrate with temperature scaling
- Monitor: If >15%, consider model retraining

### Accuracy Trending Down
- Check if model needs retraining
- Compare against baseline to identify drift
- Use model comparison table to find which models are degrading
- Consider triggering retraining if <55% for 7 days

## Data Location

- **JSONL Log**: `/data/metrics/predictions_log.jsonl`
- **Summary JSON**: `/data/metrics/summary.json`
- **API Base**: `{BACKEND_API_URL}/api/metrics/*`

## Testing

Run integration test:
```bash
cd backend
python test_metrics_integration.py
```

Expected output: ✅ All tests passing

## Documentation

- **Full Guide**: `METRICS_IMPLEMENTATION.md`
- **Implementation Details**: `METRICS_DASHBOARD_COMPLETE.md`
- **API Reference**: See `ml_api_impl.py` endpoints (lines ~1660+)

## Next Steps

1. ✅ Metrics system installed and tested
2. ⏳ Integrate prediction logging into `/api/predict-fixture`
3. ⏳ Integrate result logging into result update functions
4. ⏳ Add AdminMetrics link to navigation
5. ⏳ Monitor metrics for first week
6. ⏳ Adjust thresholds based on actual performance
