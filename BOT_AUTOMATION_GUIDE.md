# FixtureCast Bot Automation Guide

Your Telegram and Discord bots are now **fully automated** on Railway! 🎉

## What's Automated

### 1. **24/7 Bot Operation** ✅
- ✅ Discord Bot - Always online, responds to `/predict`, `/today`, `/motd` commands
- ✅ Telegram Bot - Always online, responds to commands
- ✅ Reddit Bot - Monitors mentions and comments
- ✅ Twitter Bot - Posts daily predictions
- ✅ **NEW: Scheduler** - Automated daily tasks

### 2. **Automated Daily Tasks** 📅
The new `scheduler` service automatically posts:
- **8:00 AM UTC** - Match of the Day prediction (Telegram + Discord)
- **Every 5 minutes** - Health monitoring of APIs
- **Auto-recovery** from API failures

### 3. **Automated Deployments** 🚀
Whenever you push bot code changes to GitHub:
1. GitHub Actions validates the code
2. Railway auto-deploys the updated services
3. Discord webhook notifies you of deployment status

### 4. **Automated Model Training** 🤖
Every Monday at 3 AM UTC:
1. GitHub Actions trains ML models with latest data
2. Updates and commits trained models
3. Railway auto-deploys new models
4. Discord notification sent

## Railway Services Running

```
✅ web           - ML API (Port 8000)
✅ discord_bot   - Discord bot (always online)
✅ telegram_bot  - Telegram bot (always online)
✅ reddit_bot    - Reddit monitor
✅ twitter_bot   - Daily Twitter posts
✅ scheduler     - Automated daily tasks (NEW!)
```

## Configuration Steps

### Step 1: Enable Telegram Channel Posts

To enable automated daily posts to your Telegram channel:

1. Create a Telegram channel (or use existing)
2. Add your bot as an administrator
3. Get the channel ID:
   ```bash
   # Forward a message from your channel to @userinfobot
   # Or use this method:
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Add to Railway environment variables:
   ```
   TELEGRAM_CHANNEL_ID=-100123456789  # Your channel ID (starts with -100)
   ```

### Step 2: Verify Railway Environment Variables

Required variables for automation:

```bash
# Bot Tokens
DISCORD_BOT_TOKEN=your_discord_token
TELEGRAM_BOT_TOKEN=your_telegram_token

# API URLs (Railway internal URLs)
ML_API_URL=http://web.railway.internal:8000
BACKEND_API_URL=http://backend.railway.internal:8001

# App URL
APP_URL=https://fixturecast.com

# Optional: Automated posts
TELEGRAM_CHANNEL_ID=-100123456789  # For daily broadcasts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # For announcements

# GitHub Integration
RAILWAY_TOKEN=railway_token_here  # Optional, for manual deploys
```

### Step 3: Deploy the Scheduler

The scheduler is now in your `Procfile`. To activate:

1. **Commit and push changes:**
   ```bash
   git add Procfile scripts/scheduled_tasks.py .github/workflows/deploy-bots.yml
   git commit -m "Add automated scheduler for daily tasks"
   git push origin main
   ```

2. **Railway will automatically:**
   - Detect the new `scheduler` service in Procfile
   - Start the scheduler alongside other bots
   - Keep it running 24/7

3. **Verify it's running:**
   ```bash
   railway logs -s scheduler
   ```

   You should see:
   ```
   ============================================================
   FixtureCast Scheduled Tasks
   ============================================================
   Started at: 2025-11-28 17:56:32 UTC

   📅 Daily Schedule:
     - Match of the Day: 08:00 UTC
     - Health checks: Every 5 minutes

   ✅ Scheduler is running!
   ```

## How Automation Works

### Daily Match of the Day Posts

**What happens at 8:00 AM UTC every day:**

1. Scheduler fetches today's Match of the Day from backend API
2. Gets AI prediction from ML API
3. Posts formatted prediction to:
   - Telegram channel (if `TELEGRAM_CHANNEL_ID` is set)
   - Discord webhook (if `DISCORD_WEBHOOK_URL` is set)

**Sample Post:**
```
⭐ MATCH OF THE DAY ⭐

Liverpool vs Manchester City
📅 November 28 at 15:00 UTC
🏆 Premier League

📊 AI Prediction
• Liverpool: 45.3%
• Draw: 28.1%
• Manchester City: 26.6%

🎯 Predicted Score: 2-1

🔗 Full analysis: https://fixturecast.com/prediction/12345
```

### Health Monitoring

Every 5 minutes, the scheduler:
- Checks if Backend API and ML API are responding
- Logs any failures
- Could send alerts (extend to add Discord notifications)

### Auto-Deployment

**When you update bot code:**
1. Push to GitHub `main` branch
2. GitHub Actions workflow runs
3. Validates Python bot scripts
4. Railway detects the push and auto-deploys
5. All services restart with new code
6. Discord notification sent (if webhook configured)

## Monitoring & Logs

### View Live Logs

```bash
# All services
railway logs

# Specific service
railway logs -s scheduler
railway logs -s discord_bot
railway logs -s telegram_bot

# Follow logs (real-time)
railway logs -s scheduler --follow
```

### Check Service Status

**Via Railway Dashboard:**
1. Go to railway.app → Your Project
2. Click each service
3. View metrics: CPU, Memory, Restarts
4. Check deployment history

**Via CLI:**
```bash
railway status
```

## Customizing Automation

### Change Daily Post Time

Edit `scripts/scheduled_tasks.py`:

```python
# Change from 8:00 AM to 10:00 AM UTC
asyncio.create_task(
    self.run_at_time(time(10, 0), self.daily_motd_post, "Daily MOTD Post")
),
```

### Add Weekly Summary Posts

Add to `scripts/scheduled_tasks.py`:

```python
async def weekly_summary_post(self):
    """Post weekly performance summary"""
    # Fetch metrics from API
    # Format summary message
    # Post to channels
    pass

# In start() method:
asyncio.create_task(
    self.run_at_time(time(9, 0), self.weekly_summary_post, "Weekly Summary")
),
```

### Add Custom Scheduled Tasks

The scheduler supports two types of tasks:

1. **Daily at specific time:**
   ```python
   await self.run_at_time(time(14, 30), my_task, "My Task Name")
   ```

2. **Periodic interval:**
   ```python
   await self.run_periodic(30, my_task, "My Task Name")  # Every 30 minutes
   ```

## Troubleshooting

### Scheduler Not Running?

```bash
# Check logs
railway logs -s scheduler

# Common issues:
# 1. Service not in Procfile → Check Procfile has "scheduler: python scripts/scheduled_tasks.py"
# 2. Python dependencies missing → Check requirements.txt includes python-telegram-bot, discord.py
# 3. API URLs wrong → Verify ML_API_URL and BACKEND_API_URL in Railway env vars
```

### Posts Not Appearing?

```bash
# Check scheduler logs
railway logs -s scheduler

# Verify:
# 1. TELEGRAM_CHANNEL_ID is set correctly (starts with -100)
# 2. Bot is admin in Telegram channel
# 3. DISCORD_WEBHOOK_URL is valid
# 4. APIs are healthy (check scheduler logs for health checks)
```

### Deployment Failed?

```bash
# View GitHub Actions logs
# Go to: github.com/your-repo/actions

# Check Railway logs
railway logs

# Common issues:
# 1. Python syntax errors → GitHub Actions will catch these
# 2. Missing dependencies → Add to requirements.txt
# 3. Environment variables missing → Check Railway dashboard
```

## Cost Optimization

**Current setup runs 6 services 24/7:**
- Estimated cost: **$50-75/month** on Railway

**To reduce costs:**

1. **Combine bots into one service** (reduces Railway service count)
2. **Use cheaper VPS** for bots ($5/mo Hetzner/DigitalOcean)
3. **Keep only Discord + Telegram** (disable Reddit/Twitter if unused)
4. **Run scheduler as Railway Cron Job** (cheaper than 24/7 service)

**Recommended setup for cost:**
- Railway: ML API + Backend API (~$20/mo)
- Hetzner VPS: All bots + scheduler (~$5/mo)

## GitHub Actions Secrets

For full automation, add these secrets to your GitHub repository:

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:

```
RAILWAY_TOKEN          - Optional, for Railway CLI deployments
DISCORD_WEBHOOK_URL    - For deployment notifications
API_FOOTBALL_KEY       - For model training workflow
```

## Railway Auto-Deploy Setup

Ensure Railway is watching your GitHub repo:

1. Railway dashboard → Your Project → Settings
2. Under "Deployment":
   - ✅ Auto-deploy on push to `main`
   - ✅ Watch paths: `scripts/`, `backend/`, `ml_engine/`, `Procfile`
3. Railway will automatically deploy when you push changes

## Testing Before Deploy

Always test locally before pushing:

```bash
# Test scheduler
python scripts/scheduled_tasks.py

# Test Discord bot
python scripts/discord_bot.py

# Test Telegram bot
python scripts/telegram_bot.py
```

## Next Steps

1. **✅ Push current changes to GitHub** to deploy scheduler
2. **✅ Set TELEGRAM_CHANNEL_ID** in Railway if you want automated channel posts
3. **✅ Monitor first automated post** at 8 AM UTC tomorrow
4. **✅ Customize schedule** based on your timezone/audience
5. **⭐ Add more automation** (weekly summaries, match alerts, etc.)

---

## Summary

🎉 **Your bots are now fully automated!**

- ✅ Running 24/7 on Railway
- ✅ Auto-deploy on code changes
- ✅ Daily scheduled predictions
- ✅ Health monitoring
- ✅ Auto-model training weekly

No manual intervention needed! Just push code and Railway handles the rest.
