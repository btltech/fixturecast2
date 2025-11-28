#!/bin/bash
# FixtureCast Bot Manager
# Run all social media bots with proper error handling

set -e

echo "🤖 Starting FixtureCast Social Media Bots..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Copy .env.example to .env and add your credentials."
    exit 1
fi

# Check if APIs are running
echo "🔍 Checking API availability..."
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "❌ Backend API not running on port 8001"
    echo "Start it with: python backend/main.py"
    exit 1
fi

if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ ML API not running on port 8000"
    echo "Start it with: python backend/ml_api.py"
    exit 1
fi

echo "✅ APIs are running"

# Function to start a bot in background
start_bot() {
    local bot_name=$1
    local script_path=$2

    echo "🚀 Starting $bot_name..."
    if python scripts/$script_path; then
        echo "✅ $bot_name started successfully"
    else
        echo "❌ Failed to start $bot_name"
        return 1
    fi
}

# Start bots (Twitter runs once daily, others run continuously)
echo ""
echo "🐦 Starting Twitter Bot (daily posts)..."
python scripts/twitter_bot.py &
TWITTER_PID=$!
echo "✅ Twitter bot started (PID: $TWITTER_PID)"

echo ""
echo "🟠 Starting Reddit Bot (continuous monitoring)..."
python scripts/reddit_bot.py &
REDDIT_PID=$!
echo "✅ Reddit bot started (PID: $REDDIT_PID)"

echo ""
echo "💙 Starting Discord Bot (continuous monitoring)..."
python scripts/discord_bot.py &
DISCORD_PID=$!
echo "✅ Discord bot started (PID: $DISCORD_PID)"

echo ""
echo "🎉 All bots are running!"
echo ""
echo "Bot PIDs:"
echo "  Twitter: $TWITTER_PID"
echo "  Reddit:  $REDDIT_PID"
echo "  Discord: $DISCORD_PID"
echo ""
echo "Press Ctrl+C to stop all bots"

# Wait for interrupt
trap "echo ''; echo '🛑 Stopping all bots...'; kill $TWITTER_PID $REDDIT_PID $DISCORD_PID 2>/dev/null; exit 0" INT
wait
