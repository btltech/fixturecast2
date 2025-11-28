# Reddit & Discord Bot Setup Guide

## Overview
Automatically respond to prediction requests on Reddit (r/soccer) and Discord football servers.

---

## 🟠 Reddit Bot Setup

### Features
- ✅ Monitors r/soccer, r/PremierLeague, r/LiverpoolFC, r/Gunners, etc.
- ✅ Responds to `!fixturecast Arsenal vs Chelsea`
- ✅ Posts formatted predictions with probabilities
- ✅ Auto-links to full analysis on your app
- ✅ Rate limiting to avoid spam

### 1. Create Reddit App

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..."
3. Fill in:
   - **Name**: FixtureCast Bot
   - **Type**: Select "script"
   - **Description**: AI football predictions
   - **Redirect URI**: http://localhost:8080
4. Click "Create app"
5. Note down:
   - **Client ID** (under the app name)
   - **Client Secret** (labeled "secret")

### 2. Create Bot Account (Recommended)

1. Create a new Reddit account for your bot (e.g., u/FixtureCastBot)
2. Verify the email
3. Build up some karma (~100) before posting (comment in a few subreddits)
4. This prevents being shadowbanned

### 3. Configure Environment

```bash
# Copy example .env
cp .env.example .env

# Edit .env
nano .env
```

Fill in:
```
REDDIT_CLIENT_ID=abc123...
REDDIT_CLIENT_SECRET=xyz789...
REDDIT_USERNAME=FixtureCastBot
REDDIT_PASSWORD=your_bot_password
REDDIT_USER_AGENT=FixtureCast Bot v1.0 by /u/YourMainAccount
```

### 4. Install Dependencies

```bash
pip install praw python-dotenv requests
```

### 5. Test the Bot

```bash
# Start APIs first
python backend/main.py &
python backend/ml_api.py &

# Run Reddit bot
python scripts/reddit_bot.py
```

Expected output:
```
✅ Authenticated as u/FixtureCastBot
👀 Monitoring: r/soccer, r/football, r/PremierLeague
Listening for: !fixturecast Team1 vs Team2
```

### 6. Usage Example

**Someone posts on r/soccer:**
```
!fixturecast Arsenal vs Chelsea
```

**Your bot replies:**
```
## 🔮 FixtureCast AI Prediction

**Arsenal vs Chelsea**
📅 November 28, 2024 at 17:30 UTC
🏆 Premier League

### 📊 Win Probabilities

| Outcome | Probability |
|---------|-------------|
| Arsenal Win | **58.3%** |
| Draw | **24.1%** |
| Chelsea Win | **17.6%** |

**Predicted Score:** 2-1

**🟡 Medium Confidence**

### 🎯 Betting Markets

- **Both Teams to Score (BTTS):** 64%
- **Over 2.5 Goals:** 52%

[📱 View Full AI Analysis & Detailed Stats](https://fixturecast.app/prediction/12345?league=39)

---

*I'm an AI-powered bot from FixtureCast. Predictions are generated using an 8-model ensemble...*
```

### 7. Run as Background Service

**Linux/Mac (systemd):**
```bash
# Create service file
sudo nano /etc/systemd/system/fixturecast-reddit.service
```

```ini
[Unit]
Description=FixtureCast Reddit Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/fixturecast
ExecStart=/usr/bin/python3 scripts/reddit_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable fixturecast-reddit
sudo systemctl start fixturecast-reddit

# Check status
sudo systemctl status fixturecast-reddit
```

**Windows (Task Scheduler):**
- Create a task that runs `scripts/reddit_bot.py` at startup
- Set to restart on failure

### 8. Best Practices

#### Subreddit Rules
- **Check rules** before posting in each subreddit
- Some subreddits ban bots - contact mods first
- r/soccer: Generally allows helpful bots
- Team subreddits: Ask permission first

#### Avoid Being Banned
- Don't spam (max 1 response per request)
- Wait 5-10 seconds between posts
- Don't post if not explicitly requested
- Include disclaimer about responsible gambling

#### Engagement Tips
- Reply to follow-up questions
- Thank users who appreciate your bot
- Fix bugs quickly if users report issues
- Monitor your bot's comment karma

---

## 💙 Discord Bot Setup

### Features
- ✅ Slash commands: `/predict`, `/today`, `/motd`, `/help`
- ✅ Beautiful embeds with team logos
- ✅ Color-coded by confidence level
- ✅ Works in DMs and servers

### 1. Create Discord Application

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name it "FixtureCast"
4. Go to "Bot" tab → Click "Add Bot"
5. Enable "Message Content Intent" (required)
6. Copy the bot token

### 2. Get Bot Invite Link

Still in the Developer Portal:
1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Use Slash Commands
4. Copy the generated URL
5. Open URL in browser to invite bot to your server

### 3. Configure Environment

```bash
# Edit .env
nano .env
```

Add:
```
DISCORD_BOT_TOKEN=your_long_bot_token_here
```

### 4. Install Dependencies

```bash
pip install discord.py python-dotenv requests
```

### 5. Test the Bot

```bash
# Run Discord bot
python scripts/discord_bot.py
```

Expected output:
```
✅ Backend API is reachable
✅ ML API is reachable
🚀 Starting Discord bot...
✅ Commands synced with Discord
✅ Logged in as FixtureCast#1234 (ID: 123456789)
📡 Connected to 1 servers
```

### 6. Usage Examples

#### /predict Command
```
/predict team1:Arsenal team2:Chelsea
```

Returns a rich embed with:
- Team logos
- Win probabilities (color-coded bars)
- Predicted score
- Confidence level
- BTTS and Over 2.5 stats
- Link to full analysis

#### /today Command
```
/today
```

Shows all matches scheduled for today, grouped by league.

#### /motd Command
```
/motd
```

Shows prediction for the Match of the Day.

#### /help Command
```
/help
```

Shows all available commands.

### 7. Join Football Discord Servers

#### Finding Servers:
- Search "football discord" or "soccer discord" on Google
- Check r/soccer sidebar for Discord links
- Team-specific servers (e.g., Arsenal, Liverpool, etc.)
- Disboard.org - search "football"

#### Joining Strategy:
1. **Start small**: Join 2-3 servers
2. **Introduce yourself**: In #introductions or equivalent
   - "Hi! I created FixtureCast, an AI prediction bot. Type /help to try it!"
3. **Be helpful**: Respond quickly to /predict requests
4. **Don't spam**: Only post when requested
5. **Engage**: Discuss predictions, thank users

#### Grow Organically:
- Users will invite your bot to their servers
- Accurate predictions = word of mouth
- Pin helpful predictions in server channels

### 8. Run as Background Service

**Linux/Mac (systemd):**
```bash
sudo nano /etc/systemd/system/fixturecast-discord.service
```

```ini
[Unit]
Description=FixtureCast Discord Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/fixturecast
ExecStart=/usr/bin/python3 scripts/discord_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable fixturecast-discord
sudo systemctl start fixturecast-discord
```

---

## 📊 Growth Metrics to Track

### Reddit
- **Comments posted**: How many requests did you fulfill?
- **Upvotes**: Are responses helpful?
- **Mentions**: Are people talking about your bot?
- **Click-through rate**: How many click your app link?

### Discord
- **Servers joined**: How many communities have your bot?
- **Command usage**: Which commands are most popular?
- **Active users**: How many unique users use bot per week?
- **Retention**: Do servers keep your bot?

---

## 🚨 Troubleshooting

### Reddit Bot

**"Invalid credentials"**
- Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET
- Make sure app type is "script"
- Verify username and password are correct

**"Rate limit exceeded"**
- Normal - Reddit limits posting frequency
- Bot waits 60 seconds and retries
- Don't circumvent this (you'll get banned)

**"Shadowbanned"**
- New accounts need karma before posting
- Post helpful comments manually first
- Check status at /r/ShadowBan

### Discord Bot

**"Missing Access"**
- Re-invite bot with correct permissions
- Check "Message Content Intent" is enabled
- Ensure bot role is above other roles

**"Commands not showing up"**
- Wait 5-10 minutes for Discord to sync
- Try `/` in a channel the bot can access
- Restart bot: `Ctrl+C` then re-run

**"Interaction failed"**
- Check ML and Backend APIs are running
- Verify .env has correct API URLs
- Look for error messages in bot console

---

## 💡 Pro Tips

### Reddit
1. **Timing**: Peak hours are 6-10 PM EST
2. **Match threads**: Post predictions in pre-match threads
3. **Accuracy tracker**: Weekly post showing success rate
4. **Flair**: Get custom flair on r/soccer (message mods)

### Discord
1. **Custom status**: Show current match count
2. **Reaction roles**: Let users subscribe to predictions
3. **Auto-post**: Daily predictions in #predictions channel
4. **Leaderboard**: Track most accurate predictions

### Both
1. **Acknowledge errors**: If prediction is way off, explain why
2. **Update regularly**: Add new features based on feedback
3. **Community input**: Ask what stats users want to see
4. **Responsible gambling**: Always include disclaimers

---

## 📝 Legal & Compliance

### Reddit
- Follow [Reddit's Bot Guidelines](https://www.reddit.com/wiki/bottiquette)
- Include disclaimer in every post
- Don't manipulate votes
- Respect subreddit rules

### Discord
- Follow [Discord's Terms of Service](https://discord.com/terms)
- Don't scrape user data
- Respect user privacy
- Don't spam servers

### Gambling
- Include "Gamble Responsibly" in all posts
- Link to gambling help resources if applicable
- Don't encourage excessive betting
- Clearly state predictions are for entertainment

---

## 🎯 Next Steps

1. ✅ Set up Reddit bot
2. ✅ Set up Discord bot
3. ✅ Test both in development
4. ✅ Join 2-3 football communities
5. ✅ Monitor engagement for 1 week
6. ✅ Iterate based on feedback
7. ✅ Scale to more communities

Happy botting! 🤖⚽
