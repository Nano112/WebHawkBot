#!/bin/bash
set -e

echo "🚀 Starting WebHawkBot..."
echo "Environment variables:"
echo "TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"

# Start the bot
exec python3 webpage_monitor.py