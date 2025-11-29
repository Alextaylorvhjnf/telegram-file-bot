import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8519774430:AAFLAY9E7zyFht8bs5wD4rSJ6p8WgCP-bgs")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Senderpfilesbot")
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "@betdesignernet")
PRIVATE_CHANNEL_ID = int(os.environ.get("PRIVATE_CHANNEL_ID", "-1002920455639"))
ADMIN_IDS = [int(id) for id in os.environ.get("ADMIN_IDS", "7321524568").split(",")]
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///films_bot.db")