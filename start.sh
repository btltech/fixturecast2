#!/bin/bash

# Start script that runs either ML API or Backend API based on SERVICE_TYPE env var
set -e

echo "SERVICE_TYPE: ${SERVICE_TYPE:-main}"
echo "PORT: ${PORT:-8001}"

if [ "$SERVICE_TYPE" = "ml" ]; then
    echo "Starting ML Prediction API on port ${PORT:-8002}..."
    cd /app/backend && SERVICE_TYPE=ml PORT=${PORT:-8002} python ml_api.py
elif [ "$SERVICE_TYPE" = "backend" ]; then
    echo "Starting Backend Data API on port ${PORT:-8001}..."
    cd /app/backend && python backend_api.py
else
    echo "Starting Main API (combined) on port ${PORT:-8001}..."
    cd /app/backend && python main.py
fi
