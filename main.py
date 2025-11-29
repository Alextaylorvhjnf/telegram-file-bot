import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, PRIVATE_CHANNEL_ID
from handlers.channel_handler import handle_channel_post
from handlers.user_handler import start_handler, button_handler

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 در حال راه‌اندازی ربات...")
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # هندلرهای کاربر
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # هندلر پست کانال
    application.add_handler(MessageHandler(
        filters.Chat(PRIVATE_CHANNEL_ID) & (filters.VIDEO | filters.Document.ALL),
        handle_channel_post
    ))
    
    # شروع ربات
    logger.info("✅ ربات شروع به کار کرد")
    application.run_polling()

if __name__ == "__main__":
    main()
