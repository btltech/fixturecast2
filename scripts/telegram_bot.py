#!/usr/bin/env python3
"""
FixtureCast Telegram Bot
Provides AI predictions in Telegram

Features:
- Commands: /predict, /today, /motd, /help
- Interactive buttons and inline queries
- Links to full analysis on website

Requirements:
    pip install python-telegram-bot python-dotenv requests

Setup:
1. Create bot with @BotFather on Telegram
2. Get bot token and add to .env
3. Start the bot
"""

import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ParseMode
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    print("❌ python-telegram-bot not installed. Run: pip install python-telegram-bot")
    sys.exit(1)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.com")


def get_todays_fixtures():
    """Fetch today's fixtures"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/api/fixtures/today", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", []), data.get("match_of_the_day")
    except Exception as e:
        print(f"❌ Error fetching fixtures: {e}")
        return [], None


def search_match(team1, team2=None):
    """Search for a match"""
    fixtures, _ = get_todays_fixtures()

    if not fixtures:
        return None

    team1_lower = team1.lower().strip()

    if team2:
        team2_lower = team2.lower().strip()
        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            if (team1_lower in home and team2_lower in away) or (
                team2_lower in home and team1_lower in away
            ):
                return fixture
    else:
        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            if team1_lower in home or team1_lower in away:
                return fixture

    return None


def get_prediction(fixture_id, league_id):
    """Get AI prediction"""
    try:
        fid = int(str(fixture_id).strip())
        lid = int(str(league_id).strip())
        url = f"{ML_API_URL}/api/prediction/{fid}?league={lid}"
        print(f"DEBUG: Fetching prediction from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting prediction: {e}")
        return None


def format_prediction_message(fixture, prediction_data):
    """Format prediction as Telegram message"""
    home_team = fixture["teams"]["home"]["name"]
    away_team = fixture["teams"]["away"]["name"]
    league = fixture["league"]["name"]
    kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))

    message = f"🔮 <b>FixtureCast AI Prediction</b>\n\n"
    message += f"<b>{home_team} vs {away_team}</b>\n"
    message += f"📅 {kick_off.strftime('%B %d at %H:%M UTC')}\n"
    message += f"🏆 {league}\n\n"

    if prediction_data and "prediction" in prediction_data:
        pred = prediction_data["prediction"]
        home_prob = pred.get("home_win_prob", 0) * 100
        draw_prob = pred.get("draw_prob", 0) * 100
        away_prob = pred.get("away_win_prob", 0) * 100
        scoreline = pred.get("predicted_scoreline", "N/A")
        btts = pred.get("btts_prob", 0) * 100
        over25 = pred.get("over25_prob", 0) * 100

        # Confidence
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 65:
            confidence = "🟢 High Confidence"
        elif max_prob > 50:
            confidence = "🟡 Medium Confidence"
        else:
            confidence = "🔴 Close Match"

        message += f"<b>📊 Win Probabilities</b>\n"
        message += f"• {home_team}: <b>{home_prob:.1f}%</b>\n"
        message += f"• Draw: <b>{draw_prob:.1f}%</b>\n"
        message += f"• {away_team}: <b>{away_prob:.1f}%</b>\n\n"

        message += f"<b>🎯 Predicted Score:</b> {scoreline}\n"
        message += f"<b>{confidence}</b>\n\n"

        message += f"<b>💰 Betting Markets</b>\n"
        message += f"• BTTS: {btts:.0f}%\n"
        message += f"• Over 2.5: {over25:.0f}%\n\n"

    message += f"<i>Powered by 8-Model AI Ensemble</i>"

    return message


def create_prediction_keyboard(fixture):
    """Create inline keyboard with link to full analysis"""
    fixture_id = fixture["fixture"]["id"]
    league_id = fixture["league"]["id"]
    keyboard = [
        [
            InlineKeyboardButton(
                "📱 View Full Analysis",
                url=f"{APP_URL}/prediction/{fixture_id}?league={league_id}",
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    message = (
        "⚽ <b>Welcome to FixtureCast!</b>\n\n"
        "Get AI-powered football match predictions instantly.\n\n"
        "<b>Available Commands:</b>\n"
        "/predict [team] - Get prediction for a match\n"
        "/today - View all matches today\n"
        "/motd - Match of the Day prediction\n"
        "/help - Show this message\n\n"
        f"🌐 Visit <a href='{APP_URL}'>{APP_URL}</a>"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    message = (
        "🤖 <b>FixtureCast Commands</b>\n\n"
        "<b>/predict [team1] [team2]</b>\n"
        "Get AI prediction for a specific match\n"
        "Example: <code>/predict Arsenal Chelsea</code>\n\n"
        "<b>/today</b>\n"
        "View all matches scheduled for today\n\n"
        "<b>/motd</b>\n"
        "Get prediction for today's Match of the Day\n\n"
        f"🌐 <a href='{APP_URL}'>Visit FixtureCast</a>"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Predict command"""
    args = context.args

    if not args:
        await update.message.reply_text(
            "Please specify team(s).\nExample: <code>/predict Arsenal Chelsea</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Parse team names
    if "vs" in " ".join(args).lower():
        teams = " ".join(args).lower().split("vs")
        team1 = teams[0].strip()
        team2 = teams[1].strip() if len(teams) > 1 else None
    else:
        team1 = args[0]
        team2 = args[1] if len(args) > 1 else None

    # Search for match
    await update.message.reply_text("🔍 Searching for match...")
    fixture = search_match(team1, team2)

    if not fixture:
        if team2:
            msg = f"❌ Could not find a match between <b>{team1}</b> and <b>{team2}</b> scheduled for today."
        else:
            msg = f"❌ Could not find a match for <b>{team1}</b> scheduled for today."
        msg += f"\n\nCheck all fixtures at {APP_URL}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # Get prediction
    fixture_id = fixture["fixture"]["id"]
    league_id = fixture["league"]["id"]
    prediction_data = get_prediction(fixture_id, league_id)

    # Format and send
    message = format_prediction_message(fixture, prediction_data)
    keyboard = create_prediction_keyboard(fixture)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    print(
        f"  ✅ Sent prediction for {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
    )
    print(f"     Requested by: {update.effective_user.username or update.effective_user.id}")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today command"""
    await update.message.reply_text("📅 Fetching today's matches...")

    fixtures, match_of_the_day = get_todays_fixtures()

    if not fixtures:
        await update.message.reply_text("📭 No matches scheduled for today.")
        return

    message = f"📅 <b>Today's Matches</b>\n\n"
    message += f"<b>{len(fixtures)} matches</b> scheduled across all leagues\n\n"

    # Group by league
    by_league = {}
    for fixture in fixtures[:20]:  # Limit to 20
        league_name = fixture["league"]["name"]
        if league_name not in by_league:
            by_league[league_name] = []
        by_league[league_name].append(fixture)

    # Add matches by league
    for league_name, league_fixtures in by_league.items():
        message += f"🏆 <b>{league_name}</b>\n"
        for fixture in league_fixtures[:5]:  # Max 5 per league
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
            time_str = kick_off.strftime("%H:%M")
            message += f"• {home} vs {away} ({time_str})\n"
        message += "\n"

    message += f"💡 Use /predict [team] to get predictions"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def motd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Match of the Day command"""
    await update.message.reply_text("⭐ Fetching Match of the Day...")

    _, match_of_the_day = get_todays_fixtures()

    if not match_of_the_day:
        await update.message.reply_text("📭 No Match of the Day available.")
        return

    # Get prediction
    fixture_id = match_of_the_day["fixture"]["id"]
    league_id = match_of_the_day["league"]["id"]
    prediction_data = get_prediction(fixture_id, league_id)

    # Format and send
    message = "⭐ <b>MATCH OF THE DAY</b> ⭐\n\n"
    message += format_prediction_message(match_of_the_day, prediction_data)
    keyboard = create_prediction_keyboard(match_of_the_day)

    await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def main():
    """Main execution"""
    print("=" * 60)
    print("FixtureCast Telegram Bot")
    print("=" * 60)

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    # Check APIs
    try:
        backend_health = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        if backend_health.status_code == 200:
            print("✅ Backend API is reachable")
    except Exception as e:
        print(f"❌ Backend API not reachable: {e}")
        sys.exit(1)

    try:
        ml_health = requests.get(f"{ML_API_URL}/health", timeout=5)
        if ml_health.status_code == 200:
            print("✅ ML API is reachable")
    except Exception as e:
        print(f"❌ ML API not reachable: {e}")
        sys.exit(1)

    print("\n🚀 Starting Telegram bot...\n")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("motd", motd))

    # Start bot
    print("✅ Bot is now running!")
    print("📱 Search for your bot on Telegram and send /start\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
