#!/bin/bash
# Setup script to add scheduler to crontab

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH=$(which python3)
CRON_LOG="$SCRIPT_DIR/scheduler.log"

# Create the cron job entry
CRON_JOB="*/15 * * * * cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_DIR/scheduler.py --once >> $CRON_LOG 2>&1"

echo "Setting up cron job for Arc'teryx Stock Monitor..."
echo ""
echo "Cron job will be:"
echo "$CRON_JOB"
echo ""
echo "This will check stock every 15 minutes."
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "scheduler.py"; then
    echo "⚠️  A scheduler cron job already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep scheduler.py
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing scheduler cron job
        crontab -l 2>/dev/null | grep -v "scheduler.py" | crontab -
        # Add new one
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✅ Cron job updated!"
    else
        echo "Cancelled. No changes made."
        exit 0
    fi
else
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added successfully!"
fi

echo ""
echo "To view your cron jobs, run: crontab -l"
echo "To remove the cron job, run: crontab -e (then delete the line)"
echo "Logs will be saved to: $CRON_LOG"

