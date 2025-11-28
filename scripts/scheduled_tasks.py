#!/usr/bin/env python3
"""
FixtureCast Scheduled Tasks
Automates daily predictions, weekly summaries, and health checks

This script should run 24/7 and handle:
- Daily Match of the Day posts (8 AM UTC)
- Daily top predictions post (10 AM UTC)
- Weekly performance summaries (Mondays 9 AM UTC)
- Health monitoring (every 5 minutes)
- Auto-recovery from failures

For Railway: Add to Procfile as:
scheduler: python scripts/scheduled_tasks.py
"""

import asyncio
import os
import sys
from datetime import datetime, time
from typing import Callable

import requests
from dotenv import load_dotenv

load_dotenv()

# Import bot modules conditionally
try:
    from telegram import Bot as TelegramBot
    from telegram.constants import ParseMode

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram bot not available (python-telegram-bot not installed)")

try:
    import discord

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("⚠️ Discord bot not available (discord.py not installed)")


# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")  # Your channel ID for broadcasts
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.com")


class TaskScheduler:
    """Manages scheduled tasks for bots"""

    def __init__(self):
        self.running = True
        self.last_daily_post = None
        self.last_weekly_summary = None
        self.last_health_check = None

    async def check_api_health(self) -> bool:
        """Check if APIs are healthy"""
        try:
            backend_response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
            ml_response = requests.get(f"{ML_API_URL}/health", timeout=5)

            if backend_response.status_code == 200 and ml_response.status_code == 200:
                return True
            else:
                print(
                    f"⚠️ API health check failed: Backend={backend_response.status_code}, ML={ml_response.status_code}"
                )
                return False
        except Exception as e:
            print(f"❌ API health check error: {e}")
            return False

    async def get_match_of_the_day(self):
        """Fetch Match of the Day"""
        try:
            response = requests.get(f"{BACKEND_API_URL}/api/fixtures/today", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("match_of_the_day")
        except Exception as e:
            print(f"❌ Error fetching MOTD: {e}")
            return None

    async def get_prediction(self, fixture_id, league_id):
        """Get prediction for a fixture"""
        try:
            url = f"{ML_API_URL}/api/prediction/{fixture_id}?league={league_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting prediction: {e}")
            return None

    async def post_to_telegram(self, message: str):
        """Post message to Telegram channel"""
        if not TELEGRAM_AVAILABLE or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
            print("⚠️ Telegram not configured for scheduled posts")
            return

        try:
            bot = TelegramBot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.HTML
            )
            print("✅ Posted to Telegram")
        except Exception as e:
            print(f"❌ Telegram post error: {e}")

    async def post_to_discord(self, embed_data: dict):
        """Post embed to Discord webhook"""
        if not DISCORD_WEBHOOK_URL:
            print("⚠️ Discord webhook not configured")
            return

        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed_data]}, timeout=10)
            response.raise_for_status()
            print("✅ Posted to Discord")
        except Exception as e:
            print(f"❌ Discord post error: {e}")

    def format_motd_message(self, fixture, prediction_data):
        """Format Match of the Day message"""
        home_team = fixture["teams"]["home"]["name"]
        away_team = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]
        kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))

        message = f"⭐ <b>MATCH OF THE DAY</b> ⭐\n\n"
        message += f"<b>{home_team} vs {away_team}</b>\n"
        message += f"📅 {kick_off.strftime('%B %d at %H:%M UTC')}\n"
        message += f"🏆 {league}\n\n"

        if prediction_data and "prediction" in prediction_data:
            pred = prediction_data["prediction"]
            home_prob = pred.get("home_win_prob", 0) * 100
            draw_prob = pred.get("draw_prob", 0) * 100
            away_prob = pred.get("away_win_prob", 0) * 100
            scoreline = pred.get("predicted_scoreline", "N/A")

            message += f"<b>📊 AI Prediction</b>\n"
            message += f"• {home_team}: <b>{home_prob:.1f}%</b>\n"
            message += f"• Draw: <b>{draw_prob:.1f}%</b>\n"
            message += f"• {away_team}: <b>{away_prob:.1f}%</b>\n\n"
            message += f"🎯 Predicted Score: <b>{scoreline}</b>\n\n"

        message += f"🔗 Full analysis: {APP_URL}/prediction/{fixture['fixture']['id']}"

        return message

    def format_motd_embed(self, fixture, prediction_data):
        """Format Match of the Day Discord embed"""
        home_team = fixture["teams"]["home"]["name"]
        away_team = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]
        kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))

        embed = {
            "title": f"⭐ MATCH OF THE DAY",
            "description": f"**{home_team} vs {away_team}**\n{league}",
            "color": 0xFFD700,  # Gold
            "thumbnail": {"url": fixture["teams"]["home"].get("logo", "")},
            "fields": [],
            "footer": {"text": "FixtureCast AI • 8-Model Ensemble"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if prediction_data and "prediction" in prediction_data:
            pred = prediction_data["prediction"]
            home_prob = pred.get("home_win_prob", 0) * 100
            draw_prob = pred.get("draw_prob", 0) * 100
            away_prob = pred.get("away_win_prob", 0) * 100
            scoreline = pred.get("predicted_scoreline", "N/A")

            embed["fields"].extend(
                [
                    {
                        "name": "📊 Win Probabilities",
                        "value": f"**{home_team}:** {home_prob:.1f}%\n**Draw:** {draw_prob:.1f}%\n**{away_team}:** {away_prob:.1f}%",
                        "inline": False,
                    },
                    {"name": "🎯 Predicted Score", "value": f"**{scoreline}**", "inline": True},
                    {
                        "name": "⏰ Kick-off",
                        "value": kick_off.strftime("%B %d, %H:%M UTC"),
                        "inline": True,
                    },
                ]
            )

        return embed

    async def daily_motd_post(self):
        """Post daily Match of the Day"""
        print("📅 Running daily MOTD post...")

        # Check API health
        if not await self.check_api_health():
            print("❌ APIs not healthy, skipping MOTD post")
            return

        # Get Match of the Day
        motd = await self.get_match_of_the_day()
        if not motd:
            print("⚠️ No Match of the Day available")
            return

        # Get prediction
        fixture_id = motd["fixture"]["id"]
        league_id = motd["league"]["id"]
        prediction = await self.get_prediction(fixture_id, league_id)

        # Post to platforms
        telegram_msg = self.format_motd_message(motd, prediction)
        await self.post_to_telegram(telegram_msg)

        discord_embed = self.format_motd_embed(motd, prediction)
        await self.post_to_discord(discord_embed)

        print("✅ Daily MOTD post completed")

    async def health_check_task(self):
        """Periodic health check"""
        if await self.check_api_health():
            print("✅ Health check passed")
        else:
            print("⚠️ Health check failed - APIs may be down")
            # Could send alert here

    async def run_at_time(self, target_time: time, task: Callable, task_name: str):
        """Run task once per day at target time"""
        last_run_date = None

        while self.running:
            now = datetime.utcnow()
            current_time = now.time()
            current_date = now.date()

            # Check if we should run (right time and haven't run today)
            if current_time >= target_time and last_run_date != current_date:
                print(f"🕐 Triggering scheduled task: {task_name}")
                try:
                    await task()
                    last_run_date = current_date
                except Exception as e:
                    print(f"❌ Error in {task_name}: {e}")

            # Sleep for 1 minute before checking again
            await asyncio.sleep(60)

    async def run_periodic(self, interval_minutes: int, task: Callable, task_name: str):
        """Run task periodically at interval"""
        while self.running:
            try:
                await task()
            except Exception as e:
                print(f"❌ Error in {task_name}: {e}")

            await asyncio.sleep(interval_minutes * 60)

    async def start(self):
        """Start all scheduled tasks"""
        print("=" * 60)
        print("FixtureCast Scheduled Tasks")
        print("=" * 60)
        print(f"Started at: {datetime.utcnow()} UTC")
        print()
        print("📅 Daily Schedule:")
        print("  - Match of the Day: 08:00 UTC")
        print("  - Health checks: Every 5 minutes")
        print()

        # Create tasks
        tasks = [
            # Daily MOTD at 8 AM UTC
            asyncio.create_task(
                self.run_at_time(time(8, 0), self.daily_motd_post, "Daily MOTD Post")
            ),
            # Health checks every 5 minutes
            asyncio.create_task(self.run_periodic(5, self.health_check_task, "Health Check")),
        ]

        print("✅ Scheduler is running!")
        print("Press Ctrl+C to stop\n")

        # Run all tasks
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Stopping scheduler...")
            self.running = False


async def main():
    """Main entry point"""
    scheduler = TaskScheduler()
    await scheduler.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped")
        sys.exit(0)
