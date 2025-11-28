# Automated Weekly Training Pipeline

## Overview

FixtureCast uses GitHub Actions to automatically retrain ML models weekly. This ensures models stay current with the latest match data and continuously improve prediction accuracy.

## How It Works

### Schedule
- **Default**: Every Monday at 3 AM UTC
- **Manual**: Can be triggered anytime via GitHub Actions UI
- **Customizable**: Edit cron expression in `.github/workflows/train-models.yml`

### Pipeline Steps

```
1. Checkout repository (latest code + models)
   ↓
2. Set up Python 3.12 environment
   ↓
3. Install dependencies from requirements.txt
   ↓
4. Run training with existing data (--no-collect flag)
   ↓
5. Check if models changed
   ↓
6. If changed: Commit & push to main branch
   ↓
7. Railway auto-deploys on git push (if configured)
   ↓
8. Send Discord notification on failure
```

## Configuration

### GitHub Secrets Required

Add these secrets to your GitHub repository settings:

**Optional (for notifications):**
- `DISCORD_WEBHOOK_URL` - Discord webhook for failure notifications
- `RAILWAY_TOKEN` - Railway API token (if not auto-watching branch)

### Scheduled Training

Edit `.github/workflows/train-models.yml` to change schedule:

```yaml
on:
  schedule:
    - cron: "0 3 * * 1"  # Cron format: minute hour day month day-of-week
```

Examples:
- `0 3 * * 1` - Every Monday 3 AM UTC
- `0 3 * * *` - Every day 3 AM UTC
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Every Sunday midnight UTC

### Manual Trigger

1. Go to GitHub repo → Actions tab
2. Select "Automated Weekly Training" workflow
3. Click "Run workflow" button
4. Select branch (main)
5. Click "Run workflow"

## What Gets Trained

The pipeline retrains all 11 models in the ensemble:

1. **GBDT** - Gradient Boosting Decision Trees
2. **CatBoost** - Categorical Boosting
3. **Poisson** - Poisson Regression for goals
4. **Transformer** - Transformer-based architecture
5. **LSTM** - Long Short-Term Memory networks
6. **GNN** - Graph Neural Networks
7. **Bayesian** - Bayesian inference model
8. **Elo** - Elo rating-based model
9. **Monte Carlo** - Monte Carlo simulation
10. **Calibration** - Output calibration layer
11. **Meta-Model** - Ensemble meta-learner

## Training Details

### Data Source
- **No fresh data collection** (uses --no-collect flag for speed)
- Uses historical data already in `/data/historical/`
- Can be modified to collect fresh data if needed

### Training Duration
- Typical: 5-15 minutes per training run
- Max timeout: 120 minutes (safety limit)
- Runs on Ubuntu with 2 CPU cores

### Model Storage
- Trained models saved to `ml_engine/trained_models/`
- Only committed if models actually changed
- Keeps git history clean

## Deployment

### Automatic Deployment
If Railway is configured to watch the `main` branch:
1. Models committed to GitHub
2. Railway auto-triggers deployment
3. New models live within minutes

### Manual Deployment
```bash
# Push to trigger Railway deployment
git push origin main
```

## Monitoring

### Check Training Status
1. Go to GitHub repo → Actions tab
2. Look for "Automated Weekly Training" workflow runs
3. Click run to see detailed logs

### Training Logs Include
- Data collection (if enabled)
- Model training progress
- Model performance metrics
- Commit hash and timestamp
- Success/failure status

### Discord Notifications
If `DISCORD_WEBHOOK_URL` is set:
- Failure notifications sent automatically
- Includes run link and error details
- Success is logged in GitHub Actions

## Troubleshooting

### Training Times Out
- Check if model files are too large
- Reduce training data or use --no-collect flag
- Increase timeout limit in workflow YAML

### Models Not Committing
- Check if models actually changed
- Verify git user configuration
- Check repository permissions

### Deployment Not Triggering
- Verify Railway is watching the `main` branch
- Check Railway webhook configuration
- Manually trigger deployment if needed

### Dependencies Missing
- Update `requirements.txt` in root directory
- GitHub Actions rebuilds cache on requirements change
- Pip install failures will show in logs

## Manual Training

Run training locally:

```bash
# Using continuous_training script
cd ml_engine
python continuous_training.py --no-collect --train

# Or using workflow script
python scripts/train_workflow.py
```

## Workflow File Reference

**Location**: `.github/workflows/train-models.yml`

**Key Sections:**
- `schedule` - Cron timing
- `on.workflow_dispatch` - Manual trigger
- `train.steps` - Workflow steps
- `env` - Environment variables
- `secrets` - GitHub secrets

## Best Practices

✅ **Do:**
- Run training on a regular schedule (weekly recommended)
- Monitor workflow runs for errors
- Keep requirements.txt updated
- Review model performance in metrics dashboard
- Test model updates before production deployment

❌ **Don't:**
- Run training too frequently (wastes resources)
- Commit models if they haven't changed
- Push large training datasets
- Hard-code API keys in workflow

## Next Steps

1. ✅ Add Discord webhook for notifications
2. ✅ Verify Railway auto-deployment is configured
3. ✅ Run first manual training test
4. ✅ Monitor metrics dashboard for model improvements
5. ⏳ Consider A/B testing framework (Priority #3)

## Related Documentation

- [Metrics Dashboard](METRICS_IMPLEMENTATION.md)
- [Continuous Training Script](ml_engine/continuous_training.py)
- [Model Training Guide](ml_engine/README.md)
