#!/bin/bash
# FixtureCast Continuous Training Cron Script
#
# This script runs the continuous training pipeline.
# Set up as a cron job or scheduled task to run weekly.
#
# Example cron entry (runs every Monday at 3 AM):
# 0 3 * * 1 /path/to/fixturecast/scripts/run_training.sh >> /path/to/logs/training.log 2>&1

set -e

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================"
echo "FixtureCast Continuous Training"
echo "Started: $(date)"
echo "========================================"

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run the training pipeline
python3 ml_engine/continuous_training.py "$@"

echo ""
echo "Training completed: $(date)"
echo "========================================"
