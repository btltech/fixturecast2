#!/usr/bin/env python3
"""
FixtureCast Twitter Bot
Automatically posts daily prediction threads to Twitter/X

Features:
- Posts a morning thread with top predictions
- Includes match details, probabilities, and link to app
- Runs on a schedule (cron job or systemd timer)

Requirements:
    pip install tweepy python-dotenv

Setup:
1. Create a Twitter Developer account
2. Create an app and get API keys
3. Create a .env file with:
    TWITTER_API_KEY=your_api_key
    TWITTER_API_SECRET=your_api_secret
    TWITTER_BEARER_TOKEN=your_bearer
    TWITTER_ACCESS_TOKEN=your_access_token
    TWITTER_ACCESS_SECRET=your_access_secret
    APP_URL=https://yourdomain.com
    ML_API_URL=http://localhost:8000
"""

import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitter API v2 setup
try:
    import tweepy
except ImportError:
    print("❌ tweepy not installed. Run: pip install tweepy python-dotenv")
    sys.exit(1)

# Configuration
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.app")

# Twitter credentials
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")


def init_twitter_client():
    """Initialize Twitter API v2 client"""
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
        print("❌ Missing Twitter API credentials. Check your .env file.")
        return None

    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
    )
    return client


def get_todays_fixtures():
    """Fetch today's fixtures from backend"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/api/fixtures/today", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", []), data.get("match_of_the_day")
    except Exception as e:
        print(f"❌ Error fetching fixtures: {e}")
        return [], None


def get_prediction(fixture_id, league_id):
    """Get AI prediction for a specific fixture"""
    try:
        response = requests.get(
            f"{ML_API_URL}/api/prediction/{fixture_id}?league={league_id}", timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Couldn't get prediction for fixture {fixture_id}: {e}")
        return None


def format_match_tweet(match, prediction_data=None, is_motd=False):
    """Format a single match into a tweet"""
    home_team = match["teams"]["home"]["name"]
    away_team = match["teams"]["away"]["name"]
    league = match["league"]["name"]
    kick_off = datetime.fromisoformat(match["fixture"]["date"].replace("Z", "+00:00"))
    time_str = kick_off.strftime("%H:%M")

    # League emoji mapping
    league_emoji = {
        "Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "La Liga": "🇪🇸",
        "Serie A": "🇮🇹",
        "Bundesliga": "🇩🇪",
        "Ligue 1": "🇫🇷",
        "Champions League": "⭐",
        "Europa League": "🏆",
    }.get(league, "⚽")

    # Base tweet
    tweet = f"{league_emoji} {home_team} vs {away_team}\n"
    tweet += f"⏰ {time_str}\n"

    if prediction_data and "prediction" in prediction_data:
        pred = prediction_data["prediction"]
        home_prob = pred.get("home_win_prob", 0) * 100
        draw_prob = pred.get("draw_prob", 0) * 100
        away_prob = pred.get("away_win_prob", 0) * 100
        scoreline = pred.get("predicted_scoreline", "N/A")

        tweet += f"\n🔮 AI Prediction: {scoreline}\n"
        tweet += f"📊 {home_team[:10]} {home_prob:.0f}% | Draw {draw_prob:.0f}% | {away_team[:10]} {away_prob:.0f}%\n"

        # Add confidence indicator
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 65:
            tweet += "🟢 High Confidence\n"
        elif max_prob > 50:
            tweet += "🟡 Medium Confidence\n"
        else:
            tweet += "🔴 Close Match\n"

    if is_motd:
        tweet = "⭐ MATCH OF THE DAY ⭐\n\n" + tweet

    # Add link to full prediction
    fixture_id = match["fixture"]["id"]
    league_id = match["league"]["id"]
    tweet += f"\n🔗 Full Analysis: {APP_URL}/prediction/{fixture_id}?league={league_id}"

    return tweet


def create_prediction_thread():
    """Generate and post a Twitter thread with today's top predictions"""
    client = init_twitter_client()
    if not client:
        return False

    print("🔄 Fetching today's fixtures...")
    fixtures, match_of_the_day = get_todays_fixtures()

    if not fixtures:
        print("ℹ️  No fixtures today. Skipping post.")
        return False

    # Get top 3 fixtures (MOTD + next 2 biggest)
    top_fixtures = []
    if match_of_the_day:
        top_fixtures.append((match_of_the_day, True))  # (match, is_motd)

    # Add next 2 matches (skip MOTD if already added)
    motd_id = match_of_the_day["fixture"]["id"] if match_of_the_day else None
    for fixture in fixtures[:5]:
        if len(top_fixtures) >= 3:
            break
        if fixture["fixture"]["id"] != motd_id:
            top_fixtures.append((fixture, False))

    if not top_fixtures:
        print("ℹ️  No suitable matches found.")
        return False

    # Create thread
    tweets = []
    today_str = datetime.now().strftime("%B %d, %Y")

    # Opening tweet
    opening_tweet = f"""🔮 FixtureCast Daily Predictions - {today_str}

AI-powered match analysis for today's top fixtures 👇

{len(fixtures)} matches analyzed
#Football #Predictions #AI"""
    tweets.append(opening_tweet)

    # Individual match tweets
    for i, (match, is_motd) in enumerate(top_fixtures, 1):
        print(
            f"  → Processing match {i}/{len(top_fixtures)}: {match['teams']['home']['name']} vs {match['teams']['away']['name']}"
        )

        # Get prediction
        fixture_id = match["fixture"]["id"]
        league_id = match["league"]["id"]
        prediction_data = get_prediction(fixture_id, league_id)

        match_tweet = format_match_tweet(match, prediction_data, is_motd)
        tweets.append(match_tweet)

    # Closing tweet
    closing_tweet = f"""📱 Get predictions for ALL of today's matches:
{APP_URL}

✨ Features:
• 8-model AI ensemble
• Live probabilities
• Detailed analysis
• FREE to use!

#PremierLeague #LaLiga #SerieA #Bundesliga"""
    tweets.append(closing_tweet)

    # Post thread
    print(f"\n📤 Posting thread ({len(tweets)} tweets)...")
    try:
        previous_tweet_id = None
        for i, tweet_text in enumerate(tweets, 1):
            print(f"  Tweet {i}/{len(tweets)}: {tweet_text[:50]}...")

            if previous_tweet_id:
                # Reply to previous tweet
                response = client.create_tweet(
                    text=tweet_text, in_reply_to_tweet_id=previous_tweet_id
                )
            else:
                # First tweet in thread
                response = client.create_tweet(text=tweet_text)

            previous_tweet_id = response.data["id"]
            print(f"  ✅ Posted tweet {i}")

        print(f"\n✅ Successfully posted thread!")
        print(f"   View at: https://twitter.com/i/web/status/{previous_tweet_id}")
        return True

    except Exception as e:
        print(f"\n❌ Error posting thread: {e}")
        return False


def main():
    """Main execution"""
    print("=" * 60)
    print("FixtureCast Twitter Bot")
    print("=" * 60)

    # Check if APIs are running
    try:
        backend_health = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        if backend_health.status_code != 200:
            print(f"⚠️  Backend API not healthy: {backend_health.status_code}")
    except Exception as e:
        print(f"❌ Backend API not reachable: {e}")
        print(f"   Make sure the backend is running at {BACKEND_API_URL}")
        sys.exit(1)

    try:
        ml_health = requests.get(f"{ML_API_URL}/health", timeout=5)
        if ml_health.status_code != 200:
            print(f"⚠️  ML API not healthy: {ml_health.status_code}")
    except Exception as e:
        print(f"❌ ML API not reachable: {e}")
        print(f"   Make sure the ML API is running at {ML_API_URL}")
        sys.exit(1)

    # Create and post thread
    success = create_prediction_thread()

    if success:
        print("\n🎉 Thread posted successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Thread posting failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
