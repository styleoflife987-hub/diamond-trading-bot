import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Get webhook URL from environment variable or use default
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app-url.herokuapp.com/webhook")

def update_webhook():
    """Update Telegram webhook URL"""
    try:
        # First, delete any existing webhook
        delete_response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            timeout=10
        )
        print("Delete webhook response:", delete_response.json())
        
        # Set new webhook
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": WEBHOOK_URL},
            timeout=10
        )
        
        print("=" * 50)
        print("Webhook Update Status")
        print("=" * 50)
        print(f"Status Code: {response.status_code}")
        print(f"Webhook URL: {WEBHOOK_URL}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and response.json().get("ok"):
            print("✅ Webhook updated successfully!")
        else:
            print("❌ Failed to update webhook")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error updating webhook: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def get_webhook_info():
    """Get current webhook information"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
            timeout=10
        )
        
        print("=" * 50)
        print("Current Webhook Info")
        print("=" * 50)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        if data.get("ok"):
            info = data.get("result", {})
            print(f"URL: {info.get('url', 'Not set')}")
            print(f"Has custom certificate: {info.get('has_custom_certificate', False)}")
            print(f"Pending update count: {info.get('pending_update_count', 0)}")
            print(f"Last error date: {info.get('last_error_date', 'Never')}")
            print(f"Last error message: {info.get('last_error_message', 'None')}")
            print(f"Max connections: {info.get('max_connections', 40)}")
            print(f"Allowed updates: {info.get('allowed_updates', [])}")
        else:
            print(f"Error: {data.get('description', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")

if __name__ == "__main__":
    print("🤖 Telegram Bot Webhook Manager")
    print("=" * 50)
    
    # Show current webhook info
    get_webhook_info()
    print("\n")
    
    # Update webhook
    update_response = input("Do you want to update the webhook? (y/n): ").lower()
    if update_response == 'y':
        print("\n")
        update_webhook()
