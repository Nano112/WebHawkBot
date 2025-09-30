# 🦅 WebHawkBot

A Telegram bot for monitoring webpage changes with real-time notifications. Track content changes, HTTP status code transitions, and manage your monitored URLs via Telegram commands.

## Features

- 🔔 **Real-time Notifications**: Get instant Telegram alerts when webpages change
- 📊 **Status Code Tracking**: Monitor HTTP status transitions (200→404, 500→200, etc.)
- 🔧 **Telegram Commands**: Full URL management via chat commands
- 📄 **Content Diffs**: Optional detailed change tracking with unified diffs
- 🐳 **Docker Ready**: Easy deployment with Docker/Dokploy
- 💾 **Persistent Storage**: Configuration and hashes saved to disk

## Quick Start

### 1. Setup Environment

Create a `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 2. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python webpage_monitor.py
```

### 3. Run with Docker

```bash
# Build and run
docker-compose up -d

# Or with Docker directly
docker build -t webhawkbot .
docker run -e TELEGRAM_BOT_TOKEN=your_token -e TELEGRAM_CHAT_ID=your_id webhawkbot
```

## Telegram Commands

### URL Management
- `/add <url>` - Add URL to monitor
- `/remove <url>` or `/rm <url>` - Remove URL
- `/list` or `/ls` - List monitored URLs
- `/clear` - Clear all URLs

### Settings
- `/interval <seconds>` - Set check interval (min 30s)
- `/content` or `/diff` - Toggle content storage for diffs
- `/status` - Show current status and settings

### Control
- `/stop` - Stop monitoring
- `/help` - Show all commands

### Examples
```
/add https://example.com
/interval 600
/status
```

## Configuration Files

- `monitor_config.json` - Stores URLs, interval, and settings
- `page_hashes.json` - Stores webpage hashes and status codes
- `.env` - Environment variables (not committed to git)

## Docker Deployment (Dokploy)

1. **Build the image** in your Dokploy dashboard
2. **Set environment variables**:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. **Mount volumes** (optional, for persistence):
   - `./monitor_config.json:/app/monitor_config.json`
   - `./page_hashes.json:/app/page_hashes.json`
4. **Deploy!**

## Development

### Project Structure
```
WebHawkBot/
├── webpage_monitor.py    # Main application
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose setup
├── .dockerignore       # Docker ignore rules
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

### Key Classes

- `URLManager` - Handles URL list and configuration persistence
- `WebpageMonitor` - Core monitoring logic and Telegram integration

## Security Notes

- Keep your bot token secure and never commit it to version control
- The bot only responds to commands from the configured chat ID
- All data is stored locally in JSON files

## Troubleshooting

### Bot not responding
1. Check your bot token is correct
2. Verify the chat ID matches your Telegram chat
3. Ensure the bot is running and not crashed

### Docker issues
1. Check environment variables are set correctly
2. Verify volume mounts if using persistent storage
3. Check container logs: `docker-compose logs`

### Permission issues
1. Ensure the application can write to the current directory
2. Check file permissions for config files

## Channel Setup

WebHawkBot works with both private chats and Telegram channels. For channels, follow these steps:

### 1. Add Bot to Channel
1. Open your Telegram channel
2. Go to **Channel Settings** → **Administrators**
3. **Add Administrator** → Search for `@WebHawkBot`
4. Grant these permissions:
   - ✅ **Post Messages**
   - ✅ **Edit Messages** 
   - ✅ **Delete Messages**

### 2. Get Channel ID
For channel `https://t.me/c/3043629919/4`:
- **Channel ID**: `3043629919`
- **Chat ID**: `-1003043629919`

### 3. Update Environment
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=-1003043629919  # Note the -100 prefix
```

### 4. Test Setup
```bash
python3 channel_setup.py
```

### Channel Commands
All commands work the same in channels:
```
/add https://example.com
/status
/help
```

**Note**: The bot will only respond to commands from channel administrators.