import os
import logging
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import sqlite3
import requests

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# ENV Variables
# -------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "apmarket21")
AI_API_TOKEN = os.environ.get("AI_API_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7321524568"))

DB_PATH = "orders.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in Railway ENV")

# -------------------------------
# Init Bot
# -------------------------------
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# -------------------------------
# Sample Database
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id TEXT PRIMARY KEY,
            customer TEXT,
            status TEXT,
            updated TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?)",
              ("ORDER12345", "علی رضایی", "در حال پردازش", "2025-11-28 14:20"))
    c.execute("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?)",
              ("ORDER77777", "مریم احمدی", "ارسال شده", "2025-11-27 09:12"))
    conn.commit()
    conn.close()

def lookup_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "customer": row[1],
        "status": row[2],
        "updated": row[3],
    }

# -------------------------------
# FAQ LIST
# -------------------------------
FAQ = {
    "پرداخت": {
        "چگونه باید پرداخت کنم؟": "از طریق درگاه بانکی معتبر امکان پرداخت وجود دارد.",
        "آیا پرداخت در محل دارید؟": "در حال حاضر خیر."
    },
    "ارسال": {
        "ارسال چقدر طول می‌کشد؟": "بین 1 تا 5 روز کاری بسته به شهر مقصد.",
        "هزینه ارسال چقدر است؟": "در صفحه تسویه حساب محاسبه می‌شود."
    }
}

# -------------------------------
# AI Function
# -------------------------------
def ai_answer(prompt):
    if not AI_API_TOKEN:
        return "سرویس هوش مصنوعی غیرفعال است."

    try:
        r = requests.post(
            "https://api.example-ai.com/generate",
            json={"prompt": prompt, "max_tokens": 300},
            headers={"Authorization": f"Bearer {AI_API_TOKEN}"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("text", "پاسخی دریافت نشد.")
        return "خطا در پاسخ‌دهی AI"
    except:
        return "خطای ارتباط با موتور هوش مصنوعی"

# -------------------------------
# Handlers
# -------------------------------

def start(update, context):
    keyboard = [
        [InlineKeyboardButton("سوالات متداول", callback_data="faq")],
        [InlineKeyboardButton("پیگیری سفارش", callback_data="track")],
        [InlineKeyboardButton("پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("پرسش هوش مصنوعی", callback_data="ai")],
    ]
    update.message.reply_text(
        "سلام، به ربات فروشگاه خوش آمدید.\nچطور می‌تونم کمکت کنم؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def faq_menu(update, context):
    q = update.callback_query
    q.answer()

    kb = [[InlineKeyboardButton(cat, callback_data=f"faqcat::{cat}")]]
    for cat in FAQ:
        kb.append([InlineKeyboardButton(cat, callback_data=f"faqcat::{cat}")])

    q.edit_message_text("دسته‌بندی FAQ:", reply_markup=InlineKeyboardMarkup(kb))

def faq_category(update, context):
    q = update.callback_query
    q.answer()

    _, cat = q.data.split("::")
    kb = []
    for question in FAQ[cat]:
        kb.append([InlineKeyboardButton(question, callback_data=f"faqitem::{cat}::{question}")])

    q.edit_message_text(f"سوالات دسته {cat}:", reply_markup=InlineKeyboardMarkup(kb))

def faq_item(update, context):
    q = update.callback_query
    q.answer()
    _, cat, qs = q.data.split("::")

    answer = FAQ[cat][qs]

    kb = [
        [InlineKeyboardButton("پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]

    q.edit_message_text(
        f"*سوال:* {qs}\n\n*پاسخ:* {answer}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )

def track(update, context):
    q = update.callback_query
    q.answer()
    q.message.reply_text("شماره سفارش را وارد کنید:")
    context.user_data["await_order"] = True

def ai_question(update, context):
    q = update.callback_query
    q.answer()
    q.message.reply_text("سوال خود را اینگونه ارسال کنید:\n\n!ai سوال شما")

def text_handler(update, context):
    text = update.message.text.strip()

    # پیگیری سفارش
    if context.user_data.get("await_order"):
        context.user_data["await_order"] = False
        info = lookup_order(text)
        if info:
            update.message.reply_text(
                f"سفارش یافت شد:\n"
                f"کد: {info['id']}\n"
                f"مشتری: {info['customer']}\n"
                f"وضعیت: {info['status']}\n"
                f"آپدیت: {info['updated']}"
            )
        else:
            update.message.reply_text("سفارش پیدا نشد.")

        return

    # AI
    if text.startswith("!ai "):
        question = text[4:].strip()
        update.message.reply_text("در حال پردازش...")
        update.message.reply_text(ai_answer(question))
        return

    update.message.reply_text("برای شروع /start را بزنید.")

# -------------------------------
# Register Handlers
# -------------------------------
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(faq_menu, pattern="^faq$"))
dispatcher.add_handler(CallbackQueryHandler(faq_category, pattern="^faqcat::"))
dispatcher.add_handler(CallbackQueryHandler(faq_item, pattern="^faqitem::"))
dispatcher.add_handler(CallbackQueryHandler(track, pattern="^track$"))
dispatcher.add_handler(CallbackQueryHandler(ai_question, pattern="^ai$"))
dispatcher.add_handler(MessageHandler(Filters.text, text_handler))

# -------------------------------
# Webhook
# -------------------------------
@app.route("/")
def home():
    return "Bot is running."

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# -------------------------------
# Start
# -------------------------------
if __name__ == "__main__":
    init_db()
    if WEBHOOK_URL:
        bot.set_webhook(f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=8000)
