# GitHub Actions Setup for FixtureCast

This guide explains how to configure GitHub Actions for automated bot deployments and health monitoring.

## Required GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

### Railway Secrets

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `RAILWAY_TOKEN` | Railway API token | Run `railway whoami` after login, or get from Railway dashboard → Account Settings → Tokens |
| `RAILWAY_PROJECT_ID` | Your Railway project ID | From Railway dashboard URL or run `railway status` |

### Getting Your Railway Credentials

```bash
# Login to Railway (if not already)
railway login

# Get your project info
railway status
# Output shows: Project: fixturecast, Environment: production

# Get your API token
railway whoami
# Or create a new token at: https://railway.app/account/tokens
```

## Workflows Overview

### 1. Bot Deploy (`bot-deploy.yml`)

**Triggers:** Push to `main` branch when files in `scripts/` change

**What it does:**
- Detects which bot scripts changed
- Runs linting and syntax validation
- Triggers Railway redeploy for affected bots
- Runs health check after deployment

### 2. Health Monitor (`health-monitor.yml`)

**Triggers:** Every 30 minutes (scheduled)

**What it does:**
- Checks ML API and Backend API health
- Auto-restarts services if unhealthy
- Verifies recovery after restart

### 3. Daily Predictions (`daily-predictions.yml`)

**Triggers:** 6:00 AM UTC daily

**What it does:**
- Pre-generates predictions for all today's matches
- Caches Match of the Day prediction
- Reports statistics in workflow summary

## Enabling Workflows

After adding secrets, workflows will run automatically on:
- **Bot Deploy:** Every push to `main` with script changes
- **Health Monitor:** Every 30 minutes
- **Daily Predictions:** 6 AM UTC daily

You can also manually trigger any workflow:
1. Go to **Actions** tab
2. Select the workflow
3. Click **Run workflow**

## Environment Configuration

The workflows expect these Railway services:
- `ml-api` - ML prediction API
- `backend-api` - Backend fixtures API
- `discord-bot` - Discord bot
- `telegram-bot` - Telegram bot
- `reddit-bot` - Reddit bot (optional)
- `twitter-bot` - Twitter bot (optional)

## Monitoring

Check workflow runs:
1. Go to **Actions** tab
2. View run history and logs
3. Check **Summary** for quick status

## Troubleshooting

### "Railway command not found"
The workflow installs Railway CLI automatically. If issues persist, check the logs.

### "Permission denied"
Ensure `RAILWAY_TOKEN` has sufficient permissions (project deploy access).

### "Service not found"
Verify service names match exactly in Railway dashboard.

### Manual Restart
If a service is stuck, manually redeploy from Railway dashboard.
