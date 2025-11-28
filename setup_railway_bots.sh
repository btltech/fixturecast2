#!/bin/bash

# Railway Bot Services Setup Script
# This script automatically creates Discord, Telegram, Reddit, and Twitter bot services
# on Railway using the Railway CLI.
#
# Prerequisites:
#   - Railway CLI installed: npm install -g @railway/cli
#   - Logged in: railway login
#   - Environment variables set in your shell or .env file
#
# Usage:
#   chmod +x setup_railway_bots.sh
#   ./setup_railway_bots.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Railway Bot Services Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI not found. Install it with:${NC}"
    echo "npm install -g @railway/cli"
    exit 1
fi

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo -e "${RED}❌ Not logged into Railway. Run:${NC}"
    echo "railway login"
    exit 1
fi

echo -e "${GREEN}✅ Railway CLI ready${NC}\n"

# Get project ID
PROJECT_ID=$(railway project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Could not determine Railway project. Set it with:${NC}"
    echo "railway init"
    exit 1
fi

echo -e "${YELLOW}Project ID: $PROJECT_ID${NC}\n"

# Function to create a service
create_service() {
    local SERVICE_NAME=$1
    local COMMAND=$2
    local ENV_VARS=$3

    echo -e "${BLUE}Creating service: $SERVICE_NAME${NC}"

    # Create service from GitHub repo
    railway service create \
        --name "$SERVICE_NAME" \
        --repo btltech/fixturecast2 \
        --branch main \
        --start-command "$COMMAND" \
        2>/dev/null || echo "Note: Service may already exist"

    echo -e "${GREEN}✅ Service '$SERVICE_NAME' created/configured${NC}\n"
}

# Create Discord Bot Service
echo -e "${YELLOW}[1/4]${NC} Setting up Discord Bot..."
create_service "discord-bot" "python scripts/discord_bot.py"

# Configure Discord Bot Environment Variables
echo "Setting environment variables for discord-bot..."
railway service select discord-bot 2>/dev/null || true
railway variable set DISCORD_BOT_TOKEN="${DISCORD_BOT_TOKEN}" 2>/dev/null || echo "⚠️  Set DISCORD_BOT_TOKEN manually"
railway variable set DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL}" 2>/dev/null || echo "⚠️  Set DISCORD_WEBHOOK_URL manually"
railway variable set ML_API_URL="http://ml-api:8002" 2>/dev/null || true
railway variable set BACKEND_API_URL="http://backend:8001" 2>/dev/null || true
railway variable set API_FOOTBALL_KEY="${API_FOOTBALL_KEY}" 2>/dev/null || echo "⚠️  Set API_FOOTBALL_KEY manually"
echo -e "${GREEN}✅ Discord Bot configured${NC}\n"

# Create Telegram Bot Service
echo -e "${YELLOW}[2/4]${NC} Setting up Telegram Bot..."
create_service "telegram-bot" "python scripts/telegram_bot.py"

echo "Setting environment variables for telegram-bot..."
railway service select telegram-bot 2>/dev/null || true
railway variable set TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" 2>/dev/null || echo "⚠️  Set TELEGRAM_BOT_TOKEN manually"
railway variable set ML_API_URL="http://ml-api:8002" 2>/dev/null || true
railway variable set BACKEND_API_URL="http://backend:8001" 2>/dev/null || true
railway variable set API_FOOTBALL_KEY="${API_FOOTBALL_KEY}" 2>/dev/null || echo "⚠️  Set API_FOOTBALL_KEY manually"
echo -e "${GREEN}✅ Telegram Bot configured${NC}\n"

# Create Reddit Bot Service
echo -e "${YELLOW}[3/4]${NC} Setting up Reddit Bot..."
create_service "reddit-bot" "python scripts/reddit_bot.py"

echo "Setting environment variables for reddit-bot..."
railway service select reddit-bot 2>/dev/null || true
railway variable set REDDIT_CLIENT_ID="${REDDIT_CLIENT_ID}" 2>/dev/null || echo "⚠️  Set REDDIT_CLIENT_ID manually"
railway variable set REDDIT_CLIENT_SECRET="${REDDIT_CLIENT_SECRET}" 2>/dev/null || echo "⚠️  Set REDDIT_CLIENT_SECRET manually"
railway variable set REDDIT_USER_AGENT="${REDDIT_USER_AGENT}" 2>/dev/null || echo "⚠️  Set REDDIT_USER_AGENT manually"
railway variable set ML_API_URL="http://ml-api:8002" 2>/dev/null || true
railway variable set BACKEND_API_URL="http://backend:8001" 2>/dev/null || true
railway variable set API_FOOTBALL_KEY="${API_FOOTBALL_KEY}" 2>/dev/null || echo "⚠️  Set API_FOOTBALL_KEY manually"
echo -e "${GREEN}✅ Reddit Bot configured${NC}\n"

# Create Twitter Bot Service
echo -e "${YELLOW}[4/4]${NC} Setting up Twitter Bot..."
create_service "twitter-bot" "python scripts/twitter_bot.py"

echo "Setting environment variables for twitter-bot..."
railway service select twitter-bot 2>/dev/null || true
railway variable set TWITTER_BEARER_TOKEN="${TWITTER_BEARER_TOKEN}" 2>/dev/null || echo "⚠️  Set TWITTER_BEARER_TOKEN manually"
railway variable set ML_API_URL="http://ml-api:8002" 2>/dev/null || true
railway variable set BACKEND_API_URL="http://backend:8001" 2>/dev/null || true
railway variable set API_FOOTBALL_KEY="${API_FOOTBALL_KEY}" 2>/dev/null || echo "⚠️  Set API_FOOTBALL_KEY manually"
echo -e "${GREEN}✅ Twitter Bot configured${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All bot services created!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Go to railway.app and verify all services are running"
echo "2. Check each service's logs for any errors"
echo "3. Ensure all environment variables are set correctly:"
echo "   - DISCORD_BOT_TOKEN"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT"
echo "   - TWITTER_BEARER_TOKEN"
echo ""
echo -e "${BLUE}View services:${NC}"
echo "  railway service list"
echo ""
echo -e "${BLUE}View logs:${NC}"
echo "  railway service select discord-bot && railway logs"
echo ""
