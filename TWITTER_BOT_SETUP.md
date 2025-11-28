# FixtureCast Twitter Bot - Setup Guide

## Overview
Automatically post AI predictions to Twitter/X every morning with a beautiful thread format.

## Features
- 🌅 Posts "Match of the Day" + top 2 fixtures
- 📊 Includes probabilities, predicted scores, confidence levels
- 🔗 Links back to your app for full analysis
- 🤖 Fully automated (cron job ready)

## Setup Instructions

### 1. Get Twitter API Access
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new project and app
3. Enable "OAuth 1.0a" with "Read and Write" permissions
4. Generate your API keys and access tokens

### 2. Configure Environment
```bash
# Copy the example env file
cp .env.twitter.example .env

# Edit .env and add your credentials
nano .env
```

Fill in:
- `TWITTER_API_KEY` - Your API Key
- `TWITTER_API_SECRET` - Your API Secret
- `TWITTER_ACCESS_TOKEN` - Your Access Token
- `TWITTER_ACCESS_SECRET` - Your Access Token Secret
- `APP_URL` - Your deployed app URL (e.g., https://fixturecast.app)

### 3. Install Dependencies
```bash
pip install tweepy python-dotenv requests
```

### 4. Test the Bot
```bash
# Make sure your backend and ML APIs are running
python backend/main.py &    # Port 8001
python backend/ml_api.py &  # Port 8000

# Run the Twitter bot manually
python scripts/twitter_bot.py
```

Expected output:
```
🔄 Fetching today's fixtures...
  → Processing match 1/3: Arsenal vs Chelsea
  ✅ Posted tweet 1
  ...
✅ Successfully posted thread!
```

### 5. Automate with Cron (Linux/Mac)
```bash
# Edit your crontab
crontab -e

# Add this line to post every day at 8 AM
0 8 * * * cd /path/to/fixturecast && /usr/bin/python3 scripts/twitter_bot.py >> logs/twitter_bot.log 2>&1
```

### 6. Automate with Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 8:00 AM
4. Action: Start a Program
   - Program: `python`
   - Arguments: `scripts/twitter_bot.py`
   - Start in: `C:\path\to\fixturecast`

## Example Thread Output

**Tweet 1 (Opening):**
```
🔮 FixtureCast Daily Predictions - November 28, 2024

AI-powered match analysis for today's top fixtures 👇

12 matches analyzed
#Football #Predictions #AI
```

**Tweet 2 (Match of the Day):**
```
⭐ MATCH OF THE DAY ⭐

🏴󠁧󠁢󠁥󠁮󠁧󠁿 Arsenal vs Chelsea
⏰ 17:30

🔮 AI Prediction: 2-1
📊 Arsenal 58% | Draw 24% | Chelsea 18%
🟡 Medium Confidence

🔗 Full Analysis: https://fixturecast.app/prediction/12345?league=39
```

**Tweet 3 (Second Match):**
```
🇪🇸 Real Madrid vs Barcelona
⏰ 20:00

🔮 AI Prediction: 2-2
📊 Real Madr 42% | Draw 31% | Barcelona 27%
🔴 Close Match

🔗 Full Analysis: https://fixturecast.app/prediction/12346?league=140
```

**Tweet 4 (Closing):**
```
📱 Get predictions for ALL of today's matches:
https://fixturecast.app

✨ Features:
• 8-model AI ensemble
• Live probabilities
• Detailed analysis
• FREE to use!

#PremierLeague #LaLiga #SerieA #Bundesliga
```

## Customization

### Change Number of Matches
Edit `scripts/twitter_bot.py`, line ~180:
```python
# Show top 3 matches (change this number)
if len(top_fixtures) >= 3:
    break
```

### Change Post Time
Modify your cron job or Task Scheduler trigger.

### Add More Leagues
The bot automatically includes matches from all supported leagues.

## Troubleshooting

### "Missing Twitter API credentials"
- Make sure `.env` file exists in the project root
- Check that all `TWITTER_*` variables are filled in

### "Backend API not reachable"
- Ensure `python backend/main.py` is running on port 8001
- Check `BACKEND_API_URL` in `.env`

### "Rate limit exceeded"
- Twitter has rate limits (50 tweets per day for free tier)
- Consider posting only once per day
- Upgrade to Twitter API Pro if needed

### "No fixtures today"
- Normal on days without matches
- The bot will skip posting automatically

## Best Practices

1. **Test first**: Always run manually before automating
2. **Monitor logs**: Check cron logs regularly
3. **Respect limits**: Don't spam (1 thread per day is ideal)
4. **Engage**: Reply to comments on your threads
5. **Track performance**: Use Twitter Analytics to see what works

## Analytics

Track engagement:
1. Go to [Twitter Analytics](https://analytics.twitter.com/)
2. Check impressions, engagement rate
3. Identify best posting times
4. Adjust content based on performance

## Legal

- Ensure you comply with Twitter's Automation Rules
- Don't mislead users (clearly label as AI predictions)
- Include responsible gambling disclaimers if applicable
- Follow platform's Terms of Service

## Support

If you encounter issues:
1. Check the logs: `logs/twitter_bot.log`
2. Test API endpoints manually: `curl http://localhost:8001/health`
3. Verify Twitter credentials in developer portal
4. Check Twitter API status page for outages

Happy tweeting! 🚀
