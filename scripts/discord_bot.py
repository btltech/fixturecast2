#!/usr/bin/env python3
"""
FixtureCast Discord Bot
Provides AI predictions in football Discord servers

Features:
- Slash commands: /predict, /today, /motd
- Interactive embeds with team logos and colors
- Auto-responds to match mentions
- Server-specific settings
- AUTOMATED DAILY PREDICTIONS: Posts Match of the Day at scheduled times
- HEALTH MONITORING: Auto-reconnect and error recovery
- WEEKLY SUMMARIES: Posts prediction accuracy on Sundays

Requirements:
    pip install discord.py python-dotenv requests

Setup:
1. Create Discord app at https://discord.com/developers/applications
2. Enable "Message Content Intent" in Bot settings
3. Get bot token and add to .env
4. Invite bot to server with applications.commands scope
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
    import discord
    from discord import app_commands
    from discord.ext import tasks
except ImportError:
    print("❌ discord.py not installed. Run: pip install discord.py python-dotenv")
    sys.exit(1)

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.com")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Scheduled posting channels (comma-separated channel IDs)
DAILY_PREDICTION_CHANNELS = os.getenv("DAILY_PREDICTION_CHANNELS", "").split(",")
DAILY_PREDICTION_CHANNELS = [c.strip() for c in DAILY_PREDICTION_CHANNELS if c.strip()]

# Scheduled times (UK timezone - UTC+0/+1)
MORNING_POST_TIME = time(hour=8, minute=0)  # 8:00 AM UK
AFTERNOON_POST_TIME = time(hour=14, minute=0)  # 2:00 PM UK
EVENING_POST_TIME = time(hour=18, minute=0)  # 6:00 PM UK

# Health monitoring
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MAX_CONSECUTIVE_FAILURES = 3
consecutive_failures = 0
last_health_check = None

# Bot intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message reading


class FixtureCastBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.start_time = datetime.utcnow()
        self.predictions_sent = 0
        self.errors_count = 0

    async def setup_hook(self):
        """Sync commands with Discord and start scheduled tasks"""
        await self.tree.sync()
        print("✅ Commands synced with Discord")

        # Start scheduled tasks (these are module-level, not class methods)
        if not daily_motd_post.is_running():
            daily_motd_post.start()
        if not health_check_task.is_running():
            health_check_task.start()
        if not weekly_summary.is_running():
            weekly_summary.start()
        print("✅ Scheduled tasks started")

    async def close(self):
        """Cleanup on shutdown"""
        if daily_motd_post.is_running():
            daily_motd_post.cancel()
        if health_check_task.is_running():
            health_check_task.cancel()
        if weekly_summary.is_running():
            weekly_summary.cancel()
        await super().close()


bot = FixtureCastBot()


# ============================================================================
# SCHEDULED TASKS
# ============================================================================


@tasks.loop(time=[MORNING_POST_TIME, AFTERNOON_POST_TIME])
async def daily_motd_post():
    """Post Match of the Day prediction at scheduled times"""
    global consecutive_failures

    if not DAILY_PREDICTION_CHANNELS:
        return  # No channels configured

    try:
        _, match_of_the_day = await get_todays_fixtures()

        if not match_of_the_day:
            print(f"📭 No Match of the Day for scheduled post at {datetime.utcnow()}")
            return

        # Get prediction
        fixture_id = match_of_the_day["fixture"]["id"]
        league_id = match_of_the_day["league"]["id"]
        prediction_data = await get_prediction(fixture_id, league_id)

        # Create embed
        embed = create_prediction_embed(match_of_the_day, prediction_data)
        embed.title = f"⭐ MATCH OF THE DAY ⭐\n\n{embed.title}"
        embed.color = discord.Color.gold()

        # Add scheduled post indicator
        current_time = datetime.utcnow().strftime("%H:%M UTC")
        embed.set_footer(text=f"FixtureCast AI • Scheduled {current_time} • Gamble Responsibly")

        # Post to all configured channels
        for channel_id in DAILY_PREDICTION_CHANNELS:
            try:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(content="🔔 **Daily Prediction Alert!**", embed=embed)
                    bot.predictions_sent += 1
                    print(f"✅ Posted MOTD to channel {channel.name} ({channel_id})")
            except Exception as e:
                print(f"❌ Failed to post to channel {channel_id}: {e}")

        consecutive_failures = 0

    except Exception as e:
        consecutive_failures += 1
        bot.errors_count += 1
        print(f"❌ Scheduled MOTD post failed: {e}")
        traceback.print_exc()


@daily_motd_post.before_loop
async def before_daily_motd():
    """Wait for bot to be ready before starting scheduled posts"""
    await bot.wait_until_ready()
    print(
        f"✅ Daily MOTD scheduler ready. Posting at {MORNING_POST_TIME} and {AFTERNOON_POST_TIME} UTC"
    )


@tasks.loop(seconds=HEALTH_CHECK_INTERVAL)
async def health_check_task():
    """Monitor bot health and API connectivity"""
    global consecutive_failures, last_health_check

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

        # Check Discord connection
        discord_ok = bot.is_ready() and not bot.is_closed()

        # Log health status
        status = "✅" if (backend_ok and ml_ok and discord_ok) else "⚠️"
        last_health_check = datetime.utcnow()

        if not backend_ok or not ml_ok:
            consecutive_failures += 1
            print(f"⚠️ Health check: Backend={backend_ok}, ML={ml_ok}, Discord={discord_ok}")

            # Send alert via webhook if too many failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES and DISCORD_WEBHOOK_URL:
                await send_webhook_alert(
                    f"🚨 **FixtureCast Bot Health Alert**\n\n"
                    f"Backend API: {'✅' if backend_ok else '❌'}\n"
                    f"ML API: {'✅' if ml_ok else '❌'}\n"
                    f"Discord: {'✅' if discord_ok else '❌'}\n"
                    f"Consecutive failures: {consecutive_failures}"
                )
        else:
            if consecutive_failures > 0:
                print(f"✅ Health restored after {consecutive_failures} failures")
            consecutive_failures = 0

    except Exception as e:
        print(f"❌ Health check error: {e}")


@health_check_task.before_loop
async def before_health_check():
    """Wait for bot to be ready"""
    await bot.wait_until_ready()
    print(f"✅ Health monitoring started (every {HEALTH_CHECK_INTERVAL}s)")


@tasks.loop(time=time(hour=20, minute=0))  # 8 PM UTC on Sundays
async def weekly_summary():
    """Post weekly prediction accuracy summary on Sundays"""
    if datetime.utcnow().weekday() != 6:  # Only on Sunday
        return

    if not DAILY_PREDICTION_CHANNELS:
        return

    try:
        # Fetch weekly accuracy stats
        stats = await fetch_json(f"{ML_API_URL}/api/accuracy/weekly")

        if not stats:
            return

        embed = discord.Embed(
            title="📊 Weekly Prediction Summary",
            description="How did our AI perform this week?",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow(),
        )

        if "accuracy" in stats:
            accuracy = stats["accuracy"] * 100
            total = stats.get("total_predictions", 0)
            correct = stats.get("correct_predictions", 0)

            embed.add_field(
                name="🎯 Overall Accuracy",
                value=f"**{accuracy:.1f}%**\n({correct}/{total} correct)",
                inline=True,
            )

        if "by_confidence" in stats:
            conf_text = ""
            for level, data in stats["by_confidence"].items():
                acc = data.get("accuracy", 0) * 100
                conf_text += f"**{level}:** {acc:.0f}%\n"
            embed.add_field(name="📈 By Confidence", value=conf_text, inline=True)

        embed.add_field(
            name="🔗 Full Stats",
            value=f"[View detailed model stats]({APP_URL}/models)",
            inline=False,
        )

        embed.set_footer(text="FixtureCast AI • Weekly Report • Gamble Responsibly")

        # Post to all configured channels
        for channel_id in DAILY_PREDICTION_CHANNELS:
            try:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(embed=embed)
                    print(f"✅ Posted weekly summary to {channel.name}")
            except Exception as e:
                print(f"❌ Failed to post summary to {channel_id}: {e}")

    except Exception as e:
        print(f"❌ Weekly summary failed: {e}")


@weekly_summary.before_loop
async def before_weekly_summary():
    """Wait for bot to be ready"""
    await bot.wait_until_ready()
    print("✅ Weekly summary scheduler ready (Sundays 8 PM UTC)")


async def send_webhook_alert(message):
    """Send alert via Discord webhook"""
    if not DISCORD_WEBHOOK_URL:
        return

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception as e:
        print(f"❌ Webhook alert failed: {e}")


# Helper functions
async def fetch_json(url):
    """Async fetch JSON from URL"""
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(None, lambda: requests.get(url, timeout=10))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


async def get_todays_fixtures():
    """Fetch today's fixtures"""
    data = await fetch_json(f"{BACKEND_API_URL}/api/fixtures/today")
    if data:
        return data.get("response", []), data.get("match_of_the_day")
    return [], None


async def search_match(team1, team2=None):
    """Search for a match"""
    fixtures, _ = await get_todays_fixtures()

    if not fixtures:
        return None

    team1_lower = team1.lower().strip()

    if team2:
        team2_lower = team2.lower().strip()
        # Search for specific matchup
        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            if (team1_lower in home and team2_lower in away) or (
                team2_lower in home and team1_lower in away
            ):
                return fixture
    else:
        # Search for any match involving team1
        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            if team1_lower in home or team1_lower in away:
                return fixture

    return None


async def get_prediction(fixture_id, league_id):
    """Get AI prediction"""
    # Defensive: ensure fixture_id and league_id are clean integers
    try:
        fid = int(str(fixture_id).strip())
        lid = int(str(league_id).strip())
        url = f"{ML_API_URL}/api/prediction/{fid}?league={lid}"
        print(f"DEBUG: Fetching prediction from: {url}")
        return await fetch_json(url)
    except Exception as e:
        print(f"❌ Error getting prediction: {e}")
        return None


def create_prediction_embed(fixture, prediction_data):
    """Create Discord embed for prediction"""
    home_team = fixture["teams"]["home"]["name"]
    away_team = fixture["teams"]["away"]["name"]
    league = fixture["league"]["name"]
    kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))

    # Create embed with team colors
    embed = discord.Embed(
        title=f"🔮 {home_team} vs {away_team}",
        description=f"**{league}**\n⏰ {kick_off.strftime('%B %d at %H:%M UTC')}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )

    # Add team logos as thumbnail
    if fixture["teams"]["home"].get("logo"):
        embed.set_thumbnail(url=fixture["teams"]["home"]["logo"])

    if prediction_data and "prediction" in prediction_data:
        pred = prediction_data["prediction"]
        home_prob = pred.get("home_win_prob", 0) * 100
        draw_prob = pred.get("draw_prob", 0) * 100
        away_prob = pred.get("away_win_prob", 0) * 100
        scoreline = pred.get("predicted_scoreline", "N/A")
        btts = pred.get("btts_prob", 0) * 100
        over25 = pred.get("over25_prob", 0) * 100

        # Determine confidence and color
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 65:
            confidence = "🟢 High Confidence"
            embed.color = discord.Color.green()
        elif max_prob > 50:
            confidence = "🟡 Medium Confidence"
            embed.color = discord.Color.gold()
        else:
            confidence = "🔴 Close Match"
            embed.color = discord.Color.red()

        # Win probabilities
        embed.add_field(
            name="📊 Win Probabilities",
            value=f"**{home_team}:** {home_prob:.1f}%\n"
            f"**Draw:** {draw_prob:.1f}%\n"
            f"**{away_team}:** {away_prob:.1f}%",
            inline=False,
        )

        # Predicted score
        embed.add_field(name="🎯 Predicted Score", value=f"**{scoreline}**", inline=True)

        # Confidence
        embed.add_field(name="📈 Confidence", value=confidence, inline=True)

        # Betting markets
        embed.add_field(
            name="💰 Betting Markets",
            value=f"**BTTS:** {btts:.0f}%\n**Over 2.5:** {over25:.0f}%",
            inline=False,
        )

    # Add link
    fixture_id = fixture["fixture"]["id"]
    league_id = fixture["league"]["id"]
    embed.add_field(
        name="🔗 Full Analysis",
        value=f"[View on FixtureCast]({APP_URL}/prediction/{fixture_id}?league={league_id})",
        inline=False,
    )

    embed.set_footer(text="FixtureCast AI • 8-Model Ensemble • Gamble Responsibly")

    return embed


# Bot events
@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"📡 Connected to {len(bot.guilds)} servers:")
    for guild in bot.guilds:
        print(f"   - 🏠 Server Name: {guild.name} (ID: {guild.id})")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="football matches | /predict"
        )
    )


# Slash commands
@bot.tree.command(name="predict", description="Get AI prediction for a match")
@app_commands.describe(
    team1="First team name (e.g., Arsenal)", team2="Second team name (optional, e.g., Chelsea)"
)
async def predict(interaction: discord.Interaction, team1: str, team2: str = None):
    """Predict command"""
    await interaction.response.defer()  # Shows "Bot is thinking..."

    try:
        # Search for match
        fixture = await search_match(team1, team2)

        if not fixture:
            if team2:
                await interaction.followup.send(
                    f"❌ Could not find a match between **{team1}** and **{team2}** scheduled for today.\n"
                    f"Check all fixtures at {APP_URL}"
                )
            else:
                await interaction.followup.send(
                    f"❌ Could not find a match for **{team1}** scheduled for today.\n"
                    f"Check all fixtures at {APP_URL}"
                )
            return

        # Get prediction
        fixture_id = fixture["fixture"]["id"]
        league_id = fixture["league"]["id"]
        prediction_data = await get_prediction(fixture_id, league_id)

        # Create and send embed
        embed = create_prediction_embed(fixture, prediction_data)
        await interaction.followup.send(embed=embed)

        print(
            f"  ✅ Sent prediction for {fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
        )
        print(
            f"     Requested by: {interaction.user} in {interaction.guild.name if interaction.guild else 'DM'}"
        )

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")
        print(f"  ❌ Error in /predict: {e}")


@bot.tree.command(name="today", description="Show all matches scheduled for today")
async def today(interaction: discord.Interaction):
    """Show today's matches"""
    await interaction.response.defer()

    try:
        fixtures, match_of_the_day = await get_todays_fixtures()

        if not fixtures:
            await interaction.followup.send("📭 No matches scheduled for today.")
            return

        embed = discord.Embed(
            title="📅 Today's Matches",
            description=f"**{len(fixtures)} matches** scheduled across all leagues",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow(),
        )

        # Group by league
        by_league = {}
        for fixture in fixtures[:20]:  # Limit to 20
            league_name = fixture["league"]["name"]
            if league_name not in by_league:
                by_league[league_name] = []
            by_league[league_name].append(fixture)

        # Add fields for each league
        for league_name, league_fixtures in by_league.items():
            matches_text = ""
            for fixture in league_fixtures[:5]:  # Max 5 per league
                home = fixture["teams"]["home"]["name"]
                away = fixture["teams"]["away"]["name"]
                kick_off = datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
                time_str = kick_off.strftime("%H:%M")
                matches_text += f"⚽ {home} vs {away} ({time_str})\n"

            embed.add_field(
                name=f"🏆 {league_name}", value=matches_text or "No matches", inline=False
            )

        embed.add_field(
            name="🔮 Get Predictions",
            value=f"Use `/predict Team1 Team2` or visit [{APP_URL}]({APP_URL})",
            inline=False,
        )

        embed.set_footer(text="FixtureCast AI • Real-time match data")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")
        print(f"  ❌ Error in /today: {e}")


@bot.tree.command(name="motd", description="Show Match of the Day prediction")
async def motd(interaction: discord.Interaction):
    """Match of the Day command"""
    await interaction.response.defer()

    try:
        _, match_of_the_day = await get_todays_fixtures()

        if not match_of_the_day:
            await interaction.followup.send("📭 No Match of the Day available.")
            return

        # Get prediction
        fixture_id = match_of_the_day["fixture"]["id"]
        league_id = match_of_the_day["league"]["id"]
        prediction_data = await get_prediction(fixture_id, league_id)

        # Create embed
        embed = create_prediction_embed(match_of_the_day, prediction_data)
        embed.title = f"⭐ MATCH OF THE DAY ⭐\n\n{embed.title}"
        embed.color = discord.Color.gold()

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")
        print(f"  ❌ Error in /motd: {e}")


@bot.tree.command(name="help", description="Show bot commands and usage")
async def help_command(interaction: discord.Interaction):
    """Help command"""
    embed = discord.Embed(
        title="🤖 FixtureCast Bot Commands",
        description="AI-powered football match predictions",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="/predict [team1] [team2]",
        value="Get AI prediction for a specific match\n" "Example: `/predict Arsenal Chelsea`",
        inline=False,
    )

    embed.add_field(name="/today", value="View all matches scheduled for today", inline=False)

    embed.add_field(name="/motd", value="Get prediction for today's Match of the Day", inline=False)

    embed.add_field(name="/status", value="Check bot health and uptime", inline=False)

    embed.add_field(name="🌐 Website", value=f"[{APP_URL}]({APP_URL})", inline=False)

    embed.set_footer(text="Predictions by 8-Model AI Ensemble • Gamble Responsibly")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Check bot health and statistics")
async def status_command(interaction: discord.Interaction):
    """Status command - shows bot health and stats"""
    await interaction.response.defer()

    try:
        # Calculate uptime
        uptime = datetime.utcnow() - bot.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m"

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

        embed = discord.Embed(
            title="🤖 FixtureCast Bot Status",
            color=discord.Color.green() if (backend_ok and ml_ok) else discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)

        embed.add_field(
            name="📊 Stats",
            value=f"Predictions: {bot.predictions_sent}\nErrors: {bot.errors_count}",
            inline=True,
        )

        embed.add_field(name="🖥️ Servers", value=f"{len(bot.guilds)} connected", inline=True)

        embed.add_field(
            name="🔌 API Status",
            value=f"Backend: {'✅' if backend_ok else '❌'}\nML API: {'✅' if ml_ok else '❌'}",
            inline=True,
        )

        embed.add_field(
            name="⏰ Scheduled Posts",
            value=f"Morning: {MORNING_POST_TIME.strftime('%H:%M')} UTC\n"
            f"Afternoon: {AFTERNOON_POST_TIME.strftime('%H:%M')} UTC",
            inline=True,
        )

        if last_health_check:
            embed.add_field(
                name="🩺 Last Health Check",
                value=last_health_check.strftime("%H:%M:%S UTC"),
                inline=True,
            )

        embed.set_footer(text="FixtureCast AI • Health Monitoring Active")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error getting status: {str(e)}")


def main():
    """Main execution"""
    print("=" * 60)
    print("FixtureCast Discord Bot")
    print("=" * 60)

    if not DISCORD_TOKEN:
        print("❌ DISCORD_BOT_TOKEN not found in .env")
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

    print("\n🚀 Starting Discord bot...\n")

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid Discord token. Check your .env file.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
