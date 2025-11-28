# FixtureCast Social Media Bots - Quick Reference

## 🤖 All Three Bots at a Glance

| Platform | Script | Trigger | Response Type | Best For |
|----------|--------|---------|---------------|----------|
| **Twitter** | `twitter_bot.py` | Scheduled (daily 8 AM) | Thread with top 3 matches | Brand building, daily engagement |
| **Reddit** | `reddit_bot.py` | `!fixturecast Team1 vs Team2` | Formatted comment | Community help, organic growth |
| **Discord** | `discord_bot.py` | `/predict Team1 Team2` | Rich embed | Real-time requests, server engagement |

---

## 📦 Installation (One-Time Setup)

```bash
# Install all bot dependencies
pip install tweepy praw discord.py python-dotenv requests

# Or from requirements.txt
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
nano .env  # Add your API credentials
```

---

## 🚀 Running the Bots

### Start All Bots (Recommended)
```bash
# Terminal 1: Backend API
python backend/main.py

# Terminal 2: ML API
python backend/ml_api.py

# Terminal 3: Twitter Bot (daily post)
python scripts/twitter_bot.py

# Terminal 4: Reddit Bot (always listening)
python scripts/reddit_bot.py

# Terminal 5: Discord Bot (always listening)
python scripts/discord_bot.py
```

### Start Individual Bots
```bash
# Twitter only (for testing/manual run)
python scripts/twitter_bot.py

# Reddit only
python scripts/reddit_bot.py

# Discord only
python scripts/discord_bot.py
```

---

## 🎯 Usage Examples

### Twitter Bot
**Automatically posts every morning:**

<parameter name="CodeContent"># FixtureCast Social Media Bots - Quick Reference

## 🤖 All Three Bots at a Glance

| Platform | Script | Trigger | Response Type | Best For |
|----------|--------|---------|---------------|----------|
| **Twitter** | `twitter_bot.py` | Scheduled (daily 8 AM) | Thread with top 3 matches | Brand building, daily engagement |
| **Reddit** | `reddit_bot.py` | `!fixturecast Team1 vs Team2` | Formatted comment | Community help, organic growth |
| **Discord** | `discord_bot.py` | `/predict Team1 Team2` | Rich embed | Real-time requests, server engagement |

---

## 📦 Installation (One-Time Setup)

```bash
# Install all bot dependencies
pip install tweepy praw discord.py python-dotenv requests

# Or from requirements.txt
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
nano .env  # Add your API credentials
```

---

## 🚀 Running the Bots

### Start All Bots (Recommended)
```bash
# Terminal 1: Backend API
python backend/main.py

# Terminal 2: ML API
python backend/ml_api.py

# Terminal 3: Twitter Bot (daily post)
python scripts/twitter_bot.py

# Terminal 4: Reddit Bot (always listening)
python scripts/reddit_bot.py

# Terminal 5: Discord Bot (always listening)
python scripts/discord_bot.py
```

### Start Individual Bots
```bash
# Twitter only (for testing/manual run)
python scripts/twitter_bot.py

# Reddit only
python scripts/reddit_bot.py

# Discord only
python scripts/discord_bot.py
```

---

## 🎯 Usage Examples

### Twitter Bot
**Automatically posts every morning:**
```
🔮 FixtureCast Daily Predictions - Nov 28, 2024

⭐ MATCH OF THE DAY
🏴 Arsenal vs Chelsea
🔮 AI Prediction: 2-1
📊 Arsenal 58% | Draw 24% | Chelsea 18%

[View thread on Twitter...]
```

**To automate:**
```bash
# Add to crontab
0 8 * * * cd /path/to/fixturecast && python3 scripts/twitter_bot.py
```

### Reddit Bot
**User posts on r/soccer:**
```
!fixturecast Arsenal vs Chelsea
```

**Bot replies:**
```
## 🔮 FixtureCast AI Prediction
**Arsenal vs Chelsea**
📅 November 28, 2024 at 17:30 UTC
🏆 Premier League

### 📊 Win Probabilities
| Arsenal Win | **58.3%** |
| Draw | **24.1%** |
| Chelsea Win | **17.6%** |

[Full Analysis](https://fixturecast.app/...)
```

**Monitored subreddits:**
- r/soccer
- r/football
- r/PremierLeague
- r/LiverpoolFC
- r/Gunners
- r/realmadrid
- r/Barca

### Discord Bot
**User types in Discord:**
```
/predict Arsenal Chelsea
```

**Bot sends rich embed with:**
- Team logos
- Color-coded probabilities
- Predicted score
- Confidence level
- BTTS & Over 2.5 stats
- Link to full analysis

**Other commands:**
- `/today` - All matches today
- `/motd` - Match of the Day
- `/help` - Show all commands

---

## 📊 Growth Strategy

### Week 1: Foundation
- ✅ Set up all 3 bots
- ✅ Test in small communities
- ✅ Monitor for errors

### Week 2-4: Expand
- **Twitter**: Post daily, engage with replies
- **Reddit**: Join 5-10 football subreddits
- **Discord**: Join 10-15 football servers

### Month 2+: Scale
- **Twitter**: Experiment with posting times
- **Reddit**: Respond to match threads
- **Discord**: Auto-post predictions daily

### Metrics to Track
| Platform | Week 1 Target | Month 1 Target | Month 3 Target |
|----------|---------------|----------------|----------------|
| **Twitter** | 50 impressions | 500 impressions | 5,000 impressions |
| **Reddit** | 5 responses | 50 responses | 200 responses |
| **Discord** | 3 servers | 15 servers | 50+ servers |

---

## 🛡️ Safety & Best Practices

### Rate Limiting
- **Twitter**: Max 50 tweets/day (free tier)
- **Reddit**: Wait 5-10 seconds between posts
- **Discord**: No hard limit, but don't spam

### Content Guidelines
✅ **DO:**
- Include responsible gambling disclaimers
- Respond quickly to requests
- Thank users for feedback
- Fix bugs promptly
- Engage authentically

❌ **DON'T:**
- Spam unrequested predictions
- Manipulate votes/engagement
- Scrape user data
- Circumvent rate limits
- Self-promote excessively

### Moderation
- **Reddit**: Contact subreddit mods before posting extensively
- **Discord**: Ask server admins before joining if invite-only
- **Twitter**: Follow Twitter's automation rules

---

## 🐛 Troubleshooting

### All Bots: "API not reachable"
```bash
# Check if APIs are running
curl http://localhost:8001/health  # Backend
curl http://localhost:8000/health  # ML API

# Restart if needed
python backend/main.py &
python backend/ml_api.py &
```

### Twitter: "Rate limit exceeded"
- Normal for free tier
- Reduce posting frequency
- Consider Twitter API Pro ($100/month)

### Reddit: "Invalid credentials"
- Double-check .env file
- Ensure Reddit app type is "script"
- Verify username/password

### Discord: "Commands not syncing"
- Wait 5-10 minutes
- Restart bot
- Check "applications.commands" scope

---

## 📁 File Structure

```
fixturecast/
├── scripts/
│   ├── twitter_bot.py      # Scheduled daily posts
│   ├── reddit_bot.py        # Always listening
│   └── discord_bot.py       # Slash commands
├── .env                     # Your credentials (create from .env.example)
├── .env.example             # Template
├── TWITTER_BOT_SETUP.md     # Twitter guide
├── REDDIT_DISCORD_BOT_SETUP.md  # Reddit/Discord guide
└── BOT_QUICK_REFERENCE.md   # This file
```

---

## 📚 Detailed Setup Guides

- **Twitter Bot**: See `TWITTER_BOT_SETUP.md`
- **Reddit/Discord Bots**: See `REDDIT_DISCORD_BOT_SETUP.md`

---

## 🎉 Success Checklist

Before going live:
- [ ] All APIs running
- [ ] .env configured with credentials
- [ ] Bots tested in dev/private communities
- [ ] Disclaimers added to all posts
- [ ] Error logging set up
- [ ] Monitoring dashboard (optional)

Growth milestones:
- [ ] First 100 Twitter followers
- [ ] First upvoted Reddit comment
- [ ] First Discord server with 100+ members
- [ ] 1,000 total bot interactions
- [ ] Featured in a football news article

---

**Need help?** Check the detailed setup guides or create an issue on GitHub.

**Ready to launch?** Start with Twitter (easiest), then Reddit, then Discord. Good luck! 🚀
