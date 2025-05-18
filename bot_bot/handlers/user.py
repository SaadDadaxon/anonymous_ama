from aiogram import Router, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from sqlalchemy import delete
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from bot_bot.config import SUPERADMIN_ID, DATABASE_URL, URL
from sqlalchemy.exc import IntegrityError
from bot_bot.database.database import async_session
from bot_bot.database.models import User, Channel
from sqlalchemy.future import select
print(URL)

router = Router()


def get_main_keyboard(bot_username):
    """Asosiy menyu uchun inline keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Botni kanalga qo‘shish", url=f"https://t.me/{bot_username}?startchannel=true")],
            [InlineKeyboardButton(text="❓ Savol yuborish", callback_data="question")]
    ])
    return keyboard

@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, bot: Bot):
    """Asosiy menyuni ko‘rsatish"""
    bot_username = (await bot.get_me()).username.lstrip("@")  # Bot usernamesini olish
    keyboard = get_main_keyboard(bot_username)
    await callback.message.edit_text(
        "📋 Asosiy menyuga qaytdingiz! Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(Command("start"))
async def start_handler(message: types.Message, bot: Bot):
    """Foydalanuvchini bazaga qo‘shish yoki mavjudligini tekshirish"""
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    bot_username = (await bot.me()).username  # Bot username olamiz

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            # Foydalanuvchini bazaga qo‘shish
            new_user = User(telegram_id=user_id, full_name=full_name, username=username)
            session.add(new_user)
            await session.commit()
            welcome_text =  (
    "🎉 Siz ro‘yxatdan o‘tdingiz! ✅\n"
    "             Diqqat               \n"
    "Bot faqat ommaviy kanallarda ishlaydi.\n"
    "Siz botni shaxsiy kanalingizda ishlatsangiz bo‘ladi.\n"
    "Yoki siz qaysidir kanal adminiga savol yuborganingizda "
    "sizning kimligingiz sir saqlanadi.\n"
    "Ma'lumotlaringiz oshkor qilinmaydi."
)
        else:
            welcome_text = "Siz allaqachon ro‘yxatdan o‘tigansiz! ✅"

    await message.answer(welcome_text, reply_markup=get_main_keyboard(bot_username))



async def get_user_subscribed_channels():
    """Bot bazasida ro‘yxatdan o‘tgan barcha kanallarni olish"""
    async with async_session() as session:
        result = await session.execute(select(Channel))  # Barcha kanallarni olish
        channels = result.scalars().all()
    return channels


async def get_user_subscribed_channels_1(user_id: int, bot: Bot):
    """Foydalanuvchining obuna bo‘lgan kanallarini qaytaradi"""
    async with async_session() as session:
        result = await session.execute(select(Channel))
        channels = result.scalars().all()  # Barcha kanallarni olish

    user_channels = []

    for channel in channels:
        try:
            chat_member = await bot.get_chat_member(channel.id, user_id)
            if chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                user_channels.append(channel)  # Faqat a’zo bo‘lgan kanallarni saqlash
        except TelegramBadRequest:
            continue  # Agar kanal mavjud bo‘lmasa yoki xato bo‘lsa, uni o'tkazib yuboramiz

    return user_channels


@router.callback_query(lambda c: c.data == "question" or c.data.startswith("next_page_") or c.data.startswith("prev_page_"))
async def ask_question_callback(callback: CallbackQuery, bot: Bot):
    """Foydalanuvchiga obuna bo‘lgan kanallarni inline tugma sifatida chiqarish (sahifalash bilan)"""
    user_id = callback.from_user.id
    channels = await get_user_subscribed_channels_1(user_id, bot)  # Foydalanuvchining obuna bo‘lgan kanallarini olish

    if not channels:
        await callback.answer("📭 Siz hech qaysi kanalga a'zo emassiz yoki botda kanal yo'q.", show_alert=True)
        return

    # Joriy sahifa raqamini aniqlash
    if callback.data == "question":
        current_page = 1
    elif callback.data.startswith("next_page_"):
        current_page = int(callback.data.split("_")[2]) + 1
    elif callback.data.startswith("prev_page_"):
        current_page = int(callback.data.split("_")[2]) - 1
    else:
        current_page = 1

    # Sahifalash parametrlari
    channels_per_page = 10  # Har sahifada 10 ta kanal
    total_channels = len(channels)
    total_pages = (total_channels + channels_per_page - 1) // channels_per_page  # Umumiy sahifalar soni

    # Joriy sahifadagi kanallarni olish
    start_idx = (current_page - 1) * channels_per_page
    end_idx = min(start_idx + channels_per_page, total_channels)
    page_channels = channels[start_idx:end_idx]

    # InlineKeyboardBuilder yaratish
    keyboard = InlineKeyboardBuilder()

    # Kanallarni ikkitadan qatorlarga bo‘lib tugmalar yaratish
    buttons = [
        InlineKeyboardButton(text=channel.name, callback_data=f"ask_channel_{channel.id}")
        for channel in page_channels
    ]

    # Tugmalarni ikkitadan qatorlarga joylashtirish
    for i in range(0, len(buttons), 2):
        row_buttons = buttons[i:i+2]  # Har bir qatorga 2 ta tugma
        keyboard.row(*row_buttons)

    # Navigatsiya tugmalari (Keyingi va Oldingi)
    nav_buttons = []
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"next_page_{current_page}")
        )
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"prev_page_{current_page}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text="🔙 Bosh Sahifa", callback_data="main_menu")
    )

    if nav_buttons:
        keyboard.row(*nav_buttons)


    # Savol yuborish uchun kanal ro'yxatini yuborish
    await callback.message.edit_text(
        f"📢 Qaysi kanal adminiga savol yubormoqchisiz? (Sahifa {current_page}/{total_pages})",
        reply_markup=keyboard.as_markup()
    )

    await callback.answer()  # Callback queryni tasdiqlash


# async def get_channel_by_id(channel_id: str):
#     # Kanalni ma'lumotlar bazasidan olish
#     async with async_session() as session:
#         result = await session.execute(select(Channel))
#         channels = result.scalars().all()
#     for c in channels:
#         if int(channel_id) == c.id:
#             return c


async def get_channel_admins(channel_id: str, bot: Bot):
    try:
        chat_admins = await bot.get_chat_administrators(channel_id)
        admin_ids = [admin.user.id for admin in chat_admins]
        return admin_ids
    except Exception as e:
        return None


@router.chat_member()
@router.my_chat_member()
async def process_channel(event: ChatMemberUpdated, bot: Bot):
    """Bot kanalga qo‘shilganda yoki olib tashlanganda hodisani qayta ishlash"""

    if event.new_chat_member.user.id == event.bot.id:  # Agar hodisa bot bilan bo‘lsa
        if event.new_chat_member.status in ["administrator", "creator"]:  # Agar bot admin yoki yaratuvchi bo‘lsa
            channel_id = event.chat.id
            channel_name = event.chat.title
            channel_username = event.chat.username

            # Admin ID ni olish
            chat_admins = await bot.get_chat_administrators(channel_id)
            admin_id = None

            for admin in chat_admins:
                if not admin.user.is_bot:  # Bot bo'lmagan adminni olish
                    admin_id = admin.user.id
                    break

            if not admin_id:
                print("❌ Adminni aniqlab bo‘lmadi!")
                return

            # Kanalni bazaga saqlash
            async with async_session() as session:
                result = await session.execute(select(Channel).where(Channel.id == channel_id))
                existing_channel = result.scalar_one_or_none()

                if not existing_channel:
                    new_channel = Channel(
                        id=channel_id,
                        name=channel_name,
                        admin_id=admin_id,
                        channel_username=channel_username
                    )
                    session.add(new_channel)
                    try:
                        await session.commit()
                        await bot.send_message(
                            SUPERADMIN_ID,
                            f"📢 *{channel_name} @{channel_username}* bazaga qo‘shildi! ✅"
                        )
                    except IntegrityError:
                        await session.rollback()
                        await bot.send_message(
                            admin_id,
                            "❌ Bu kanal allaqachon ro‘yxatdan o‘tgan!"
                        )

        elif event.new_chat_member.status == ChatMemberStatus.LEFT:  # Agar bot kanalni tark etsa
            # Agar bot kanalni tark etsa, bazadan o‘chirish
            async with async_session() as session:
                await session.execute(delete(Channel).where(Channel.id == event.chat.id))
                await session.commit()
                await bot.send_message(SUPERADMIN_ID, f"📢 @{event.chat.username} bazadan o‘chirildi! ❌")


async def get_channel_by_id(channel_id):
    """Kanalni ID bo‘yicha olish"""
    async with async_session() as session:
        result = await session.execute(select(Channel).where(Channel.id == int(channel_id)))
        return result.scalar_one_or_none()

@router.callback_query(lambda c: c.data.startswith(("ask_channel_", "next_admin_page_", "prev_admin_page_")))
async def ask_channel_callback(callback: CallbackQuery, bot: Bot):
    """Foydalanuvchi kanalni tanlasa, adminlar ro‘yxatini chiqaradi"""
    # callback.data dan channel_id va sahifa raqamini olish
    if callback.data.startswith("ask_channel_"):
        channel_id = callback.data.split("_")[-1]
        current_page = 1
    elif callback.data.startswith("next_admin_page_") or callback.data.startswith("prev_admin_page_"):
        parts = callback.data.split("_")
        current_page = int(parts[-2])
        channel_id = parts[-1]
        if callback.data.startswith("next_admin_page_"):
            current_page += 1
        elif callback.data.startswith("prev_admin_page_"):
            current_page -= 1

    # Kanalni olish
    channel = await get_channel_by_id(channel_id)
    if not channel:
        await callback.answer("⛔ Kanal topilmadi.")
        return

    # Telegramdan kanal adminlarini olish
    try:
        chat_admins = await bot.get_chat_administrators(channel_id)
    except Exception as e:
        await callback.answer(f"⛔ Kanal adminlarini olishda xato: {str(e)}")
        return

    # BOT bo‘lmagan real adminlarni olish
    real_admins = [admin for admin in chat_admins if not admin.user.is_bot]
    if not real_admins:
        await callback.answer("⛔ Kanalda real adminlar mavjud emas.")
        return

    # Botda ro‘yxatdan o‘tgan adminlar ro‘yxatini olish
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        registered_admin_ids = [row[0] for row in result.fetchall()]

    # Real + ro‘yxatdan o‘tgan adminlarni olish
    filtered_admins = [admin for admin in real_admins if admin.user.id in registered_admin_ids]
    if not filtered_admins:
        await callback.answer("⛔ Botda ro‘yxatdan o‘tgan adminlar topilmadi.")
        return

    # Sahifalash parametrlari
    admins_per_page = 10  # Har sahifada 10 ta admin
    total_admins = len(filtered_admins)
    total_pages = (total_admins + admins_per_page - 1) // admins_per_page  # Umumiy sahifalar soni

    # Joriy sahifadagi adminlarni olish
    start_idx = (current_page - 1) * admins_per_page
    end_idx = min(start_idx + admins_per_page, total_admins)
    page_admins = filtered_admins[start_idx:end_idx]

    # InlineKeyboardBuilder yaratish
    keyboard = InlineKeyboardBuilder()
    print(URL)
    # Adminlarni ikkitadan qatorlarga bo‘lib tugmalar yaratish
    user_id = callback.from_user.id  # Foydalanuvchi Telegram ID’sini olish
    buttons = [
        InlineKeyboardButton(
            text=admin.user.full_name,
            web_app=WebAppInfo(url=f"{URL}/ask_question?admin_id={admin.user.id}&channel_id={channel_id}&user_id={user_id}")
        )
        for admin in page_admins
    ]

    # Tugmalarni ikkitadan qatorlarga joylashtirish
    for i in range(0, len(buttons), 2):
        row_buttons = buttons[i:i+2]  # Har bir qatorga 2 ta tugma
        keyboard.row(*row_buttons)

    # Navigatsiya tugmalari (Keyingi, Oldingi va Orqaga)
    nav_buttons = []
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"next_admin_page_{current_page}_{channel_id}")
        )
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"prev_admin_page_{current_page}_{channel_id}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="question")
    )
    if nav_buttons:
        keyboard.row(*nav_buttons)

    # Xabar matni
    new_text = f"📢 Siz {channel.name} kanalini tanladingiz. Quyidagi adminlardan biriga savol yuborishingiz mumkin (Sahifa {current_page}/{total_pages}):"

    # Joriy xabar matni va tugmalar bilan solishtirish
    current_message = callback.message.text
    current_reply_markup = callback.message.reply_markup

    # Agar xabar va tugmalar o‘zgarmagan bo‘lsa, yangilashni o‘tkazib yuboramiz
    if current_message == new_text and current_reply_markup == keyboard.as_markup():
        print(f"Skipping edit: Message and markup unchanged for channel_id={channel_id}, page={current_page}")  # Debug
        await callback.answer()
        return

    # Xabarni yangilash
    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=keyboard.as_markup()
        )
        print(f"Message updated: channel_id={channel_id}, page={current_page}")  # Debug
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            print(f"Ignored: Message not modified for channel_id={channel_id}, page={current_page}")  # Debug
        else:
            print(f"Error editing message: {str(e)}")  # Debug
            await callback.answer(f"Xato yuz berdi: {str(e)}")

    # URL’ni konsolga chop etish (debug uchun)
    for admin in page_admins:
        print(f"WebApp URL: {URL}/ask_question?admin_id={admin.user.id}&channel_id={channel_id}&user_id={user_id}")

    await callback.answer()

@router.callback_query(lambda c: c.data == "post")
async def ask_question_callback(callback: CallbackQuery):
    print('salom')

