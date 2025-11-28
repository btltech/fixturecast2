#!/bin/bash
# Quick setup script for bot automation
# Run this to deploy automated bots to Railway

set -e

echo "🤖 FixtureCast Bot Automation Setup"
echo "===================================="
echo ""

# Check if git repo exists
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository. Initialize first:"
    echo "   git init"
    echo "   git remote add origin <your-repo-url>"
    exit 1
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "⚠️  Railway CLI not found."
    echo "Install it: npm install -g @railway/cli"
    echo "Or deploy manually via Railway dashboard"
    echo ""
fi

echo "📋 Pre-deployment Checklist:"
echo ""
echo "1. ✅ Bot scripts created (telegram_bot.py, discord_bot.py)"
echo "2. ✅ Scheduler created (scheduled_tasks.py)"
echo "3. ✅ Procfile updated with scheduler service"
echo "4. ✅ GitHub Actions workflow created (deploy-bots.yml)"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo "Make sure you've configured environment variables in Railway dashboard"
fi

echo "📝 Required Railway Environment Variables:"
echo ""
echo "  Core (Required):"
echo "    DISCORD_BOT_TOKEN"
echo "    TELEGRAM_BOT_TOKEN"
echo "    ML_API_URL (e.g., http://web.railway.internal:8000)"
echo "    BACKEND_API_URL (e.g., http://backend.railway.internal:8001)"
echo "    APP_URL (e.g., https://fixturecast.com)"
echo ""
echo "  Optional (for automated posts):"
echo "    TELEGRAM_CHANNEL_ID=-100123456789"
echo "    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..."
echo ""

read -p "Have you configured these in Railway dashboard? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please configure environment variables first:"
    echo "   Railway Dashboard → Your Project → Variables"
    exit 1
fi

echo ""
echo "🚀 Deploying to Railway..."
echo ""

# Stage files
echo "📦 Staging files..."
git add Procfile
git add scripts/scheduled_tasks.py
git add .github/workflows/deploy-bots.yml
git add BOT_AUTOMATION_GUIDE.md

# Show what will be committed
echo ""
echo "Files to commit:"
git status --short

echo ""
read -p "Proceed with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Commit
echo "📝 Committing changes..."
git commit -m "feat: Add bot automation with scheduler

- Added scheduled_tasks.py for automated daily predictions
- Updated Procfile to include scheduler service
- Added GitHub Actions workflow for auto-deployment
- Created comprehensive automation guide
"

# Push
echo "🚀 Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Deployment initiated!"
echo ""
echo "Railway will automatically:"
echo "  1. Detect the push to main branch"
echo "  2. Build and deploy all services"
echo "  3. Start the scheduler service"
echo ""
echo "📊 Monitor deployment:"
echo "  - Railway Dashboard: https://railway.app"
echo "  - GitHub Actions: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo ""
echo "📋 Next steps:"
echo "  1. Check Railway logs: railway logs -s scheduler"
echo "  2. Verify services are running in Railway dashboard"
echo "  3. Wait for 8:00 AM UTC for first automated post"
echo "  4. Check BOT_AUTOMATION_GUIDE.md for customization"
echo ""
echo "🎉 Done! Your bots are now automated."
