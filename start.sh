#!/bin/bash
# start.sh - Start the Diamond Trading Bot

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill existing bot processes
echo "🛑 Stopping any existing bot processes..."
pkill -f "python.*diamond_bot.py" || true
sleep 2

# Start the bot
echo "🚀 Starting Diamond Trading Bot..."
nohup python diamond_bot.py > logs/bot.log 2>&1 &

# Wait for startup
echo "⏳ Waiting for bot to start..."
sleep 5

# Check if bot is running
if pgrep -f "python.*diamond_bot.py" > /dev/null; then
    echo "✅ Bot started successfully!"
    echo ""
    echo "📊 Status Information:"
    echo "• PID: $(pgrep -f 'python.*diamond_bot.py')"
    echo "• Log file: logs/bot.log"
    echo "• API Health: http://localhost:${PORT:-10000}/health"
    echo "• API Root: http://localhost:${PORT:-10000}/"
    echo ""
    echo "📝 Useful commands:"
    echo "• View logs: tail -f logs/bot.log"
    echo "• Stop bot: ./stop.sh"
    echo "• Monitor: ./monitor.sh"
else
    echo "❌ Failed to start bot. Check logs/bot.log for errors."
    exit 1
fi
