import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import FORCE_SUB_CHANNEL, BOT_USERNAME

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_start_link(film_code):
    return f"https://t.me/{BOT_USERNAME}?start={film_code}"

def get_join_channel_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("🎬 لیست فیلم‌ها", callback_data="list_films")]
    ]
    return InlineKeyboardMarkup(keyboard)
