from aiogram import Router, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, WebAppInfo
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot_bot.config import SUPERADMIN_ID

router = Router()  # Router yaratamiz


@router.message(Command("admin_saad"))
async def admin_panel(message: Message):
    """Superadmin uchun admin panel WebApp havolasini yuborish"""
    if str(message.from_user.id) == SUPERADMIN_ID:
        web_app_url = "https://your-admin-panel.com"  # Admin panel URL
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔹 Admin Panelga kirish", web_app=WebAppInfo(url=web_app_url))
        await message.answer("🔹 **Admin panelga kirish uchun tugmani bosing:**", reply_markup=keyboard.as_markup())
    else:
        await message.answer("⛔ Sizda admin panelga kirish huquqi yo‘q!")


