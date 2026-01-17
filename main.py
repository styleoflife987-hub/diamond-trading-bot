import asyncio
import nest_asyncio
import pandas as pd
import boto3
import re
from io import BytesIO
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import types
import os
import json
import pytz
import uuid
from openai import OpenAI



# ---------------- DEAL STATE VALIDATION ----------------

def is_valid_deal_state(deal: dict) -> bool:
    supplier_action = deal.get("supplier_action")
    admin_action = deal.get("admin_action")
    final_status = deal.get("final_status")

    valid_states = {
        ("PENDING", "PENDING", "OPEN"),
        ("ACCEPTED", "PENDING", "OPEN"),
        ("REJECTED", "REJECTED", "CLOSED"),
        ("ACCEPTED", "APPROVED", "COMPLETED"),
        ("ACCEPTED", "REJECTED", "CLOSED"),
    }

    return (supplier_action, admin_action, final_status) in valid_states



# ---------------- CONFIG ----------------

TOKEN = "8438406844:AAFlKgi25TvbFnsUgcbBysjrnTc4Z7s6wrU"
AWS_ACCESS_KEY = "AKIA3SFAMUMTLVXXXJVY"
AWS_SECRET_KEY = "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"
AWS_BUCKET = "diamond-bucket-styleoflifes"
AWS_REGION = "ap-south-1"

# ---------------- OPENAI ----------------

openai_client = OpenAI(
    api_key=os.getenv("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")
)

ACCOUNTS_KEY = "users/accounts.xlsx"
STOCK_KEY = "stock/diamonds.xlsx"

SUPPLIER_STOCK_FOLDER = "stock/suppliers/"
COMBINED_STOCK_KEY = "stock/combined/all_suppliers_stock.xlsx"
ACTIVITY_LOG_FOLDER = "activity_logs/"
DEALS_FOLDER = "deals/"
DEAL_HISTORY_KEY = "deals/deal_history.xlsx"
NOTIFICATIONS_FOLDER = "notifications/"


# ---------------- BOT INIT ----------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------------- AWS ----------------

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# ---------------- KEYBOARDS ----------------
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

