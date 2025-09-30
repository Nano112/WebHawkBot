#!/usr/bin/env python3
"""
Test script to send commands to WebHawkBot
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_command(command):
    """Send a command to the bot"""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing credentials")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": command
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Sent command: {command}")
        else:
            print(f"❌ Failed to send command: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing WebHawkBot commands...")
    print(f"Chat ID: {CHAT_ID}")
    print()

    # Test commands
    test_commands = [
        "/help",
        "/status",
        "/add https://example.com"
    ]

    for cmd in test_commands:
        send_command(cmd)
        print(f"Sent: {cmd}")

    print("\n📨 Commands sent! Check your Telegram channel for responses.")