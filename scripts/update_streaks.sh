#!/bin/bash

# Script to update user streaks based on activity
# This should be run daily via cron

# Change to the Django project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run the management commands
echo "Updating streaks from activity..."
python manage.py update_streaks_from_activity --days=7

echo "Resetting inactive streaks..."
python manage.py reset_inactive_streaks

echo "Streak update completed at $(date)"
