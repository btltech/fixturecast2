# Railway CLI Setup Guide

This guide shows you how to use the Railway CLI to automatically create and configure all bot services.

## Prerequisites

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
```

### 2. Authenticate with Railway
```bash
railway login
```
This will open your browser to authenticate. Your credentials are saved locally.

### 3. Set Your Project
Navigate to your project directory and set the Railway project:
```bash
cd /Users/mobolaji/.gemini/antigravity/scratch/fixturecast
railway init
# Select your existing "ml-training" project when prompted
```

## Option 1: Bash Script (Recommended)

### Quick Start
```bash
# Make script executable
chmod +x setup_railway_bots.sh

# Run the setup
./setup_railway_bots.sh
```

### What It Does
- ✅ Creates 4 bot services (discord, telegram, reddit, twitter)
- ✅ Sets up start commands for each
- ✅ Configures environment variables from your shell
- ✅ Displays colored output for easy tracking

### Environment Variables Required
Before running the script, ensure these are set in your shell or `.env` file:

```bash
# For Discord Bot
export DISCORD_BOT_TOKEN="your_discord_token"
export DISCORD_WEBHOOK_URL="your_webhook_url"

# For Telegram Bot
export TELEGRAM_BOT_TOKEN="your_telegram_token"

# For Reddit Bot
export REDDIT_CLIENT_ID="your_reddit_id"
export REDDIT_CLIENT_SECRET="your_reddit_secret"
export REDDIT_USER_AGENT="FixtureCast/1.0"

# For Twitter Bot
export TWITTER_BEARER_TOKEN="your_twitter_token"

# Shared API Keys
export API_FOOTBALL_KEY="your_api_football_key"
```

**Load from `.env` file:**
```bash
set -a
source .env
set +a
./setup_railway_bots.sh
```

## Option 2: Python Script

### Prerequisites
```bash
pip install requests
```

### Setup
```bash
# Make executable
chmod +x setup_railway_bots.py

# Set Railway token and project ID
export RAILWAY_TOKEN="your_railway_api_token"
export RAILWAY_PROJECT_ID="your_project_id"

# Run
python3 setup_railway_bots.py
```

**Get your tokens:**
- Railway Token: https://railway.app/account/tokens
- Project ID: From your project URL in Railway dashboard (`railway.app/project/{PROJECT_ID}`)

## Option 3: Manual Railway CLI Commands

If you prefer step-by-step:

### 1. Create Discord Bot Service
```bash
railway service create \
  --name discord-bot \
  --repo btltech/fixturecast2 \
  --branch main \
  --start-command "python scripts/discord_bot.py"
```

### 2. Set Discord Bot Environment Variables
```bash
railway service select discord-bot
railway variable set DISCORD_BOT_TOKEN "$DISCORD_BOT_TOKEN"
railway variable set DISCORD_WEBHOOK_URL "$DISCORD_WEBHOOK_URL"
railway variable set ML_API_URL "http://ml-api:8002"
railway variable set BACKEND_API_URL "http://backend:8001"
railway variable set API_FOOTBALL_KEY "$API_FOOTBALL_KEY"
```

### 3. Repeat for Other Bots
```bash
# Telegram
railway service create --name telegram-bot --repo btltech/fixturecast2 --branch main --start-command "python scripts/telegram_bot.py"
railway service select telegram-bot
railway variable set TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
railway variable set ML_API_URL "http://ml-api:8002"
railway variable set BACKEND_API_URL "http://backend:8001"
railway variable set API_FOOTBALL_KEY "$API_FOOTBALL_KEY"

# Reddit
railway service create --name reddit-bot --repo btltech/fixturecast2 --branch main --start-command "python scripts/reddit_bot.py"
railway service select reddit-bot
railway variable set REDDIT_CLIENT_ID "$REDDIT_CLIENT_ID"
railway variable set REDDIT_CLIENT_SECRET "$REDDIT_CLIENT_SECRET"
railway variable set REDDIT_USER_AGENT "FixtureCast/1.0"
railway variable set ML_API_URL "http://ml-api:8002"
railway variable set BACKEND_API_URL "http://backend:8001"
railway variable set API_FOOTBALL_KEY "$API_FOOTBALL_KEY"

# Twitter
railway service create --name twitter-bot --repo btltech/fixturecast2 --branch main --start-command "python scripts/twitter_bot.py"
railway service select twitter-bot
railway variable set TWITTER_BEARER_TOKEN "$TWITTER_BEARER_TOKEN"
railway variable set ML_API_URL "http://ml-api:8002"
railway variable set BACKEND_API_URL "http://backend:8001"
railway variable set API_FOOTBALL_KEY "$API_FOOTBALL_KEY"
```

## Verification

### View All Services
```bash
railway service list
```

### View Specific Service Logs
```bash
railway service select discord-bot
railway logs
```

### Check Service Environment Variables
```bash
railway service select discord-bot
railway variable list
```

### Restart a Service
```bash
railway service select discord-bot
railway restart
```

## Troubleshooting

### Service Won't Start
1. Check logs: `railway service select {service-name} && railway logs`
2. Verify environment variables: `railway variable list`
3. Check that start command is correct: `railway service describe`

### Environment Variables Not Set
```bash
# View what's set
railway variable list

# Manually set missing variables
railway variable set VARIABLE_NAME "value"

# Delete incorrect variable
railway variable delete VARIABLE_NAME
```

### Services Not Visible in Dashboard
1. Wait 30-60 seconds for services to appear
2. Refresh railway.app in browser
3. Check build logs in Railway dashboard
4. Verify GitHub repo is connected

### Connection Issues Between Services
Within Railway, services communicate via internal domain names:
- `backend:8001` (Backend API)
- `ml-api:8002` (ML API)
- `redis:6379` (Redis cache)

If services can't connect, check network settings in Railway UI.

## Useful Railway CLI Commands

```bash
# Show current project
railway project

# Switch project
railway init

# Open project in browser
railway open

# View environment details
railway status

# Run command in service
railway run {command}

# SSH into service
railway shell

# View metrics
railway metrics

# Create PostgreSQL plugin
railway add

# Remove service
railway service remove {service-name}

# View all CLI options
railway --help
```

## Monitoring & Logs

### Real-time Logs
```bash
railway service select discord-bot
railway logs --follow
```

### Filter Logs
```bash
railway logs --grep "ERROR"
railway logs --grep "Connected"
```

### View Historical Logs
```bash
railway logs --limit 100
```

## Cost Optimization

Each bot service runs ~$5/month on Railway's free tier ($5 baseline credit), plus additional usage:
- Memory: Bots typically use 128-256MB → minimal cost
- CPU: Minimal, mostly idle waiting for commands
- Network egress: Minimal outbound traffic to Discord/Telegram APIs

**Estimated Total:** $10-20/month for 4 bots + existing ML APIs

To reduce costs:
1. Combine lightweight bots into single service
2. Use cron jobs for scheduled tasks
3. Monitor memory usage in Railway metrics

## Next Steps

1. ✅ Create bot services using preferred method above
2. ⏳ Wait 1-2 minutes for services to deploy
3. 📊 Verify services are running in Railway dashboard
4. 📝 Check logs for any startup errors
5. 🧪 Test commands in Discord/Telegram
6. 🔄 Enable auto-restart if needed: Railway dashboard → Service → Deployment → Policies

---

**Questions?** Check Railway docs: https://docs.railway.app
