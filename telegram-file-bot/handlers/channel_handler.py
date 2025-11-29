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
        
        if message.chat.id != PRIVATE_CHANNEL_ID:
            return
        
        if not message.video and not message.document:
            return
        
        if message.video:
            file_id = message.video.file_id
        else:
            file_id = message.document.file_id
        
        caption = message.caption or ""
        film_code_match = re.search(r'film\d+', caption, re.IGNORECASE)
        
        if film_code_match:
            film_code = film_code_match.group().lower()
            title = caption.split('\n')[0] if '\n' in caption else caption
            
            success = db.add_film(
                film_code=film_code,
                file_id=file_id,
                title=title,
                caption=caption
            )
            
            if success:
                logger.info(f"Film {film_code} saved successfully")
            else:
                logger.error(f"Failed to save film {film_code}")
        else:
            logger.warning(f"No film code found in caption: {caption}")
            
    except Exception as e:
        logger.error(f"Error handling channel post: {e}")