import re
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from config import PRIVATE_CHANNEL_ID

logger = logging.getLogger(__name__)
db = Database()

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.channel_post
        
        # فقط پیام‌های کانال خصوصی
        if message.chat.id != PRIVATE_CHANNEL_ID:
            return
        
        # فقط ویدیو و فایل
        if not message.video and not message.document:
            return
        
        # دریافت file_id
        if message.video:
            file_id = message.video.file_id
            file_type = "video"
        else:
            file_id = message.document.file_id
            file_type = "document"
        
        caption = message.caption or ""
        
        # پیدا کردن کد فیلم
        film_code_match = re.search(r'film\d+', caption, re.IGNORECASE)
        if film_code_match:
            film_code = film_code_match.group().lower()
            title = caption.split('\n')[0] if '\n' in caption else caption[:100]
            
            # ذخیره در دیتابیس
            success = db.add_film(
                film_code=film_code,
                file_id=file_id,
                title=title,
                caption=caption
            )
            
            if success:
                logger.info(f"✅ فیلم {film_code} ذخیره شد (نوع: {file_type})")
            else:
                logger.error(f"❌ خطا در ذخیره فیلم {film_code}")
        else:
            logger.warning(f"⚠️ کد فیلم در caption پیدا نشد: {caption}")
            
    except Exception as e:
        logger.error(f"❌ خطا در پردازش پست کانال: {e}")
