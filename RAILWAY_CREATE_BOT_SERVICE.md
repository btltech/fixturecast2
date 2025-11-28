# Create Bot Services on Railway (Step by Step)

## One-Time Setup Per Bot (4 total: Discord, Telegram, Reddit, Twitter)

### Step 1: Go to Railway Dashboard
- Open https://railway.app
- Select your **fixturecast** project

### Step 2: Click "+ New"
- Top right corner, click **+ New**
- Select **GitHub Repo**

### Step 3: Configure Service

**For Discord Bot:**
- Repo: `btltech/fixturecast2`
- Branch: `main`
- Name: `discord-bot`
- Start Command: `python scripts/discord_bot.py`

**For Telegram Bot:**
- Repo: `btltech/fixturecast2`
- Branch: `main`
- Name: `telegram-bot`
- Start Command: `python scripts/telegram_bot.py`

**For Reddit Bot:**
- Repo: `btltech/fixturecast2`
- Branch: `main`
- Name: `reddit-bot`
- Start Command: `python scripts/reddit_bot.py`

**For Twitter Bot:**
- Repo: `btltech/fixturecast2`
- Branch: `main`
- Name: `twitter-bot`
- Start Command: `python scripts/twitter_bot.py`

### Step 4: Add Environment Variables

After creating each service:
1. Click the service name in the left sidebar
2. Go to **Variables** tab
3. Add each variable one by one

**Discord Bot Variables:**
```
DISCORD_BOT_TOKEN=<your_token>
DISCORD_WEBHOOK_URL=<your_webhook>
ML_API_URL=http://ml-api:8002
BACKEND_API_URL=http://backend:8001
API_FOOTBALL_KEY=<your_key>
```

**Telegram Bot Variables:**
```
TELEGRAM_BOT_TOKEN=<your_token>
ML_API_URL=http://ml-api:8002
BACKEND_API_URL=http://backend:8001
API_FOOTBALL_KEY=<your_key>
```

**Reddit Bot Variables:**
```
REDDIT_CLIENT_ID=<your_id>
REDDIT_CLIENT_SECRET=<your_secret>
REDDIT_USER_AGENT=FixtureCast/1.0
ML_API_URL=http://ml-api:8002
BACKEND_API_URL=http://backend:8001
API_FOOTBALL_KEY=<your_key>
```

**Twitter Bot Variables:**
```
TWITTER_BEARER_TOKEN=<your_token>
ML_API_URL=http://ml-api:8002
BACKEND_API_URL=http://backend:8001
API_FOOTBALL_KEY=<your_key>
```

### Step 5: Verify Running
1. Click **Deployments** tab
2. Wait for green checkmark (deployment complete)
3. Click **Logs** tab
4. Should see bot startup messages
5. If errors, fix and push to GitHub (auto-redeploy)

---

## That's It

Each bot is now running 24/7 on Railway, auto-redeploying whenever you push code changes to GitHub.

**To update bot logic:**
1. Edit `scripts/discord_bot.py` (or whatever)
2. `git push`
3. Railway auto-deploys the new version
