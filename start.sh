#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Wait for network
echo "Waiting for network connectivity..."
sleep 5

# Check required environment variables
if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: BOT_TOKEN is not set"
    exit 1
fi

if [ -z "$AWS_BUCKET" ]; then
    echo "WARNING: AWS_BUCKET is not set. Some features may not work."
fi

# Create temp directory
mkdir -p /tmp
chmod 777 /tmp

# Start the bot
echo "Starting Diamond Trading Bot..."
exec python bot.py
