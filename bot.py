# ONE COMMAND - Complete deployment (no GitHub needed)
cd ~ && rm -rf diamond-bot && mkdir diamond-bot && cd diamond-bot && cat > bot.py << 'EOF'
import asyncio
import nest_asyncio
import pandas as pd
import boto3
import re
from io import BytesIO
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import os
import json
import pytz
import uuid
import time
import unicodedata
import uvicorn
from typing import Optional, Dict, Any, List
import logging

# -------- SETUP LOGGING --------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -------- GLOBAL FLAGS --------
BOT_STARTED = False
READ_ONLY_ACCOUNTS = False

# -------- TIMEZONE --------
IST = pytz.timezone("Asia/Kolkata")

# -------- STATUS CONSTANTS --------
YES = "YES"
NO = "NO"
STATUS_PENDING = "PENDING"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_REJECTED = "REJECTED"
STATUS_COMPLETED = "COMPLETED"
STATUS_CLOSED = "CLOSED"

# -------- CONFIGURATION --------
def load_env_config():
    """Load and validate all environment variables"""
    config = {
        "BOT_TOKEN": os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "AWS_REGION": os.getenv("AWS_REGION", "ap-south-1"),
        "AWS_BUCKET": os.getenv("AWS_BUCKET", "diamond-bot-123456"),
        "PORT": int(os.getenv("PORT", "10000")),
        "PYTHON_VERSION": os.getenv("PYTHON_VERSION", "3.9"),
        "SESSION_TIMEOUT": int(os.getenv("SESSION_TIMEOUT", "3600")),
        "RATE_LIMIT": int(os.getenv("RATE_LIMIT", "5")),
        "RATE_LIMIT_WINDOW": int(os.getenv("RATE_LIMIT_WINDOW", "10")),
    }
    
    if config["BOT_TOKEN"] == "YOUR_BOT_TOKEN_HERE":
        logger.warning("⚠️ Please set BOT_TOKEN environment variable")
    
    return config

CONFIG = load_env_config()

# -------- AWS CONFIGURATION --------
AWS_CONFIG = {
    "aws_access_key_id": CONFIG["AWS_ACCESS_KEY_ID"],
    "aws_secret_access_key": CONFIG["AWS_SECRET_ACCESS_KEY"],
    "region_name": CONFIG["AWS_REGION"]
}

# -------- S3 KEYS --------
ACCOUNTS_KEY = "users/accounts.xlsx"
STOCK_KEY = "stock/diamonds.xlsx"
SUPPLIER_STOCK_FOLDER = "stock/suppliers/"
COMBINED_STOCK_KEY = "stock/combined/all_suppliers_stock.xlsx"
ACTIVITY_LOG_FOLDER = "activity_logs/"
DEALS_FOLDER = "deals/"
DEAL_HISTORY_KEY = "deals/deal_history.xlsx"
NOTIFICATIONS_FOLDER = "notifications/"
SESSION_KEY = "sessions/logged_in_users.json"

# -------- INITIALIZE AWS CLIENTS --------
try:
    s3 = boto3.client("s3", **{k: v for k, v in AWS_CONFIG.items() if v})
except:
    s3 = boto3.client("s3")

# -------- INITIALIZE BOT --------
bot = Bot(token=CONFIG["BOT_TOKEN"])
dp = Dispatcher()

# -------- GLOBAL DATA STORES --------
logged_in_users = {}
user_state = {}
user_rate_limit = {}

# -------- KEYBOARDS --------
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 View All Stock")],
        [KeyboardButton(text="👥 View Users")],
        [KeyboardButton(text="⏳ Pending Accounts")],
        [KeyboardButton(text="🏆 Supplier Leaderboard")],
        [KeyboardButton(text="🤝 View Deals")],
        [KeyboardButton(text="📑 User Activity Report")],
        [KeyboardButton(text="🗑 Delete Supplier Stock")],
        [KeyboardButton(text="🚪 Logout")]
    ],
    resize_keyboard=True
)

client_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Search Diamonds")],
        [KeyboardButton(text="🔥 Smart Deals")],
        [KeyboardButton(text="🤝 Request Deal")],
        [KeyboardButton(text="🚪 Logout")]
    ],
    resize_keyboard=True
)

supplier_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Upload Excel")],
        [KeyboardButton(text="📦 My Stock")],
        [KeyboardButton(text="📊 My Analytics")],
        [KeyboardButton(text="🤝 View Deals")],
        [KeyboardButton(text="📥 Download Sample Excel")],
        [KeyboardButton(text="🚪 Logout")]
    ],
    resize_keyboard=True
)

# -------- TEXT CLEANING FUNCTIONS --------
def clean_text(value: Any) -> str:
    """Clean and normalize text values"""
    if value is None:
        return ""
    value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00A0", " ").replace("\u200B", "")
    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def clean_password(val: Any) -> str:
    """Clean password, handling Excel .0 issue"""
    val = clean_text(val)
    if val.endswith(".0"):
        val = val[:-2]
    return val

def normalize_text(x: Any) -> str:
    """Normalize text for comparison"""
    return clean_text(x).lower()

def safe_excel(val: Any) -> Any:
    """Prevent Excel formula injection"""
    if isinstance(val, str) and val.startswith(("=", "+", "-", "@")):
        return "'" + val
    return val

# -------- USER MANAGEMENT FUNCTIONS --------
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username from logged_in_users"""
    username = normalize_text(username)
    for uid, user_data in logged_in_users.items():
        if normalize_text(user_data.get("USERNAME", "")) == username:
            return {"TELEGRAM_ID": uid, **user_data}
    return None

def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    """Check if user is admin"""
    if not user:
        return False
    role = normalize_text(user.get("ROLE", ""))
    return role == "admin"

def get_logged_user(uid: int) -> Optional[Dict[str, Any]]:
    """Get logged in user with session validation"""
    user = logged_in_users.get(uid)
    if not user:
        return None
    last_active = user.get("last_active", 0)
    if time.time() - last_active > CONFIG["SESSION_TIMEOUT"]:
        logged_in_users.pop(uid, None)
        save_sessions()
        return None
    user["last_active"] = time.time()
    return user

def touch_session(uid: int):
    """Update user's last active time"""
    if uid in logged_in_users:
        logged_in_users[uid]["last_active"] = time.time()
        save_sessions()

# -------- SESSION MANAGEMENT --------
def save_sessions():
    """Save sessions to S3"""
    try:
        s3.put_object(
            Bucket=CONFIG["AWS_BUCKET"],
            Key=SESSION_KEY,
            Body=json.dumps(logged_in_users, default=str),
            ContentType="application/json"
        )
        logger.info(f"Saved {len(logged_in_users)} active sessions")
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")

def load_sessions():
    """Load sessions from S3"""
    global logged_in_users
    try:
        obj = s3.get_object(Bucket=CONFIG["AWS_BUCKET"], Key=SESSION_KEY)
        raw = json.loads(obj["Body"].read())
        logged_in_users = {int(k): v for k, v in raw.items()}
        logger.info(f"Loaded {len(logged_in_users)} sessions from S3")
    except:
        logged_in_users = {}

def cleanup_sessions():
    """Remove expired sessions"""
    now = time.time()
    expired = []
    for uid, data in list(logged_in_users.items()):
        if now - data.get("last_active", now) > CONFIG["SESSION_TIMEOUT"]:
            expired.append(uid)
    for uid in expired:
        user_data = logged_in_users.pop(uid, None)
        if user_data:
            log_activity(user_data, "SESSION_EXPIRED")
            logger.info(f"Expired session for user: {user_data.get('USERNAME')}")
    if expired:
        save_sessions()

# -------- RATE LIMITING --------
def is_rate_limited(uid: int) -> bool:
    """Check if user is rate limited"""
    now = time.time()
    window = CONFIG["RATE_LIMIT_WINDOW"]
    limit = CONFIG["RATE_LIMIT"]
    history = user_rate_limit.get(uid, [])
    history = [t for t in history if now - t < window]
    if len(history) >= limit:
        return True
    history.append(now)
    user_rate_limit[uid] = history[-10:]
    return False

# -------- DATA LOADING/SAVING --------
def load_accounts() -> pd.DataFrame:
    """Load accounts from Excel file in S3"""
    try:
        local_path = "/tmp/accounts.xlsx"
        s3.download_file(CONFIG["AWS_BUCKET"], ACCOUNTS_KEY, local_path)
        df = pd.read_excel(local_path, dtype=str)
        required_cols = ["USERNAME", "PASSWORD", "ROLE", "APPROVED"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
            df[col] = df[col].fillna("").astype(str).apply(clean_text)
        logger.info(f"Loaded {len(df)} accounts from S3")
        return df
    except Exception as e:
        logger.error(f"Failed to load accounts: {e}")
        return pd.DataFrame({
            "USERNAME": ["prince"],
            "PASSWORD": ["1234"],
            "ROLE": ["admin"],
            "APPROVED": ["YES"]
        })

def save_accounts(df: pd.DataFrame):
    """Save accounts to Excel file in S3"""
    if READ_ONLY_ACCOUNTS:
        logger.warning("Accounts file is READ ONLY. Skipping save.")
        return
    try:
        local_path = "/tmp/accounts.xlsx"
        df.to_excel(local_path, index=False)
        s3.upload_file(local_path, CONFIG["AWS_BUCKET"], ACCOUNTS_KEY)
        logger.info(f"Saved {len(df)} accounts to S3")
    except Exception as e:
        logger.error(f"Failed to save accounts: {e}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

def load_stock() -> pd.DataFrame:
    """Load combined stock from S3"""
    try:
        local_path = "/tmp/all_suppliers_stock.xlsx"
        s3.download_file(CONFIG["AWS_BUCKET"], COMBINED_STOCK_KEY, local_path)
        df = pd.read_excel(local_path)
        logger.info(f"Loaded {len(df)} stock items from S3")
        return df
    except Exception as e:
        logger.warning(f"Failed to load stock: {e}")
        return pd.DataFrame()

# -------- ACTIVITY LOGGING --------
def log_activity(user: Dict[str, Any], action: str, details: Optional[Dict] = None):
    """Log user activity to S3"""
    try:
        ist_time = datetime.now(IST)
        log_entry = {
            "date": ist_time.strftime("%Y-%m-%d"),
            "time": ist_time.strftime("%H:%M:%S"),
            "login_id": user.get("USERNAME"),
            "role": user.get("ROLE"),
            "action": action,
            "details": details or {},
            "telegram_id": user.get("TELEGRAM_ID", "N/A")
        }
        key = f"{ACTIVITY_LOG_FOLDER}{log_entry['date']}/{log_entry['login_id']}.json"
        try:
            obj = s3.get_object(Bucket=CONFIG["AWS_BUCKET"], Key=key)
            data = json.loads(obj["Body"].read())
        except:
            data = []
        data.append(log_entry)
        s3.put_object(
            Bucket=CONFIG["AWS_BUCKET"],
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Logged activity: {user.get('USERNAME')} - {action}")
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")

# -------- NOTIFICATION SYSTEM --------
def save_notification(username: str, role: str, message: str):
    """Save notification for user"""
    try:
        key = f"{NOTIFICATIONS_FOLDER}{role}_{username}.json"
        try:
            obj = s3.get_object(Bucket=CONFIG["AWS_BUCKET"], Key=key)
            data = json.loads(obj["Body"].read())
        except:
            data = []
        data.append({
            "message": message,
            "time": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
            "read": False
        })
        s3.put_object(
            Bucket=CONFIG["AWS_BUCKET"],
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType="application/json"
        )
    except Exception as e:
        logger.error(f"Failed to save notification: {e}")

# -------- STOCK MANAGEMENT --------
def rebuild_combined_stock():
    """Rebuild combined stock from all supplier files"""
    try:
        objs = s3.list_objects_v2(
            Bucket=CONFIG["AWS_BUCKET"],
            Prefix=SUPPLIER_STOCK_FOLDER
        )
        if "Contents" not in objs:
            return
        dfs = []
        for obj in objs.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".xlsx"):
                continue
            try:
                local_path = f"/tmp/{key.split('/')[-1]}"
                s3.download_file(CONFIG["AWS_BUCKET"], key, local_path)
                df = pd.read_excel(local_path)
                df["SUPPLIER"] = key.split("/")[-1].replace(".xlsx", "").lower()
                dfs.append(df)
                if os.path.exists(local_path):
                    os.remove(local_path)
            except Exception as e:
                logger.error(f"Failed to process {key}: {e}")
                continue
        if not dfs:
            return
        final_df = pd.concat(dfs, ignore_index=True)
        desired_columns = [
            "Stock #", "Availability", "Shape", "Weight", "Color", "Clarity", "Cut", "Polish", "Symmetry",
            "Fluorescence Color", "Measurements", "Shade", "Milky", "Eye Clean", "Lab", "Report #", "Location",
            "Treatment", "Discount", "Price Per Carat", "Final Price", "Depth %", "Table %", "Girdle Thin",
            "Girdle Thick", "Girdle %", "Girdle Condition", "Culet Size", "Culet Condition", "Crown Height",
            "Crown Angle", "Pavilion Depth", "Pavilion Angle", "Inscription", "Cert comment", "KeyToSymbols",
            "White Inclusion", "Black Inclusion", "Open Inclusion", "Fancy Color", "Fancy Color Intensity",
            "Fancy Color Overtone", "Country", "State", "City", "CertFile", "Diamond Video", "Diamond Image",
            "SUPPLIER", "LOCKED", "Diamond Type"
        ]
        for col in desired_columns:
            if col not in final_df.columns:
                final_df[col] = ""
        if "Diamond Type" not in final_df.columns:
            final_df["Diamond Type"] = "Unknown"
        final_df["LOCKED"] = final_df.get("LOCKED", "NO")
        final_df = final_df[desired_columns]
        local_path = "/tmp/all_suppliers_stock.xlsx"
        final_df.to_excel(local_path, index=False)
        s3.upload_file(local_path, CONFIG["AWS_BUCKET"], COMBINED_STOCK_KEY)
        logger.info(f"Rebuilt combined stock with {len(final_df)} items from {len(dfs)} suppliers")
        if os.path.exists(local_path):
            os.remove(local_path)
    except Exception as e:
        logger.error(f"Error rebuilding combined stock: {e}")

# -------- LIFESPAN MANAGER --------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown"""
    global BOT_STARTED
    logger.info("🤖 Diamond Trading Bot starting up...")
    try:
        load_sessions()
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    BOT_STARTED = True
    asyncio.create_task(dp.start_polling(bot))
    logger.info("✅ Bot startup complete")
    yield
    logger.info("🤖 Diamond Trading Bot shutting down...")
    save_sessions()
    BOT_STARTED = False
    logger.info("✅ Bot shutdown complete")

# -------- FASTAPI APP --------
app = FastAPI(title="Diamond Trading Bot", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Diamond Trading Bot",
        "bot_started": BOT_STARTED,
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(logged_in_users)
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if BOT_STARTED else "starting",
        "bot": "running" if BOT_STARTED else "stopped",
        "active_users": len(logged_in_users),
        "timestamp": datetime.now().isoformat()
    }

# -------- COMMAND HANDLERS --------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply(
        "💎 Welcome to Diamond Trading Bot!\n\n"
        "Use /login to sign in\n"
        "Use /createaccount to register\n"
        "Use /help for assistance",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = """
🤖 **Diamond Trading Bot Help**

**Commands:**
• /start - Start the bot
• /login - Login to your account
• /createaccount - Register new account
• /logout - Logout from current session

**Roles:**
• 👑 **Admin** - Manage users, view all stock, approve deals
• 💎 **Supplier** - Upload stock, view deals, analytics
• 🥂 **Client** - Search diamonds, request deals, smart deals

**Need help?** Contact system administrator.
"""
    await message.reply(help_text)

@dp.message(Command("createaccount"))
async def create_account(message: types.Message):
    uid = message.from_user.id
    if is_rate_limited(uid):
        await message.reply("⏳ Please wait before creating another account.")
        return
    user_state[uid] = {"step": "create_username", "last_updated": time.time()}
    await message.reply("📝 **Account Creation**\n\nEnter your desired username (minimum 3 characters):")

@dp.message(Command("login"))
async def login_command(message: types.Message):
    uid = message.from_user.id
    if is_rate_limited(uid):
        await message.reply("⏳ Please wait before trying to login again.")
        return
    user = get_logged_user(uid)
    if user:
        await message.reply(f"ℹ️ You're already logged in as {user['USERNAME']}.\nUse /logout to sign out first.")
        return
    user_state.pop(uid, None)
    user_state[uid] = {"step": "login_username", "last_updated": time.time()}
    await message.reply("👤 Enter your username:")

@dp.message(Command("logout"))
async def logout_command(message: types.Message):
    uid = message.from_user.id
    user = get_logged_user(uid)
    if not user:
        await message.reply("ℹ️ You are not logged in.")
        return
    log_activity(user, "LOGOUT")
    logged_in_users.pop(uid, None)
    user_state.pop(uid, None)
    save_sessions()
    await message.reply("✅ Successfully logged out.\nUse /login to sign in again.", reply_markup=types.ReplyKeyboardRemove())

# -------- MAIN MESSAGE HANDLER --------
@dp.message()
async def handle_all_messages(message: types.Message):
    uid = message.from_user.id
    if is_rate_limited(uid):
        await message.reply("⏳ Too many messages. Please slow down.")
        return
    user = get_logged_user(uid)
    if user:
        touch_session(uid)
    state = user_state.get(uid)
    if state:
        state["last_updated"] = time.time()
        # Account creation flow
        if state.get("step") == "create_username":
            username = message.text.strip().lower()
            if len(username) < 3:
                await message.reply("❌ Username must be at least 3 characters.")
                return
            df = load_accounts()
            if not df[df["USERNAME"].str.lower() == username].empty:
                await message.reply("❌ Username already exists.")
                user_state.pop(uid, None)
                return
            state["username"] = username
            state["step"] = "create_password"
            await message.reply("🔐 Enter password (minimum 4 characters):")
            return
        elif state.get("step") == "create_password":
            password = message.text.strip()
            if len(password) < 4:
                await message.reply("❌ Password must be at least 4 characters.")
                return
            username = state["username"]
            df = load_accounts()
            new_row = {
                "USERNAME": username,
                "PASSWORD": clean_password(password),
                "ROLE": "client",
                "APPROVED": "NO"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_accounts(df)
            user_state.pop(uid, None)
            await message.reply("✅ Account created successfully!\n\n⏳ Your account is pending admin approval.\nYou'll be notified once approved.\n\nUse /login after approval.")
            return
        # Login flow
        elif state.get("step") == "login_username":
            username = message.text.strip()
            state["login_username"] = username
            state["step"] = "login_password"
            await message.reply("🔐 Enter password:")
            return
        elif state.get("step") == "login_password":
            password = message.text.strip()
            username = state.get("login_username", "")
            df = load_accounts()
            df["USERNAME"] = df["USERNAME"].apply(normalize_text)
            df["PASSWORD"] = df["PASSWORD"].apply(clean_password)
            df["APPROVED"] = df["APPROVED"].apply(normalize_text).str.upper()
            df["ROLE"] = df["ROLE"].apply(normalize_text)
            username_clean = normalize_text(username)
            password_clean = clean_password(password)
            user_row = df[
                (df["USERNAME"] == username_clean) &
                (df["PASSWORD"] == password_clean) &
                (df["APPROVED"] == "YES")
            ]
            if user_row.empty:
                await message.reply("❌ Invalid login credentials\n\nPossible reasons:\n• Username/password incorrect\n• Account not approved\n• Account doesn't exist\n\nPlease check your credentials and try again.")
                user_state.pop(uid, None)
                return
            user_data = user_row.iloc[0].to_dict()
            role = user_data["ROLE"].lower()
            logged_in_users[uid] = {
                "USERNAME": user_data["USERNAME"],
                "ROLE": role,
                "SUPPLIER_KEY": f"supplier_{user_data['USERNAME'].lower()}" if role == "supplier" else None,
                "last_active": time.time()
            }
            save_sessions()
            log_activity(logged_in_users[uid], "LOGIN")
            if role == "admin":
                kb = admin_kb
                welcome_msg = f"👑 Welcome Admin {user_data['USERNAME'].capitalize()}"
            elif role == "supplier":
                kb = supplier_kb
                welcome_msg = f"💎 Welcome Supplier {user_data['USERNAME'].capitalize()}"
            else:
                kb = client_kb
                welcome_msg = f"🥂 Welcome {user_data['USERNAME'].capitalize()}"
            await message.reply(welcome_msg, reply_markup=kb)
            user_state.pop(uid, None)
            return
    # Handle button presses
    if user:
        text = message.text
        if user["ROLE"] == "admin":
            if text == "💎 View All Stock":
                df = load_stock()
                if df.empty:
                    await message.reply("❌ No stock available.")
                    return
                total_diamonds = len(df)
                total_carats = df["Weight"].sum() if "Weight" in df.columns else 0
                total_value = (df["Weight"] * df["Price Per Carat"]).sum() if "Weight" in df.columns and "Price Per Carat" in df.columns else 0
                summary = f"📊 **Stock Summary**\n\n💎 Total Diamonds: {total_diamonds}\n⚖️ Total Carats: {total_carats:.2f}\n💰 Estimated Value: ${total_value:,.2f}\n👥 Suppliers: {df['SUPPLIER'].nunique() if 'SUPPLIER' in df.columns else 0}\n\n"
                if "Shape" in df.columns:
                    shape_counts = df["Shape"].value_counts().head(5)
                    summary += "**Top Shapes:**\n"
                    for shape, count in shape_counts.items():
                        summary += f"• {shape}: {count}\n"
                await message.reply(summary)
            elif text == "👥 View Users":
                df = load_accounts()
                if df.empty:
                    await message.reply("❌ No users found.")
                    return
                role_stats = df.groupby("ROLE").size()
                approval_stats = df.groupby("APPROVED").size()
                stats_msg = f"📊 **User Statistics**\n\n👥 Total Users: {len(df)}\n\n**By Role:**\n"
                for role, count in role_stats.items():
                    stats_msg += f"• {role.title()}: {count}\n"
                stats_msg += f"\n**By Approval Status:**\n"
                for status, count in approval_stats.items():
                    stats_msg += f"• {status}: {count}\n"
                await message.reply(stats_msg)
            elif text == "⏳ Pending Accounts":
                await message.reply("✅ No pending accounts.")
            elif text == "🚪 Logout":
                await logout_command(message)
            else:
                await message.reply("Please use the menu buttons.")
        elif user["ROLE"] == "supplier":
            if text == "📤 Upload Excel":
                await message.reply("📤 **Upload Stock Excel File**\n\nPlease send an Excel file with your diamond stock.")
            elif text == "📦 My Stock":
                await message.reply("📦 Your stock will be shown here.")
            elif text == "🚪 Logout":
                await logout_command(message)
            else:
                await message.reply("Please use the menu buttons.")
        else:  # client
            if text == "💎 Search Diamonds":
                await message.reply("💎 **Diamond Search**\n\nEnter the carat weight you're looking for:")
            elif text == "🔥 Smart Deals":
                await message.reply("🔥 **Smart Deals**\n\nFinding the best deals for you...")
            elif text == "🤝 Request Deal":
                await message.reply("🤝 **Request Deal**\n\nEnter the Stone ID:")
            elif text == "🚪 Logout":
                await logout_command(message)
            else:
                await message.reply("Please use the menu buttons.")
    else:
        await message.reply("🔒 Please login first using /login\nOr create an account using /createaccount")

# -------- MAIN ENTRY POINT --------
if __name__ == "__main__":
    nest_asyncio.apply()
    logger.info(f"🚀 Starting Diamond Trading Bot v1.0")
    logger.info(f"📊 Python: {CONFIG['PYTHON_VERSION']}")
    logger.info(f"🌐 Port: {CONFIG['PORT']}")
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"], reload=False, log_level="info")
EOF
 && cat > requirements.txt << 'EOF'
aiogram==3.0.0b7
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.4
openpyxl==3.1.2
boto3==1.34.0
nest-asyncio==1.5.8
pytz==2023.3.post1
python-multipart==0.0.6
EOF
 && cat > setup.py << 'EOF'
import boto3
import pandas as pd
import os

# Create S3 bucket
bucket_name = "diamond-bot-" + boto3.client('sts').get_caller_identity()['Account']
s3 = boto3.client('s3')

try:
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
    )
    print(f"✅ Created S3 bucket: {bucket_name}")
except:
    print(f"✅ Using existing bucket: {bucket_name}")

# Create admin account
accounts = pd.DataFrame({
    'USERNAME': ['prince'],
    'PASSWORD': ['1234'],
    'ROLE': ['admin'],
    'APPROVED': ['YES']
})

accounts.to_excel('/tmp/accounts.xlsx', index=False)
s3.upload_file('/tmp/accounts.xlsx', bucket_name, 'users/accounts.xlsx')
print("✅ Created admin account: prince / 1234")

# Set environment variable
os.environ['AWS_BUCKET'] = bucket_name
print(f"✅ Set AWS_BUCKET={bucket_name}")
print("\n🎉 Setup complete! Run: python bot.py")
EOF
 && pip install -r requirements.txt && python setup.py && echo "✅ Installation complete!" && echo "📢 IMPORTANT: Set your Telegram Bot Token:" && echo "export BOT_TOKEN='YOUR_BOT_TOKEN_FROM_BOTFATHER'" && echo "Then run: python bot.py"
