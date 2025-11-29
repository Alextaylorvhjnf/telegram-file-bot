import os
import logging
import sqlite3
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# تنظیمات
BOT_TOKEN = os.getenv("BOT_TOKEN", "8519774430:AAFLAY9E7zyFht8bs5wD4rSJ6p8WgCP-bgs")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Senderpfilesbot")
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "@betdesignernet")
PRIVATE_CHANNEL_ID = int(os.getenv("PRIVATE_CHANNEL_ID", "-1002920455639"))

# دیتابیس
class Database:
    def __init__(self, db_path="films_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS films (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                film_code TEXT UNIQUE NOT NULL,
                file_id TEXT NOT NULL,
                title TEXT,
                caption TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("✅ دیتابیس آماده است")
    
    def add_film(self, film_code, file_id, title=None, caption=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO films (film_code, file_id, title, caption) VALUES (?, ?, ?, ?)', 
                         (film_code, file_id, title, caption))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"خطا در ذخیره فیلم: {e}")
            return False
        finally:
            conn.close()
    
    def get_film(self, film_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT film_code, file_id, title, caption FROM films WHERE film_code = ?', (film_code,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'film_code': result[0], 'file_id': result[1], 'title': result[2], 'caption': result[3]}
        return None
    
    def get_all_films(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT film_code, title FROM films ORDER BY added_at DESC')
        results = cursor.fetchall()
        conn.close()
        return [{'film_code': row[0], 'title': row[1] or row[0]} for row in results]
    
    def add_user(self, user_id, username, first_name, last_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)', 
                         (user_id, username, first_name, last_name))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"خطا در ذخیره کاربر: {e}")
            return False
        finally:
            conn.close()

# توابع کمکی
def create_start_link(film_code):
    return f"https://t.me/{BOT_USERNAME}?start={film_code}"

def get_join_channel_keyboard():
    channel_username = FORCE_SUB_CHANNEL.replace('@', '')
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{channel_username}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("🎬 لیست فیلم‌ها", callback_data="list_films")]
    ]
    return InlineKeyboardMarkup(keyboard)

# هندلرها
db = Database()

async def check_user_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest:
        return False
    except Exception as e:
        logging.error(f"خطا در بررسی عضویت: {e}")
        return False

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.channel_post
        if message.chat.id != PRIVATE_CHANNEL_ID:
            return
        if not message.video and not message.document:
            return
        
        file_id = message.video.file_id if message.video else message.document.file_id
        caption = message.caption or ""
        
        film_code_match = re.search(r'film\d+', caption, re.IGNORECASE)
        if film_code_match:
            film_code = film_code_match.group().lower()
            title = caption.split('\n')[0] if '\n' in caption else caption[:100]
            
            success = db.add_film(film_code=film_code, file_id=file_id, title=title, caption=caption)
            if success:
                logging.info(f"✅ فیلم {film_code} ذخیره شد")
            else:
                logging.error(f"❌ خطا در ذخیره فیلم {film_code}")
    except Exception as e:
        logging.error(f"❌ خطا در پردازش پست کانال: {e}")

async def send_film_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, film_code: str, user_id: int):
    is_member = await check_user_membership(user_id, context)
    
    if not is_member:
        join_text = f"⚠️ برای دریافت فیلم باید در کانال ما عضو شوید.\n\n📢 {FORCE_SUB_CHANNEL}\n\n✅ پس از عضویت روی «عضو شدم» کلیک کنید."
        if update.message:
            await update.message.reply_text(join_text, reply_markup=get_join_channel_keyboard())
        else:
            await update.callback_query.edit_message_text(join_text, reply_markup=get_join_channel_keyboard())
        return
    
    film = db.get_film(film_code)
    if not film:
        error_text = "❌ فیلم مورد نظر یافت نشد."
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        return
    
    try:
        caption = film['caption'] or film['title'] or f"🎬 فیلم {film_code}"
        if film['file_id'].startswith('BA') or film['file_id'].startswith('Ag'):
            await context.bot.send_video(chat_id=user_id, video=film['file_id'], caption=caption, reply_markup=get_main_keyboard())
        else:
            await context.bot.send_document(chat_id=user_id, document=film['file_id'], caption=caption, reply_markup=get_main_keyboard())
        
        success_text = f"✅ فیلم {film_code} ارسال شد"
        if update.callback_query:
            await update.callback_query.edit_message_text(success_text)
    except Exception as e:
        logging.error(f"خطا در ارسال فیلم: {e}")
        error_text = "❌ خطا در ارسال فیلم. لطفاً بعداً تلاش کنید."
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    if context.args:
        film_code = context.args[0]
        return await send_film_to_user(update, context, film_code, user.id)
    
    welcome_text = f"🤖 به ربات دریافت فیلم خوش آمدید {user.first_name}!\n\n🎬 برای دریافت فیلم روی لینک مخصوص آن کلیک کنید.\n\n📢 حتما در کانال ما عضو شوید:\n{FORCE_SUB_CHANNEL}"
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"📖 راهنمای ربات:\n\n1. برای دریافت فیلم روی لینک مربوطه کلیک کنید\n2. اگر لینک کار نکرد، در کانال عضو شوید\n3. پس از عضویت دکمه «عضو شدم» را بزنید\n\n🎬 لینک نمونه:\nhttps://t.me/{BOT_USERNAME}?start=film001\n\n📢 کانال: {FORCE_SUB_CHANNEL}"
    await update.message.reply_text(help_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "check_join":
        is_member = await check_user_membership(user_id, context)
        if is_member:
            await query.edit_message_text("✅ عالی! حالا می‌توانید از لینک فیلم استفاده کنید.", reply_markup=get_main_keyboard())
        else:
            await query.edit_message_text("❌ هنوز در کانال عضو نشده‌اید. لطفاً ابتدا عضو شوید.", reply_markup=get_join_channel_keyboard())
    
    elif query.data == "list_films":
        films = db.get_all_films()
        if not films:
            await query.edit_message_text("📭 در حال حاضر فیلمی موجود نیست.", reply_markup=get_main_keyboard())
            return
        
        films_text = "🎬 لیست فیلم‌های موجود:\n\n"
        keyboard = []
        for film in films[:10]:
            films_text += f"• {film['title']}\n"
            keyboard.append([InlineKeyboardButton(film['title'], url=create_start_link(film['film_code']))])
        keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="back_to_main")])
        await query.edit_message_text(films_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "help":
        help_text = f"📖 راهنمای ربات:\n\n1. برای دریافت فیلم روی لینک مربوطه کلیک کنید\n2. اگر لینک کار نکرد، در کانال عضو شوید\n3. پس از عضویت دکمه «عضو شدم» را بزنید\n\n🎬 لینک نمونه:\nhttps://t.me/{BOT_USERNAME}?start=film001\n\n📢 کانال: {FORCE_SUB_CHANNEL}"
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت ◀️", callback_data="back_to_main")]]))
    
    elif query.data == "back_to_main":
        await query.edit_message_text("🤖 به ربات دریافت فیلم خوش آمدید!\n\n🎬 برای دریافت فیلم روی لینک مخصوص آن کلیک کنید.", reply_markup=get_main_keyboard())

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 در حال راه‌اندازی ربات...")
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start_handler))
        application.add_handler(CommandHandler("help", help_handler))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.Chat(PRIVATE_CHANNEL_ID) & (filters.VIDEO | filters.Document.ALL), handle_channel_post))
        
        logger.info("✅ ربات شروع به کار کرد")
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ خطا در راه‌اندازی ربات: {e}")
        raise

if __name__ == "__main__":
    main()
