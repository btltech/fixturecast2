#!/usr/bin/env python3
"""
FixtureCast Reddit Bot
Monitors r/soccer and responds to prediction requests

Features:
- Watches for mentions like "!fixturecast Arsenal vs Chelsea"
- Posts formatted predictions with probabilities
- Includes link to full analysis
- Respects Reddit rate limits

Requirements:
    pip install praw python-dotenv requests

Setup:
1. Create Reddit app at https://www.reddit.com/prefs/apps
2. Get Client ID, Client Secret, and set redirect URI
3. Create .env file with credentials
"""

import os
import re
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

try:
    import praw
except ImportError:
    print("❌ praw not installed. Run: pip install praw python-dotenv")
    sys.exit(1)

# Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "FixtureCast Bot v1.0")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.com")

# Subreddits to monitor
SUBREDDITS = [
    "soccer",
    "football",
    "PremierLeague",
    "realmadrid",
    "Barca",
    "LiverpoolFC",
    "Gunners",
]

# Track processed comments to avoid duplicates
PROCESSED_FILE = "data/reddit_processed.txt"


def init_reddit_client():
    """Initialize Reddit API client"""
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
        print("❌ Missing Reddit credentials. Check your .env file.")
        return None

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
        )
        # Test authentication
        reddit.user.me()
        print(f"✅ Authenticated as u/{reddit.user.me()}")
        return reddit
    except Exception as e:
        print(f"❌ Reddit authentication failed: {e}")
        return None


def load_processed_comments():
    """Load list of already processed comment IDs"""
    try:
        os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
        with open(PROCESSED_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()


def save_processed_comment(comment_id):
    """Save a processed comment ID"""
    with open(PROCESSED_FILE, "a") as f:
        f.write(f"{comment_id}\n")


def search_match_in_fixtures(team1, team2):
    """Search for a match between two teams in today's fixtures"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/api/fixtures/today", timeout=10)
        response.raise_for_status()
        data = response.json()

        fixtures = data.get("response", [])

        # Normalize team names for matching
        team1_lower = team1.lower().strip()
        team2_lower = team2.lower().strip()

        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            # Check if both teams match (in either order)
            if (
                (team1_lower in home and team2_lower in away)
                or (team2_lower in home and team1_lower in away)
                or (team1_lower in away and team2_lower in home)
                or (team2_lower in away and team1_lower in home)
            ):
                return fixture

        return None
    except Exception as e:
        print(f"⚠️  Error searching fixtures: {e}")
        return None


def get_prediction(fixture_id, league_id):
    """Get AI prediction for a fixture"""
    try:
        response = requests.get(
            f"{ML_API_URL}/api/prediction/{fixture_id}?league={league_id}", timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Error getting prediction: {e}")
        return None


def format_prediction_reply(fixture, prediction_data):
    """Format prediction as Reddit comment"""
    home_team = fixture["teams"]["home"]["name"]
    away_team = fixture["teams"]["away"]["name"]
    league = fixture["league"]["name"]
    kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
    time_str = kick_off.strftime("%B %d, %Y at %H:%M UTC")

    reply = f"## 🔮 FixtureCast AI Prediction\n\n"
    reply += f"**{home_team} vs {away_team}**  \n"
    reply += f"📅 {time_str}  \n"
    reply += f"🏆 {league}\n\n"

    if prediction_data and "prediction" in prediction_data:
        pred = prediction_data["prediction"]
        home_prob = pred.get("home_win_prob", 0) * 100
        draw_prob = pred.get("draw_prob", 0) * 100
        away_prob = pred.get("away_win_prob", 0) * 100
        scoreline = pred.get("predicted_scoreline", "N/A")
        btts = pred.get("btts_prob", 0) * 100
        over25 = pred.get("over25_prob", 0) * 100

        reply += "### 📊 Win Probabilities\n\n"
        reply += f"| Outcome | Probability |\n"
        reply += f"|---------|-------------|\n"
        reply += f"| {home_team} Win | **{home_prob:.1f}%** |\n"
        reply += f"| Draw | **{draw_prob:.1f}%** |\n"
        reply += f"| {away_team} Win | **{away_prob:.1f}%** |\n\n"

        reply += f"**Predicted Score:** {scoreline}\n\n"

        # Confidence indicator
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 65:
            confidence = "🟢 High Confidence"
        elif max_prob > 50:
            confidence = "🟡 Medium Confidence"
        else:
            confidence = "🔴 Close Match"
        reply += f"**{confidence}**\n\n"

        reply += "### 🎯 Betting Markets\n\n"
        reply += f"- **Both Teams to Score (BTTS):** {btts:.0f}%\n"
        reply += f"- **Over 2.5 Goals:** {over25:.0f}%\n\n"

    # Add link
    fixture_id = fixture["fixture"]["id"]
    league_id = fixture["league"]["id"]
    reply += f"[📱 View Full AI Analysis & Detailed Stats]({APP_URL}/prediction/{fixture_id}?league={league_id})\n\n"

    reply += "---\n\n"
    reply += "*I'm an AI-powered bot from [FixtureCast](" + APP_URL + "). "
    reply += "Predictions are generated using an 8-model ensemble trained on 5 seasons of data. "
    reply += "Use for entertainment purposes only. Gamble responsibly.*"

    return reply


def process_comment(comment, reddit):
    """Process a single comment"""
    try:
        text = comment.body.lower()

        # Check for trigger phrases
        triggers = [
            r"!fixturecast\s+(.+?)\s+vs?\s+(.+)",
            r"@fixturecast\s+(.+?)\s+vs?\s+(.+)",
            r"u/fixturecast\s+(.+?)\s+vs?\s+(.+)",
        ]

        match = None
        for pattern in triggers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                break

        if not match:
            return False

        team1 = match.group(1).strip()
        team2 = match.group(2).strip()

        print(f"  📝 Request: {team1} vs {team2}")
        print(f"     From: u/{comment.author} in r/{comment.subreddit}")

        # Search for match
        fixture = search_match_in_fixtures(team1, team2)

        if not fixture:
            # No match found
            reply = f"Sorry, I couldn't find a match between **{team1}** and **{team2}** scheduled for today.\n\n"
            reply += f"Check all of today's fixtures at [{APP_URL}]({APP_URL})"
            comment.reply(reply)
            print("  ❌ Match not found")
            return True

        # Get prediction
        fixture_id = fixture["fixture"]["id"]
        league_id = fixture["league"]["id"]
        prediction_data = get_prediction(fixture_id, league_id)

        # Format and post reply
        reply_text = format_prediction_reply(fixture, prediction_data)
        comment.reply(reply_text)

        print(
            f"  ✅ Posted prediction for {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
        )
        return True

    except praw.exceptions.APIException as e:
        if "RATELIMIT" in str(e):
            print(f"  ⏳ Rate limited. Waiting...")
            time.sleep(60)
        else:
            print(f"  ❌ Reddit API error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error processing comment: {e}")
        return False


def monitor_subreddits(reddit):
    """Monitor subreddits for prediction requests"""
    print(f"\n👀 Monitoring: {', '.join([f'r/{s}' for s in SUBREDDITS])}")
    print("Listening for: !fixturecast Team1 vs Team2\n")

    processed = load_processed_comments()
    subreddit_str = "+".join(SUBREDDITS)

    try:
        subreddit = reddit.subreddit(subreddit_str)

        # Stream comments in real-time
        for comment in subreddit.stream.comments(skip_existing=True):
            try:
                # Skip if already processed
                if comment.id in processed:
                    continue

                # Skip if comment is from the bot itself
                if comment.author == reddit.user.me():
                    continue

                # Check if comment mentions the bot
                text = comment.body.lower()
                if "!fixturecast" in text or "@fixturecast" in text or "u/fixturecast" in text:
                    processed = process_comment(comment, reddit)

                    if processed:
                        processed.add(comment.id)
                        save_processed_comment(comment.id)
                        # Rate limiting (avoid spam)
                        time.sleep(5)

            except Exception as e:
                print(f"⚠️  Error in stream: {e}")
                time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise


def main():
    """Main execution"""
    print("=" * 60)
    print("FixtureCast Reddit Bot")
    print("=" * 60)

    # Check APIs
    try:
        backend_health = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        if backend_health.status_code == 200:
            print("✅ Backend API is reachable")
        else:
            print(f"⚠️  Backend API returned {backend_health.status_code}")
    except Exception as e:
        print(f"❌ Backend API not reachable: {e}")
        sys.exit(1)

    try:
        ml_health = requests.get(f"{ML_API_URL}/health", timeout=5)
        if ml_health.status_code == 200:
            print("✅ ML API is reachable")
        else:
            print(f"⚠️  ML API returned {ml_health.status_code}")
    except Exception as e:
        print(f"❌ ML API not reachable: {e}")
        sys.exit(1)

    # Initialize Reddit
    reddit = init_reddit_client()
    if not reddit:
        sys.exit(1)

    # Start monitoring
    print("\n🤖 Bot is now live!\n")
    monitor_subreddits(reddit)


if __name__ == "__main__":
    main()
