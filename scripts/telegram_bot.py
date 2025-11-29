#!/usr/bin/env python3
"""
FixtureCast Telegram Bot
Provides AI predictions in Telegram

Features:
- Commands: /predict, /today, /motd, /help, /status
- Interactive buttons and inline queries
- Links to full analysis on website
- AUTOMATED DAILY PREDICTIONS: Posts Match of the Day at scheduled times
- HEALTH MONITORING: Auto-reconnect and error recovery
- WEEKLY SUMMARIES: Posts prediction accuracy on Sundays

Requirements:
    pip install python-telegram-bot python-dotenv requests apscheduler

Setup:
1. Create bot with @BotFather on Telegram
2. Get bot token and add to .env
3. Start the bot
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime, time, timedelta

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

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    print("⚠️ apscheduler not installed. Scheduled tasks will be disabled.")
    AsyncIOScheduler = None

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.com")

# Scheduled posting channels (comma-separated chat IDs)
DAILY_PREDICTION_CHANNELS = os.getenv("TELEGRAM_DAILY_CHANNELS", "").split(",")
DAILY_PREDICTION_CHANNELS = [c.strip() for c in DAILY_PREDICTION_CHANNELS if c.strip()]

# Bot statistics
start_time = None
predictions_sent = 0
errors_count = 0
last_health_check = None
consecutive_failures = 0


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
        "<b>/status</b>\n"
        "Check bot health and statistics\n\n"
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


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command - shows bot health and stats"""
    global start_time, predictions_sent, errors_count, last_health_check

    # Calculate uptime
    if start_time:
        uptime = datetime.utcnow() - start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
    else:
        uptime_str = "Unknown"

    # Check API health
    backend_ok = False
    ml_ok = False

    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        backend_ok = response.status_code == 200
    except Exception:
        pass

    try:
        response = requests.get(f"{ML_API_URL}/health", timeout=5)
        ml_ok = response.status_code == 200
    except Exception:
        pass

    status_emoji = "✅" if (backend_ok and ml_ok) else "⚠️"

    message = f"{status_emoji} <b>FixtureCast Bot Status</b>\n\n"
    message += f"⏱️ <b>Uptime:</b> {uptime_str}\n"
    message += f"📊 <b>Predictions sent:</b> {predictions_sent}\n"
    message += f"❌ <b>Errors:</b> {errors_count}\n\n"
    message += f"🔌 <b>API Status</b>\n"
    message += f"• Backend: {'✅' if backend_ok else '❌'}\n"
    message += f"• ML API: {'✅' if ml_ok else '❌'}\n\n"

    if last_health_check:
        message += f"🩺 <b>Last check:</b> {last_health_check.strftime('%H:%M:%S UTC')}\n"

    message += f"\n<i>Health monitoring active</i>"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


def main():
    """Main execution"""
    global start_time, predictions_sent, errors_count

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
        print(f"⚠️ Backend API not reachable: {e}")
        print("   Bot will start anyway and retry connection later.")

    try:
        ml_health = requests.get(f"{ML_API_URL}/health", timeout=5)
        if ml_health.status_code == 200:
            print("✅ ML API is reachable")
    except Exception as e:
        print(f"⚠️ ML API not reachable: {e}")
        print("   Bot will start anyway and retry connection later.")

    print("\n🚀 Starting Telegram bot...\n")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("motd", motd))
    application.add_handler(CommandHandler("status", status))

    # Set start time for uptime tracking
    start_time = datetime.utcnow()

    # Setup scheduled tasks
    if AsyncIOScheduler and DAILY_PREDICTION_CHANNELS:
        scheduler = AsyncIOScheduler()

        # Daily MOTD at 8 AM and 2 PM UTC
        scheduler.add_job(
            post_scheduled_motd,
            CronTrigger(hour=8, minute=0),
            args=[application],
            id="morning_motd",
        )
        scheduler.add_job(
            post_scheduled_motd,
            CronTrigger(hour=14, minute=0),
            args=[application],
            id="afternoon_motd",
        )

        # Weekly summary on Sunday at 8 PM UTC
        scheduler.add_job(
            post_weekly_summary,
            CronTrigger(day_of_week="sun", hour=20, minute=0),
            args=[application],
            id="weekly_summary",
        )

        # Health check every 5 minutes
        scheduler.add_job(health_check, "interval", minutes=5, id="health_check")

        scheduler.start()
        print("✅ Scheduled tasks started")
        print("   - Daily MOTD: 8:00 AM & 2:00 PM UTC")
        print("   - Weekly summary: Sunday 8:00 PM UTC")
        print("   - Health check: Every 5 minutes")
    elif not DAILY_PREDICTION_CHANNELS:
        print("⚠️ No TELEGRAM_DAILY_CHANNELS configured - scheduled posts disabled")
    else:
        print("⚠️ APScheduler not installed - scheduled posts disabled")

    # Start bot
    print("\n✅ Bot is now running!")
    print("📱 Search for your bot on Telegram and send /start\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def post_scheduled_motd(application):
    """Post Match of the Day to all configured channels"""
    global predictions_sent, errors_count, consecutive_failures

    if not DAILY_PREDICTION_CHANNELS:
        return

    try:
        _, match_of_the_day = get_todays_fixtures()

        if not match_of_the_day:
            print(f"📭 No Match of the Day for scheduled post at {datetime.utcnow()}")
            return

        # Get prediction
        fixture_id = match_of_the_day["fixture"]["id"]
        league_id = match_of_the_day["league"]["id"]
        prediction_data = get_prediction(fixture_id, league_id)

        # Format message
        message = "🔔 <b>Daily Prediction Alert!</b>\n\n"
        message += "⭐ <b>MATCH OF THE DAY</b> ⭐\n\n"
        message += format_prediction_message(match_of_the_day, prediction_data)
        keyboard = create_prediction_keyboard(match_of_the_day)

        # Post to all configured channels
        for chat_id in DAILY_PREDICTION_CHANNELS:
            try:
                await application.bot.send_message(
                    chat_id=int(chat_id),
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
                predictions_sent += 1
                print(f"✅ Posted MOTD to chat {chat_id}")
            except Exception as e:
                print(f"❌ Failed to post to chat {chat_id}: {e}")
                errors_count += 1

        consecutive_failures = 0

    except Exception as e:
        consecutive_failures += 1
        errors_count += 1
        print(f"❌ Scheduled MOTD post failed: {e}")
        traceback.print_exc()


async def post_weekly_summary(application):
    """Post weekly prediction accuracy summary"""
    global errors_count

    if not DAILY_PREDICTION_CHANNELS:
        return

    try:
        # Fetch weekly accuracy stats
        response = requests.get(f"{ML_API_URL}/api/accuracy/weekly", timeout=10)
        if response.status_code != 200:
            return

        stats = response.json()

        message = "📊 <b>Weekly Prediction Summary</b>\n\n"
        message += "How did our AI perform this week?\n\n"

        if "accuracy" in stats:
            accuracy = stats["accuracy"] * 100
            total = stats.get("total_predictions", 0)
            correct = stats.get("correct_predictions", 0)
            message += f"🎯 <b>Overall Accuracy:</b> {accuracy:.1f}%\n"
            message += f"   ({correct}/{total} correct)\n\n"

        if "by_confidence" in stats:
            message += "📈 <b>By Confidence Level:</b>\n"
            for level, data in stats["by_confidence"].items():
                acc = data.get("accuracy", 0) * 100
                message += f"• {level}: {acc:.0f}%\n"

        message += f"\n🔗 <a href='{APP_URL}/models'>View Full Stats</a>"
        message += "\n\n<i>FixtureCast AI • Weekly Report • Gamble Responsibly</i>"

        # Post to all configured channels
        for chat_id in DAILY_PREDICTION_CHANNELS:
            try:
                await application.bot.send_message(
                    chat_id=int(chat_id), text=message, parse_mode=ParseMode.HTML
                )
                print(f"✅ Posted weekly summary to chat {chat_id}")
            except Exception as e:
                print(f"❌ Failed to post summary to {chat_id}: {e}")
                errors_count += 1

    except Exception as e:
        errors_count += 1
        print(f"❌ Weekly summary failed: {e}")


def health_check():
    """Periodic health check"""
    global last_health_check, consecutive_failures

    try:
        # Check backend API
        backend_ok = False
        try:
            response = requests.get(f"{BACKEND_API_URL}/health", timeout=10)
            backend_ok = response.status_code == 200
        except Exception:
            pass

        # Check ML API
        ml_ok = False
        try:
            response = requests.get(f"{ML_API_URL}/health", timeout=10)
            ml_ok = response.status_code == 200
        except Exception:
            pass

        last_health_check = datetime.utcnow()

        if not backend_ok or not ml_ok:
            consecutive_failures += 1
            print(f"⚠️ Health check: Backend={backend_ok}, ML={ml_ok}")
        else:
            if consecutive_failures > 0:
                print(f"✅ Health restored after {consecutive_failures} failures")
            consecutive_failures = 0

    except Exception as e:
        print(f"❌ Health check error: {e}")


if __name__ == "__main__":
    main()
