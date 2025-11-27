# FixtureCast Continuous Training Pipeline

## Overview

The continuous training pipeline keeps the ML models up-to-date with the latest match data across all supported leagues.

## Training Data Coverage

### Before Update (Nov 26, 2025)
- **6 leagues**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Championship
- **Seasons**: 2020-2024
- **Total matches**: 11,779

### After Update (Nov 27, 2025)
- **15 leagues**: All supported leagues including:
  - Top 5: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
  - Additional: Eredivisie, Primeira Liga
  - Second tier: Championship, Segunda División, Serie B, 2. Bundesliga, Ligue 2
  - European: Champions League, Europa League, Conference League
- **Seasons**: 2020-2025 ✅
- **Total matches**: 26,387 (+124%)

## How to Run

### Data Collection Only
```bash
python3 ml_engine/continuous_training.py --collect-only
```

### Model Training Only (using existing data)
```bash
python3 ml_engine/continuous_training.py --train-only
```

### Full Pipeline (Collect + Train)
```bash
python3 ml_engine/continuous_training.py
```

Or use the shell script:
```bash
./scripts/run_training.sh
```

## Scheduled Training

### Option 1: Cron Job (Linux/macOS)
Add to crontab (`crontab -e`):
```
# Run every Monday at 3 AM
0 3 * * 1 /path/to/fixturecast/scripts/run_training.sh >> /path/to/logs/training.log 2>&1
```

### Option 2: Railway Scheduled Jobs
1. Create a new Railway service from the same repo
2. Set the start command to: `python3 ml_engine/continuous_training.py`
3. Configure as a cron job in Railway settings

### Option 3: GitHub Actions
Create `.github/workflows/train.yml`:
```yaml
name: Weekly Model Training
on:
  schedule:
    - cron: '0 3 * * 1'  # Monday at 3 AM
  workflow_dispatch:  # Manual trigger

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python3 ml_engine/continuous_training.py --train-only
        env:
          API_FOOTBALL_KEY: ${{ secrets.API_FOOTBALL_KEY }}
```

## Trained Models

All 11 models are retrained:
1. **GBDT** - Gradient Boosting Decision Trees
2. **CatBoost** - Categorical Boosting
3. **Poisson** - Goal scoring distributions
4. **Transformer** - Attention-based form analysis
5. **LSTM** - Long-term trend analysis
6. **GNN** - Team relationship graphs
7. **Bayesian** - Probabilistic inference
8. **Elo** - Dynamic team ratings
9. **Monte Carlo** - Match simulation
10. **Calibration** - Probability calibration
11. **Meta-Model** - Stacked ensemble

## API Rate Limits

The data collection respects API-Football rate limits:
- 0.5s delay between API calls
- ~120 API calls per league/season combination
- Full collection (~90 league-season combos) takes ~50 seconds

## Deployment

After training, deploy the updated models:
```bash
cd fixturecast
railway up
```

The Railway deployment automatically includes:
- All trained model files in `ml_engine/trained_models/`
- Updated combined dataset in `data/historical/`
