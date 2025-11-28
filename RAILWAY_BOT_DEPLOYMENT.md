# Deploy Bots to Railway

Railway supports running multiple services via the `Procfile`. Your bots and APIs will all run as separate Railway services within the same project.

## Setup

### 1. Link GitHub Repository to Railway
```bash
# If not already linked:
railway login
railway init
```

### 2. Configure Railway Secrets

Add environment variables via Railway dashboard:

**Discord Bot:**
- `DISCORD_BOT_TOKEN` — Discord bot token
- `DISCORD_WEBHOOK_URL` — Discord webhook for notifications
- `ML_API_URL` — http://[your-ml-api-url]:8000
- `BACKEND_API_URL` — http://[your-backend-url]:8001

**Telegram Bot:**
- `TELEGRAM_BOT_TOKEN` — Telegram bot token

**Reddit Bot:**
- `REDDIT_CLIENT_ID` — Reddit app credentials
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

**Twitter Bot:**
- `TWITTER_BEARER_TOKEN` — Twitter API v2 token

**APIs (if not already set):**
- `API_FOOTBALL_KEY` — API-Football key
- `PORT` — 8001 (for backend)
- `ML_PORT` — 8000 (for ML API)

### 3. Deploy

Railway auto-deploys on every `git push` to `main`.

```bash
# Push changes to trigger Railway deployment
git add -A
git commit -m "Add bot services to Procfile"
git push origin main
```

Railway will read the `Procfile` and start:
- `web` service (ML API) — port 8000
- `discord_bot` service
- `telegram_bot` service
- `reddit_bot` service
- `twitter_bot` service

### 4. Monitor

**Via Railway Dashboard:**
1. Go to railway.app → Your Project
2. Click each service to view logs and metrics
3. Each service auto-restarts on crash (Restart Policy: 10 retries)

**Via CLI:**
```bash
# View logs for a specific service
railway logs -s discord_bot

# View all logs
railway logs
```

## Service URLs in Railway

After deployment, Railway assigns internal network URLs:

- Discord Bot: `$DISCORD_BOT` (internal)
- Telegram Bot: `$TELEGRAM_BOT` (internal)
- ML API: `$ML_API_URL` (expose via Railway plugin if needed)
- Backend API: `$BACKEND_API_URL` (expose via Railway plugin if needed)

Your bots can reach each other via Railway's internal network.

## Troubleshooting

### Bot not starting?
```bash
railway logs -s discord_bot
# Check for missing env vars, import errors, or API connectivity issues
```

### API calls failing?
- Ensure `ML_API_URL` and `BACKEND_API_URL` point to Railway internal addresses
- In Railway, services communicate via internal network (don't use `localhost`)
- Use the service variable (e.g., `$ml_api_service`) or the Railway-assigned URL

### Out of memory?
- Upgrade Railway plan or split bots into separate Railway projects
- Monitor RAM usage in Railway dashboard

## Cost Estimate

**Railway Pricing (as of Nov 2025):**
- $5/month baseline
- Additional $0.25/hour per service
- For 5 services (ML API + 4 bots) running 24/7: ~$50-75/month

Cheaper option: Move some bots to a VPS ($3-5/mo) if you want to save costs.

---

## Local Testing Before Deployment

Before pushing to Railway, test locally:

```bash
# Test Discord bot
. .venv/bin/activate
python scripts/discord_bot.py

# Test Telegram bot (in another terminal)
python scripts/telegram_bot.py

# Check logs
tail -f logs/discord_bot.log
```

Once verified locally, commit and push to Railway.
