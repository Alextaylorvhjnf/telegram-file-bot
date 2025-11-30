#!/usr/bin/env python3
# main.py
import os
import logging
import sqlite3
import asyncio
from typing import Dict

import requests
from datetime import datetime
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- ENV ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set. Exiting.")
    raise SystemExit("BOT_TOKEN environment variable not set")

# مقادیر پیش‌فرض (قابل تغییر در ENV)
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "apmarket21")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7321524568"))
AI_API_TOKEN = os.environ.get("AI_API_TOKEN")  # اختیاری
DB_PATH = os.environ.get("DB_PATH", "orders.db")

# ---------- Sample FAQ ----------
FAQ: Dict[str, Dict[str, str]] = {
    "پرداخت": {
        "نحوه پرداخت چگونه است؟": "شما می‌توانید با کارت‌های شتاب از طریق درگاه بانکی پرداخت کنید.",
        "آیا پرداخت در محل وجود دارد؟": "در برخی مناطق پرداخت در محل فعال است؛ در صفحه تسویه بررسی کنید."
    },
    "ارسال": {
        "هزینه ارسال چقدر است؟": "هزینه ارسال به وزن و آدرس مقصد بستگی دارد و در صفحه پرداخت نمایش داده می‌شود.",
        "چقدر طول می‌کشد؟": "معمولاً بین 1 تا 5 روز کاری بسته به شهر مقصد."
    }
}

# ---------- Database helpers (SQLite sample) ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            status TEXT,
            last_update TEXT
        );
    """)
    # sample data
    cur.execute(
        "INSERT OR IGNORE INTO orders (id, customer_name, status, last_update) VALUES (?, ?, ?, ?)",
        ("ORDER12345", "علی رضایی", "در حال پردازش", "2025-11-29 12:34")
    )
    cur.execute(
        "INSERT OR IGNORE INTO orders (id, customer_name, status, last_update) VALUES (?, ?, ?, ?)",
        ("ORDER54321", "سارا موسوی", "ارسال شده", "2025-11-28 08:12")
    )
    conn.commit()
    conn.close()

def lookup_order(order_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, customer_name, status, last_update FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "customer_name": row[1],
        "status": row[2],
        "last_update": row[3],
    }

# ---------- AI helper (placeholder) ----------
def generate_ai_answer(prompt: str) -> str:
    """
    مثال: جایگزین با API واقعی شما (OpenAI یا سرویس دیگر).
    اگر توکن AI_API_TOKEN تنظیم نشده باشد، پیغام دیفالت می‌دهد.
    """
    if not AI_API_TOKEN:
        return "سرویس هوش‌مصنوعی فعال نیست. لطفاً بعداً تلاش کنید یا از گزینه‌های منو استفاده کنید."
    # نمونه‌ی درخواست (این URL فرضی است — آن را با API واقعی خود جایگزین کنید)
    try:
        resp = requests.post(
            "https://api.example-ai.com/generate",
            json={"prompt": prompt, "max_tokens": 300},
            headers={"Authorization": f"Bearer {AI_API_TOKEN}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("text", "پاسخی دریافت نشد.")
        logger.error("AI service returned %s: %s", resp.status_code, resp.text)
        return "خطا در ارتباط با سرویس هوش‌مصنوعی."
    except Exception as e:
        logger.exception("AI request failed")
        return "خطا در ارتباط با سرویس هوش‌مصنوعی."

# ---------- Bot handlers (async) ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("سؤالات متداول", callback_data="faq_main")],
        [InlineKeyboardButton("پیگیری سفارش", callback_data="track_order")],
        [InlineKeyboardButton("تماس با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("سؤال آزاد (هوش‌مصنوعی)", callback_data="ai_question")]
    ]
    text = "سلام! به ربات پشتیبانی فروشگاه خوش آمدید.\nچطور می‌تونم کمکتون کنم؟"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def faq_main_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = []
    for cat in FAQ.keys():
        kb.append([InlineKeyboardButton(cat, callback_data=f"faq_cat::{cat}")])
    kb.append([InlineKeyboardButton("برگشت", callback_data="back_main")])
    await query.edit_message_text("دسته‌بندی سؤالات متداول:", reply_markup=InlineKeyboardMarkup(kb))

async def faq_cat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat = query.data.split("::", 1)
    entries = FAQ.get(cat, {})
    if not entries:
        await query.edit_message_text("هیچ سوالی در این دسته وجود ندارد.")
        return
    kb = []
    for q in entries.keys():
        kb.append([InlineKeyboardButton(q, callback_data=f"faq_q::{cat}::{q}")])
    kb.append([InlineKeyboardButton("برگشت", callback_data="faq_main")])
    await query.edit_message_text(f"سؤالات در دستهٔ *{cat}*:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def faq_q_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, cat, q = query.data.split("::", 2)
    answer = FAQ.get(cat, {}).get(q, "پاسخی موجود نیست.")
    kb = [
        [InlineKeyboardButton("نیافتم — تماس با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("برگشت", callback_data=f"faq_cat::{cat}")]
    ]
    await query.edit_message_text(f"*سؤال:* {q}\n\n*پاسخ:* {answer}", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def back_main_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("سؤالات متداول", callback_data="faq_main")],
        [InlineKeyboardButton("پیگیری سفارش", callback_data="track_order")],
        [InlineKeyboardButton("تماس با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("سؤال آزاد (هوش‌مصنوعی)", callback_data="ai_question")]
    ]
    await query.edit_message_text("چطور می‌تونم کمکتون کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def track_order_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("لطفا شماره سفارش خود را وارد کنید (مثال: ORDER12345).")
    # علامت‌گذاری برای پیام بعدی
    context.user_data["awaiting_order"] = True

async def ai_question_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("سؤالتان را بنویسید. برای دریافت پاسخ هوش‌مصنوعی، پیام را با پیش‌وند `!ai ` شروع کنید.\nمثال: `!ai هزینه ارسال برای تهران چقدر است؟`")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id if update.effective_user else None

    # بررسی پیگیری سفارش
    if context.user_data.get("awaiting_order"):
        context.user_data.pop("awaiting_order", None)
        order_id = text
        order = lookup_order(order_id)
        if order:
            reply = (
                f"اطلاعات سفارش:\n"
                f"شناسه: {order['id']}\n"
                f"نام مشتری: {order['customer_name']}\n"
                f"وضعیت: {order['status']}\n"
                f"آخرین به‌روزرسانی: {order['last_update']}"
            )
            kb = [[InlineKeyboardButton("نیافتم — تماس با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")]]
            await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(kb))
        else:
            kb = [[InlineKeyboardButton("درخواست کمک از پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")]]
            await update.message.reply_text("سفارش پیدا نشد. لطفاً شناسه سفارش را بررسی کنید یا با پشتیبانی تماس بگیرید.", reply_markup=InlineKeyboardMarkup(kb))
        return

    # پردازش دستور AI با پیشوند !ai
    if text.startswith("!ai "):
        prompt = text[len("!ai "):].strip()
        await update.message.reply_text("در حال دریافت پاسخ از سرویس هوش‌مصنوعی...")
        # اجرای همگام با تابع sync generate_ai_answer (requests) را در executor اجرا می‌کنیم تا بلاک نشود
        loop = asyncio.get_event_loop()
        ai_resp = await loop.run_in_executor(None, generate_ai_answer, prompt)
        await update.message.reply_text(ai_resp)
        return

    # پیام پیش‌فرض
    await update.message.reply_text("برای شروع /start را ارسال کنید یا از دکمه‌ها استفاده کنید.")

# Admin-only command example
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("فقط ادمین مجاز است.")
        return
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("متن پخش را بنویسید: /broadcast متن پیام")
        return

    # در این نمونه، فهرستی از کاربران نداریم؛ اینجا یک مثال ساده است:
    await update.message.reply_text("شروع پخش (نمونه): " + text)
    # نکته: برای پخش واقعی باید table کاربران را داشته باشید و پیغام را برای هر کاربر ارسال کنید.

# Unknown command handler
async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("دستور نامشخص. برای شروع /start را بزنید.")

# ---------- Main ----------
async def main():
    init_db()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))  # usage: /broadcast text (admin only)

    # CallbackQuery handlers
    application.add_handler(CallbackQueryHandler(faq_main_cb, pattern="^faq_main$"))
    application.add_handler(CallbackQueryHandler(faq_cat_cb, pattern="^faq_cat::"))
    application.add_handler(CallbackQueryHandler(faq_q_cb, pattern="^faq_q::"))
    application.add_handler(CallbackQueryHandler(back_main_cb, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(track_order_cb, pattern="^track_order$"))
    application.add_handler(CallbackQueryHandler(ai_question_cb, pattern="^ai_question$"))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    # Fallback unknown command
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))

    logger.info("Bot starting (polling)...")
    # Run polling (blocking)
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
