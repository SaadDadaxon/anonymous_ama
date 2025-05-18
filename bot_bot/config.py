from dotenv import load_dotenv
import os

load_dotenv()  # .env faylini yuklaymiz

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPERADMIN_ID = os.getenv("SUPERADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
URL = os.getenv("URL")
