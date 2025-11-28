# Railway Quick Configuration for Automated Bots

## Environment Variables to Set in Railway

Go to **Railway Dashboard → Your Project → Variables** and add these:

### 🟢 Required (Core Functionality)

```env
# Discord Bot
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# API URLs (use Railway internal networking)
ML_API_URL=http://web.railway.internal:8000
BACKEND_API_URL=http://backend.railway.internal:8001

# Your public app URL
APP_URL=https://fixturecast.com
```

### 🟡 Optional (Automated Posts)

```env
# For automated daily Telegram channel posts
TELEGRAM_CHANNEL_ID=-100123456789

# For automated Discord announcements
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### 🔵 Optional (Reddit & Twitter Bots)

```env
# Reddit Bot
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=FixtureCast Bot v1.0

# Twitter Bot
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
```

### ⚙️ System Variables (Usually auto-set)

```env
PORT=8000
PYTHON_VERSION=3.12
```

---

## Getting Telegram Channel ID

### Method 1: Using @userinfobot

1. Create a Telegram channel
2. Add your bot as administrator
3. Forward a message from the channel to [@userinfobot](https://t.me/userinfobot)
4. It will show the channel ID (starts with `-100`)

### Method 2: Using Telegram API

```bash
# Send a message in your channel (as admin)
# Then run:
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# Look for "chat":{"id":-100123456789,...}
```

---

## Creating Discord Webhook

1. Go to your Discord server
2. Right-click channel → Edit Channel → Integrations
3. Click "Create Webhook"
4. Give it a name (e.g., "FixtureCast Bot")
5. Copy webhook URL
6. Paste into Railway: `DISCORD_WEBHOOK_URL`

---

## Railway Service URLs (Internal)

Railway provides internal networking between services:

| Service | Internal URL |
|---------|--------------|
| ML API | `http://web.railway.internal:8000` |
| Backend API | `http://backend.railway.internal:8001` |
| Discord Bot | (no URL, runs as daemon) |
| Telegram Bot | (no URL, runs as daemon) |
| Scheduler | (no URL, runs as daemon) |

**Important:** Use these internal URLs for `ML_API_URL` and `BACKEND_API_URL` to avoid external network calls.

---

## Verifying Configuration

After setting variables, restart services in Railway:

```bash
# Using Railway CLI
railway restart

# Or use Railway dashboard:
# Click service → Click "Restart"
```

Then check logs:

```bash
railway logs -s scheduler
railway logs -s telegram_bot
railway logs -s discord_bot
```

Look for:
- ✅ `Bot is now running!`
- ✅ `Scheduler is running!`
- ❌ `API not reachable` → Check `ML_API_URL` and `BACKEND_API_URL`

---

## Testing Automated Posts

### Option 1: Trigger Manually (for testing)

Add this to `scheduled_tasks.py` and deploy:

```python
# In main() function:
print("🧪 Test mode: Posting immediately...")
await scheduler.daily_motd_post()
```

### Option 2: Wait for Scheduled Time

The scheduler runs at **8:00 AM UTC** daily.

Convert to your timezone:
- PST: 12:00 AM (midnight)
- EST: 3:00 AM
- GMT: 8:00 AM
- CET: 9:00 AM
- IST: 1:30 PM

---

## Service Health Checks

Railway automatically monitors services:

- **Restart Policy:** Auto-restart on crash (up to 10 retries)
- **Health Checks:** Railway pings `/health` endpoint (for web services)
- **Logs Retention:** 7 days

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot offline | Check Railway logs for errors |
| No automated posts | Verify `TELEGRAM_CHANNEL_ID` and bot is admin |
| API calls failing | Use Railway internal URLs, not `localhost` |
| Out of memory | Upgrade Railway plan or reduce services |
| Deployment failed | Check GitHub Actions logs |

---

## Quick Deployment Checklist

- [ ] All environment variables set in Railway
- [ ] Bot tokens are valid and fresh
- [ ] Telegram bot is admin in channel
- [ ] Discord webhook is created
- [ ] `Procfile` includes all 6 services
- [ ] Code pushed to GitHub main branch
- [ ] Railway auto-deploy is enabled
- [ ] Services show as "Running" in Railway dashboard

---

## Cost Management

Current setup: **6 services running 24/7**

Estimated monthly cost on Railway: **$50-75**

To reduce costs:
1. Disable unused bots (Reddit/Twitter) by removing from `Procfile`
2. Use Railway Cron instead of 24/7 scheduler (coming soon in Railway)
3. Move bots to a $5 VPS and keep only APIs on Railway

---

**Ready to deploy?** Run:

```bash
./deploy_automation.sh
```

Or manually:

```bash
git add .
git commit -m "Add bot automation"
git push origin main
```

Railway will handle the rest! 🚀
