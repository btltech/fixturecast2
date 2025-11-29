#!/bin/bash

# Start script that runs services based on SERVICE_TYPE env var
set -e

echo "SERVICE_TYPE: ${SERVICE_TYPE:-main}"
echo "PORT: ${PORT:-8001}"

if [ "$SERVICE_TYPE" = "ml" ]; then
    echo "Starting ML Prediction API on port ${PORT:-8002}..."
    cd /app/backend && SERVICE_TYPE=ml PORT=${PORT:-8002} python ml_api.py
elif [ "$SERVICE_TYPE" = "backend" ]; then
    echo "Starting Backend Data API on port ${PORT:-8001}..."
    cd /app/backend && python backend_api.py
elif [ "$SERVICE_TYPE" = "discord" ]; then
    echo "Starting Discord Bot..."
    cd /app && python scripts/discord_bot.py
elif [ "$SERVICE_TYPE" = "telegram" ]; then
    echo "Starting Telegram Bot..."
    cd /app && python scripts/telegram_bot.py
elif [ "$SERVICE_TYPE" = "scheduler" ]; then
    echo "Starting Scheduled Tasks..."
    cd /app && python scripts/scheduled_tasks.py
else
    echo "Starting Main API (combined) on port ${PORT:-8001}..."
    cd /app/backend && python main.py
fi
