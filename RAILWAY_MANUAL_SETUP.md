# Railway Bot Services - Manual Setup

Since Railway's Procfile multi-service support is limited, you need to manually create services in the Railway dashboard.

## Quick Steps

### 1. Go to railway.app → Your Project

### 2. Click **Settings** → scroll to **Service Creation**

Or go directly to project → **+ New** button to add services.

### 3. Create Each Service

For each bot, click **Add Service** and select:
- **Source**: GitHub Repository (`btltech/fixturecast2`)
- **Branch**: `main`
- **Build Settings**: Dockerfile

Then create these services:

| Service Name | Start Command |
|---|---|
| `discord-bot` | `python scripts/discord_bot.py` |
| `telegram-bot` | `python scripts/telegram_bot.py` |
| `reddit-bot` | `python scripts/reddit_bot.py` |
| `twitter-bot` | `python scripts/twitter_bot.py` |

### 4. Set Environment Variables for Each Service

For **discord-bot** service, go to **Variables** and add:
```
DISCORD_BOT_TOKEN=your_token_here
DISCORD_WEBHOOK_URL=your_webhook_here
ML_API_URL=http://localhost:8000
BACKEND_API_URL=http://localhost:8001
API_FOOTBALL_KEY=your_key_here
```

For **telegram-bot**, add:
```
TELEGRAM_BOT_TOKEN=your_token_here
ML_API_URL=http://localhost:8000
BACKEND_API_URL=http://localhost:8001
API_FOOTBALL_KEY=your_key_here
```

Similar for reddit-bot and twitter-bot.

### 5. Deploy

Each service will auto-deploy once created and will restart on crashes.

---

## Alternative: Use railway.json (Advanced)

If manual setup doesn't work, replace `railway.toml` with a `railway.json` that defines all services, but this requires using Railway's CLI or API.

---

## Troubleshooting

**Services still not showing?**
- Verify you're in the right project
- Check **Deployments** tab - there should be a build for your recent push
- If build failed, check the build logs for errors

**Service won't start?**
- Click service → **Logs** to see startup errors
- Usually missing environment variables or import errors

**Need help?**
Railway docs: https://docs.railway.app/guides/services
