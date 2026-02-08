import requests
import json

# Your bot token
BOT_TOKEN = "7965048668:AAHFhqx-u5lVJk4Z5yuBOyBOzVwGQqD3ZK0"
WEBHOOK_URL = "https://telegram-bot-6iil.onrender.com/webhook"

def setup_telegram_webhook():
    print("🤖 Setting up Telegram Webhook...")
    print(f"Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print("-" * 60)
    
    # 1. Get current webhook info
    print("📡 Getting current webhook info...")
    try:
        info_response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
            timeout=10
        )
        info_data = info_response.json()
        if info_data.get("ok"):
            current_url = info_data["result"].get("url", "Not set")
            print(f"Current webhook URL: {current_url}")
    except Exception as e:
        print(f"⚠️ Could not get webhook info: {e}")
    
    # 2. Delete existing webhook
    print("\n🗑️ Deleting existing webhook...")
    try:
        delete_response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            timeout=10
        )
        delete_data = delete_response.json()
        if delete_data.get("ok"):
            print("✅ Existing webhook deleted")
    except Exception as e:
        print(f"⚠️ Error deleting webhook: {e}")
    
    # 3. Set new webhook
    print(f"\n📡 Setting webhook to: {WEBHOOK_URL}")
    try:
        webhook_data = {
            "url": WEBHOOK_URL,
            "max_connections": 50,
            "allowed_updates": ["message", "callback_query", "chat_member"],
            "drop_pending_updates": True
        }
        
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json=webhook_data,
            timeout=30
        )
        
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {result}")
        
        if result.get("ok"):
            print("\n" + "="*60)
            print("✅ WEBHOOK SETUP SUCCESSFUL!")
            print("="*60)
            print(f"Your bot is now connected to:")
            print(f"{WEBHOOK_URL}")
            print("\n🎉 Telegram will now send updates to your bot!")
        else:
            print(f"\n❌ Failed: {result.get('description')}")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    
    # 4. Test bot connection
    print("\n🔧 Testing bot connection...")
    try:
        test_response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
            timeout=10
        )
        test_data = test_response.json()
        if test_data.get("ok"):
            bot_info = test_data["result"]
            print(f"✅ Bot is working!")
            print(f"   Name: {bot_info['first_name']}")
            print(f"   Username: @{bot_info.get('username', 'N/A')}")
            print(f"   ID: {bot_info['id']}")
    except Exception as e:
        print(f"❌ Bot test failed: {e}")

if __name__ == "__main__":
    setup_telegram_webhook()
    print("\n📋 Next steps:")
    print("1. Open Telegram and search for your bot")
    print("2. Start with /start command")
    print("3. Login as admin with username: admin, password: admin123")
    print("4. Start using your Diamond Trading Bot! 💎")
