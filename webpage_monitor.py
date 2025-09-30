import requests
import hashlib
import time
import json
import os
import html
import signal
import sys
from datetime import datetime
from difflib import unified_diff


from dotenv import load_dotenv
load_dotenv()


class URLManager:
    """Manages the list of URLs to monitor and configuration settings"""
    def __init__(self, config_file="monitor_config.json"):
        self.config_file = config_file
        self.urls = []
        self.interval = 300  # 5 minutes default
        self.store_content = False
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.urls = config.get('urls', [])
                self.interval = config.get('interval', 300)
                self.store_content = config.get('store_content', False)
        except FileNotFoundError:
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        config = {
            'urls': self.urls,
            'interval': self.interval,
            'store_content': self.store_content,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def add_url(self, url):
        """Add a URL to monitor"""
        if url not in self.urls:
            self.urls.append(url)
            self.save_config()
            return True
        return False

    def remove_url(self, url):
        """Remove a URL from monitoring"""
        if url in self.urls:
            self.urls.remove(url)
            self.save_config()
            return True
        return False

    def clear_urls(self):
        """Clear all URLs"""
        self.urls = []
        self.save_config()

    def set_interval(self, interval):
        """Set check interval in seconds"""
        self.interval = max(30, interval)  # Minimum 30 seconds
        self.save_config()

    def toggle_content_storage(self):
        """Toggle content storage for diffs"""
        self.store_content = not self.store_content
        self.save_config()
        return self.store_content


class WebpageMonitor:
    def __init__(self, bot_token, chat_id, url_manager=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.telegram_api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.hashes_file = "page_hashes.json"
        self.url_manager = url_manager or URLManager()
        self.load_hashes()
        self.running = False
        
        # Validate credentials on initialization
        if not self.validate_credentials():
            print("⚠️  Warning: Telegram credentials may be invalid. Messages may fail to send.")
    
    def load_hashes(self):
        """Load previously stored hashes from file"""
        try:
            with open(self.hashes_file, 'r') as f:
                self.stored_hashes = json.load(f)
        except FileNotFoundError:
            self.stored_hashes = {}
    
    def save_hashes(self):
        """Save current hashes to file"""
        with open(self.hashes_file, 'w') as f:
            json.dump(self.stored_hashes, f, indent=2)
    
    def get_page_content(self, url):
        """Fetch webpage content and return content with status code"""
        try:
            response = requests.get(url, timeout=10)
            # Don't raise for status here - we want to track status code changes
            return response.text, response.status_code
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None, None
    
    def calculate_hash(self, content):
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_diff(self, old_content, new_content):
        """Generate a simple diff between old and new content"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = unified_diff(old_lines, new_lines, lineterm='', n=1)
        diff_text = ''.join(list(diff)[:20])  # Limit to first 20 lines
        return diff_text if diff_text else "Content changed (diff too large to display)"
    
    def validate_credentials(self):
        """Validate Telegram bot token and chat_id"""
        try:
            test_payload = {
                "chat_id": self.chat_id,
                "text": "🧪 WebHawkBot validation test"
            }
            response = requests.post(self.telegram_api, json=test_payload, timeout=10)
            if response.status_code == 200:
                print("✓ Telegram credentials validated successfully")
                return True
            else:
                print(f"❌ Telegram validation failed: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Could not validate Telegram credentials: {e}")
            return False
    
    def escape_html(self, text):
        """Escape HTML characters for Telegram HTML parse mode"""
        return html.escape(str(text))
    
    def process_command(self, command_text):
        """Process a command from Telegram"""
        command_text = command_text.strip()
        if not command_text.startswith('/'):
            return "❌ Commands must start with /"

        parts = command_text.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == '/start' or command == '/help':
            return self.get_help_text()
        elif command == '/add':
            return self.handle_add_url(args)
        elif command == '/remove' or command == '/rm':
            return self.handle_remove_url(args)
        elif command == '/list' or command == '/ls':
            return self.handle_list_urls()
        elif command == '/clear':
            return self.handle_clear_urls()
        elif command == '/interval' or command == '/int':
            return self.handle_set_interval(args)
        elif command == '/content' or command == '/diff':
            return self.handle_toggle_content()
        elif command == '/status':
            return self.handle_status()
        elif command == '/stop':
            return self.handle_stop()
        else:
            return f"❌ Unknown command: {command}\n\n{self.get_help_text()}"

    def get_help_text(self):
        """Get help text for commands"""
        return """🦅 <b>WebHawkBot Commands</b>

<b>URL Management:</b>
• <code>/add &lt;url&gt;</code> - Add URL to monitor
• <code>/remove &lt;url&gt;</code> or <code>/rm &lt;url&gt;</code> - Remove URL
• <code>/list</code> or <code>/ls</code> - List monitored URLs
• <code>/clear</code> - Clear all URLs

<b>Settings:</b>
• <code>/interval &lt;seconds&gt;</code> - Set check interval (min 30s)
• <code>/content</code> or <code>/diff</code> - Toggle content storage for diffs
• <code>/status</code> - Show current status and settings

<b>Control:</b>
• <code>/stop</code> - Stop monitoring
• <code>/help</code> - Show this help

<b>Example:</b>
<code>/add https://example.com</code>
<code>/interval 600</code> (10 minutes)"""

    def handle_add_url(self, args):
        """Handle /add command"""
        if not args:
            return "❌ Please provide a URL to add\n\nExample: <code>/add https://example.com</code>"

        url = args[0]
        if not url.startswith(('http://', 'https://')):
            return "❌ URL must start with http:// or https://"

        if self.url_manager.add_url(url):
            return f"✅ Added URL to monitor:\n{self.escape_html(url)}"
        else:
            return f"⚠️ URL already being monitored:\n{self.escape_html(url)}"

    def handle_remove_url(self, args):
        """Handle /remove command"""
        if not args:
            return "❌ Please provide a URL to remove\n\nExample: <code>/remove https://example.com</code>"

        url = args[0]
        if self.url_manager.remove_url(url):
            return f"✅ Removed URL from monitoring:\n{self.escape_html(url)}"
        else:
            return f"❌ URL not found in monitoring list:\n{self.escape_html(url)}"

    def handle_list_urls(self):
        """Handle /list command"""
        if not self.url_manager.urls:
            return "📝 No URLs currently being monitored\n\nUse <code>/add &lt;url&gt;</code> to add some!"

        url_list = "\n".join(f"• {self.escape_html(url)}" for url in self.url_manager.urls)
        return f"📋 <b>Monitored URLs ({len(self.url_manager.urls)}):</b>\n{url_list}"

    def handle_clear_urls(self):
        """Handle /clear command"""
        count = len(self.url_manager.urls)
        self.url_manager.clear_urls()
        return f"🗑️ Cleared all URLs from monitoring ({count} removed)"

    def handle_set_interval(self, args):
        """Handle /interval command"""
        if not args:
            return f"⚙️ Current check interval: {self.url_manager.interval} seconds ({self.url_manager.interval//60} minutes)\n\nUse <code>/interval &lt;seconds&gt;</code> to change"

        try:
            new_interval = int(args[0])
            if new_interval < 30:
                return "❌ Interval must be at least 30 seconds"
            self.url_manager.set_interval(new_interval)
            return f"✅ Check interval set to {new_interval} seconds ({new_interval//60} minutes)"
        except ValueError:
            return "❌ Please provide a valid number of seconds"

    def handle_toggle_content(self):
        """Handle /content command"""
        new_state = self.url_manager.toggle_content_storage()
        status = "ENABLED" if new_state else "DISABLED"
        return f"📄 Content storage for diffs: {status}\n\n{'✅ Will show detailed changes in notifications' if new_state else 'ℹ️ Will only show hash changes'}"

    def handle_status(self):
        """Handle /status command"""
        status = f"""📊 <b>WebHawkBot Status</b>

<b>Monitoring:</b> {'🟢 ACTIVE' if self.running else '🔴 STOPPED'}
<b>URLs:</b> {len(self.url_manager.urls)}
<b>Check Interval:</b> {self.url_manager.interval}s ({self.url_manager.interval//60}min)
<b>Content Storage:</b> {'✅ Enabled' if self.url_manager.store_content else '❌ Disabled'}
<b>Last Config Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>URLs:</b>
{self.handle_list_urls() if self.url_manager.urls else 'None'}"""

        return status

    def handle_stop(self):
        """Handle /stop command"""
        self.running = False
        return "🛑 Monitoring stopped. Use the script to restart."

    def get_updates(self, offset=None):
        """Get updates from Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get updates: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error getting updates: {e}")
            return None

    def process_updates(self):
        """Process incoming Telegram updates"""
        # Use a class variable to track the last update ID
        if not hasattr(self, 'last_update_id'):
            self.last_update_id = 0

        updates = self.get_updates(offset=self.last_update_id + 1)
        if updates and updates.get("ok"):
            result_count = len(updates.get("result", []))
            if result_count > 0:
                print(f"📨 Received {result_count} update(s) from Telegram")

            for update in updates.get("result", []):
                self.last_update_id = update["update_id"]
                print(f"🔍 Processing update ID: {update['update_id']}")

                # Handle both regular messages and channel posts
                message = None
                if "message" in update:
                    message = update["message"]
                    print("📨 Received regular message")
                elif "channel_post" in update:
                    message = update["channel_post"]
                    print("📢 Received channel post")

                if message:
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")

                    print(f"📨 Message from chat {chat_id}: '{text}' (configured chat: {self.chat_id})")

                    # Only respond to messages from our configured chat
                    if str(chat_id) == str(self.chat_id):
                        if text.startswith('/'):
                            print(f"⚡ Processing command: {text}")
                            response = self.process_command(text)
                            print(f"📤 Sending response: {response[:100]}...")
                            self.send_telegram_message(response)
                        else:
                            print(f"ℹ️  Ignoring non-command message: {text}")
                    else:
                        print(f"❌ Ignoring message from unauthorized chat {chat_id}")
                else:
                    print(f"ℹ️  Update has no message or channel_post field: {update.keys()}")
        else:
            # Only print if there are actual errors
            if updates and not updates.get("ok"):
                print(f"❌ Update error: {updates.get('description', 'Unknown error')}")

    def get_updates(self, offset=None):
        """Get updates from Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {"timeout": 10}  # Shorter timeout for responsive checking
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get updates: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error getting updates: {e}")
            return None


    
    def send_telegram_message(self, message):
        """Send message via Telegram bot"""
        try:
            # Split message if it's too long (Telegram has 4096 char limit)
            max_length = 4000
            if len(message) > max_length:
                message = message[:max_length] + "\n\n... (message truncated)"
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(self.telegram_api, json=payload)
            response.raise_for_status()
            print(f"✓ Notification sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except requests.RequestException as e:
            print(f"Error sending Telegram message: {e}")
            # Try sending without HTML formatting as fallback
            try:
                # Strip HTML tags for plain text
                plain_text = message.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')
                payload_fallback = {
                    "chat_id": self.chat_id,
                    "text": plain_text
                }
                response = requests.post(self.telegram_api, json=payload_fallback)
                response.raise_for_status()
                print(f"✓ Fallback message sent (without HTML formatting)")
            except requests.RequestException as fallback_error:
                print(f"Fallback message also failed: {fallback_error}")
                # Try to validate bot token and chat_id
                try:
                    test_payload = {
                        "chat_id": self.chat_id,
                        "text": "Test message from WebHawkBot"
                    }
                    response = requests.post(self.telegram_api, json=test_payload)
                    if response.status_code == 400:
                        print("❌ Bot token or chat_id appears to be invalid")
                        print("Please check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
                    else:
                        print(f"❌ Unexpected error: {response.status_code} - {response.text}")
                except Exception as test_error:
                    print(f"❌ Could not validate credentials: {test_error}")
    
    def check_page(self, url, store_content=False):
        """Check if a webpage has changed"""
        print(f"Checking {url}...")
        
        content, status_code = self.get_page_content(url)
        if content is None or status_code is None:
            return
        
        current_hash = self.calculate_hash(content)
        
        # First time checking this URL
        if url not in self.stored_hashes:
            self.stored_hashes[url] = {
                "hash": current_hash,
                "status_code": status_code,
                "last_checked": datetime.now().isoformat()
            }
            if store_content:
                self.stored_hashes[url]["content"] = content
            self.save_hashes()
            message = f"🆕 <b>Started monitoring:</b>\n{self.escape_html(url)}\n\nStatus: {status_code}\nHash: {current_hash[:16]}..."
            self.send_telegram_message(message)
            return
        
        # Check if content or status code has changed
        content_changed = current_hash != self.stored_hashes[url]["hash"]
        status_changed = status_code != self.stored_hashes[url].get("status_code")
        
        if content_changed or status_changed:
            print(f"⚠️  Change detected on {url}")
            
            message = f"🔔 <b>PAGE CHANGE DETECTED!</b>\n\n"
            message += f"<b>URL:</b> {self.escape_html(url)}\n"
            message += f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if status_changed:
                old_status = self.stored_hashes[url].get("status_code", "Unknown")
                message += f"<b>Status Code:</b> {old_status} → {status_code}\n"
            else:
                message += f"<b>Status Code:</b> {status_code}\n"
            
            if content_changed:
                message += f"<b>Old hash:</b> {self.stored_hashes[url]['hash'][:16]}...\n"
                message += f"<b>New hash:</b> {current_hash[:16]}...\n"
            
            # Add diff if we stored the content and content actually changed
            if content_changed and store_content and "content" in self.stored_hashes[url]:
                diff = self.get_diff(self.stored_hashes[url]["content"], content)
                message += f"\n<b>Content Changes:</b>\n<code>{self.escape_html(diff[:500])}</code>"
            elif status_changed and not content_changed:
                message += f"\n<b>Note:</b> Only status code changed, content remains the same"
            
            self.send_telegram_message(message)
            
            # Update stored hash and status code
            self.stored_hashes[url]["hash"] = current_hash
            self.stored_hashes[url]["status_code"] = status_code
            self.stored_hashes[url]["last_checked"] = datetime.now().isoformat()
            if store_content:
                self.stored_hashes[url]["content"] = content
            self.save_hashes()
        else:
            print(f"✓ No changes detected")
            self.stored_hashes[url]["last_checked"] = datetime.now().isoformat()
            self.save_hashes()
    
    def monitor(self):
        """
        Monitor URLs continuously with command processing
        """
        self.running = True
        print(f"Starting webpage monitor...")
        print(f"Monitoring {len(self.url_manager.urls)} URL(s) every {self.url_manager.interval} seconds")
        print(f"Content storage: {'Enabled' if self.url_manager.store_content else 'Disabled'}")
        print(f"Press Ctrl+C to stop\n")

        # Send initial status
        self.send_telegram_message(f"🟢 <b>WebHawkBot Started</b>\n\n{self.handle_status()}")

        try:
            while self.running:
                # Check URLs if any are configured
                if self.url_manager.urls:
                    for url in self.url_manager.urls:
                        if not self.running:  # Check if we should stop
                            break
                        self.check_page(url, store_content=self.url_manager.store_content)

                # Wait for next check or process commands
                wait_time = self.url_manager.interval if self.url_manager.urls else 60
                start_time = time.time()

                while time.time() - start_time < wait_time and self.running:
                    # Process any pending commands
                    self.process_updates()
                    time.sleep(1)

                if self.url_manager.urls:
                    print(f"\nWaiting {self.url_manager.interval} seconds until next check...\n")

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        finally:
            self.running = False
            self.send_telegram_message("🔴 <b>WebHawkBot Stopped</b>")


# Example usage
if __name__ == "__main__":
    # Load credentials from environment variables
    # Works with both .env file (local) and environment variables (Docker/Dockploy)
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Validate credentials
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: Missing credentials!")
        print("\nFor local development, create a .env file:")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("  TELEGRAM_CHAT_ID=your_chat_id_here")
        print("\nFor Docker/Dockploy, set environment variables in your deployment config")
        exit(1)
    
    print("✓ Credentials loaded successfully")
    
    # Create URL manager and monitor
    url_manager = URLManager()
    monitor = WebpageMonitor(BOT_TOKEN, CHAT_ID, url_manager)
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        print("\n\n� Received shutdown signal...")
        monitor.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("\n�🚀 Starting WebHawkBot webpage monitor...")
    
    # If no URLs configured, show helpful message
    if not url_manager.urls:
        print("ℹ️  No URLs configured. Use Telegram commands to add URLs:")
        print("   /add <url> - Add a URL to monitor")
        print("   /help - Show all commands")
    
    # Start monitoring with command processing
    monitor.monitor()