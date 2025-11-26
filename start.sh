#!/bin/bash

# Start script that runs either ML API or Backend API based on SERVICE_TYPE env var
if [ "$SERVICE_TYPE" = "backend" ]; then
    echo "Starting Backend Data API..."
    cd /app/backend && python main.py
else
    echo "Starting ML Prediction API..."
    python /app/backend/ml_api.py
fi
