#!/usr/bin/env python3
"""
FixtureCast Discord Bot
Provides AI predictions in football Discord servers

Features:
- Slash commands: /predict, /today, /motd
- Interactive embeds with team logos and colors
- Auto-responds to match mentions
- Server-specific settings

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
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

try:
    import discord
    from discord import app_commands
except ImportError:
    print("❌ discord.py not installed. Run: pip install discord.py python-dotenv")
    sys.exit(1)

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8000")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8001")
APP_URL = os.getenv("APP_URL", "https://fixturecast.app")

# Bot intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message reading


class FixtureCastBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Sync commands with Discord"""
        await self.tree.sync()
        print("✅ Commands synced with Discord")


bot = FixtureCastBot()


# Helper functions
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


def get_prediction(fixture_id, league_id):
    """Get AI prediction"""
    try:
        response = requests.get(
            f"{ML_API_URL}/api/prediction/{fixture_id}?league={league_id}", timeout=30
        )
        response.raise_for_status()
        return response.json()
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
    print(f"📡 Connected to {len(bot.guilds)} servers")
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
        fixture = search_match(team1, team2)

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
        prediction_data = get_prediction(fixture_id, league_id)

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
        fixtures, match_of_the_day = get_todays_fixtures()

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
        _, match_of_the_day = get_todays_fixtures()

        if not match_of_the_day:
            await interaction.followup.send("📭 No Match of the Day available.")
            return

        # Get prediction
        fixture_id = match_of_the_day["fixture"]["id"]
        league_id = match_of_the_day["league"]["id"]
        prediction_data = get_prediction(fixture_id, league_id)

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

    embed.add_field(name="🌐 Website", value=f"[{APP_URL}]({APP_URL})", inline=False)

    embed.set_footer(text="Predictions by 8-Model AI Ensemble • Gamble Responsibly")

    await interaction.response.send_message(embed=embed)


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
        print(f"❌ Backend API not reachable: {e}")
        sys.exit(1)

    try:
        ml_health = requests.get(f"{ML_API_URL}/health", timeout=5)
        if ml_health.status_code == 200:
            print("✅ ML API is reachable")
    except Exception as e:
        print(f"❌ ML API not reachable: {e}")
        sys.exit(1)

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
