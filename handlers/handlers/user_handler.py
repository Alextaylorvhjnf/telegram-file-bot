import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database import Database
from config import FORCE_SUB_CHANNEL, BOT_USERNAME
from utils import get_join_channel_keyboard, get_main_keyboard

logger = logging.getLogger(__name__)
db = Database()

async def check_user_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest:
        return False
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت: {e}")
        return False

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # ذخیره کاربر
    db.add_user(user_id, user.username, user.first_name, user.last_name)
    
    # اگر پارامتر start داشت
    if context.args:
        film_code = context.args[0]
        return await send_film_to_user(update, context, film_code, user_id)
    
    # پیام خوشامدگویی
    welcome_text = f"""
🤖 به ربات دریافت فیلم خوش آمدید {user.first_name}!

🎬 برای دریافت فیلم روی لینک مخصوص آن کلیک کنید.

📢 حتما در کانال ما عضو شوید:
@{FORCE_SUB_CHANNEL[1:]}
    """
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def send_film_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, film_code: str, user_id: int):
    # بررسی عضویت
    is_member = await check_user_membership(user_id, context)
    
    if not is_member:
        join_text = f"""
⚠️ برای دریافت فیلم باید در کانال ما عضو شوید.

📢 @{FORCE_SUB_CHANNEL[1:]}

✅ پس از عضویت روی «عضو شدم» کلیک کنید.
        """
        
        if update.message:
            await update.message.reply_text(join_text, reply_markup=get_join_channel_keyboard())
        else:
            await update.callback_query.edit_message_text(join_text, reply_markup=get_join_channel_keyboard())
        return
    
    # پیدا کردن فیلم
    film = db.get_film(film_code)
    
    if not film:
        error_text = "❌ فیلم مورد نظر یافت نشد."
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        return
    
    # ارسال فیلم
    try:
        caption = film['caption'] or film['title'] or f"🎬 فیلم {film_code}"
        
        if film['file_id'].startswith('BA'):
            # ویدیو
            await context.bot.send_video(
                chat_id=user_id,
                video=film['file_id'],
                caption=caption,
                reply_markup=get_main_keyboard()
            )
        else:
            # سند
            await context.bot.send_document(
                chat_id=user_id,
                document=film['file_id'],
                caption=caption,
                reply_markup=get_main_keyboard()
            )
        
        success_text = f"✅ فیلم {film_code} ارسال شد"
        if update.callback_query:
            await update.callback_query.edit_message_text(success_text)
            
    except Exception as e:
        logger.error(f"خطا در ارسال فیلم: {e}")
        error_text = "❌ خطا در ارسال فیلم. لطفاً بعداً تلاش کنید."
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "check_join":
        is_member = await check_user_membership(user_id, context)
        
        if is_member:
            await query.edit_message_text(
                "✅ عالی! حالا می‌توانید از لینک فیلم استفاده کنید.",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ هنوز در کانال عضو نشده‌اید. لطفاً ابتدا عضو شوید.",
                reply_markup=get_join_channel_keyboard()
            )
    
    elif query.data == "list_films":
        films = db.get_all_films()
        
        if not films:
            await query.edit_message_text(
                "📭 در حال حاضر فیلمی موجود نیست.",
                reply_markup=get_main_keyboard()
            )
            return
        
        from utils import create_start_link
        
        films_text = "🎬 لیست فیلم‌های موجود:\n\n"
        keyboard = []
        
        for film in films[:10]:  # حداکثر 10 فیلم
            film_title = film['title']
            films_text += f"• {film_title}\n"
            
            keyboard.append([InlineKeyboardButton(
                film_title,
                url=create_start_link(film['film_code'])
            )])
        
        keyboard.append([InlineKeyboardButton("بازگشت ◀️", callback_data="back_to_main")])
        
        await query.edit_message_text(
            films_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "help":
        help_text = f"""
📖 راهنمای ربات:

1. برای دریافت فیلم روی لینک مربوطه کلیک کنید
2. اگر لینک کار نکرد، در کانال عضو شوید
3. پس از عضویت دکمه «عضو شدم» را بزنید
4. برای مشاهده لیست فیلم‌ها از دکمه پایین استفاده کنید

🎬 لینک نمونه:
https://t.me/{BOT_USERNAME}?start=film001

📢 کانال: @{FORCE_SUB_CHANNEL[1:]}
        """
        
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت ◀️", callback_data="back_to_main")]])
        )
    
    elif query.data == "back_to_main":
        welcome_text = """
🤖 به ربات دریافت فیلم خوش آمدید!

🎬 برای دریافت فیلم روی لینک مخصوص آن کلیک کنید.
        """
        
        await query.edit_message_text(welcome_text, reply_markup=get_main_keyboard())
