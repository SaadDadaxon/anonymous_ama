import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from bot_bot.config import BOT_TOKEN, SUPERADMIN_ID
from bot_bot.database.models import Channel, User
from bot_bot.database.database import async_session
from bot_bot.handlers import user, admin
from bot_bot.database.database import create_tables
import sys
import os
import logging

# Logging sozlamalari
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

# Bot va Dispatcher obyektlarini yaratamiz
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# Handler'ni registratsiya qilamiz
dp.include_router(user.router)
dp.include_router(admin.router)


# Faoliyatni yoqish
dp.message.filter(F.chat.type == "private")
dp.chat_member.filter(F.chat.type == "channel")


@dp.my_chat_member()
async def handle_my_chat_member(event: ChatMemberUpdated):
    """Foydalanuvchi botni block qilsa — bazadan o‘chirish"""
    status = event.new_chat_member.status
    user_id = event.from_user.id

    # Agar foydalanuvchi botni block qilgan bo‘lsa
    if status == "kicked":
        async with async_session() as session:
            await session.execute(delete(User).where(User.telegram_id == user_id))
            await session.commit()
            print(f"❌ Foydalanuvchi {user_id} block qildi va o‘chirildi.")



async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await create_tables()
    await dp.start_polling(bot, allowed_updates=["message", "chat_member", "my_chat_member", "callback_query"], skip_update=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
