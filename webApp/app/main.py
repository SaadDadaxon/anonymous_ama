from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy.future import select
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from bot_bot.config import BOT_TOKEN, URL
from pathlib import Path
from fastapi.responses import FileResponse
from bot_bot.database.database import async_session
from bot_bot.database.models import Channel, User
from aiogram import Bot
from urllib.parse import quote

# FastAPI ilovasini yaratish
app = FastAPI()

app.mount("/static", StaticFiles(directory="webApp/static"), name="static")
bot = Bot(token=BOT_TOKEN)


@app.get("/ask_question", response_class=HTMLResponse)
async def ask_question(request: Request, admin_id: int, channel_id: int):
    """Savolni kiritish uchun sahifaga yo'naltirish"""
    async with async_session() as session:
        # Barcha kanallarni olish
        channel_result = await session.execute(select(Channel))
        channels = channel_result.scalars().all()

        # Adminni olish
        admin_result = await session.execute(select(User).where(User.telegram_id == admin_id))
        admin = admin_result.scalar_one_or_none()

    if not admin:
        return HTMLResponse(content="Admin topilmadi", status_code=404)

    user_channels = []

    for channel in channels:
        try:
            chat_member = await bot.get_chat_member(channel.id, admin_id)
            if chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                user_channels.append(channel)
        except TelegramBadRequest:
            continue

    # Foydalanuvchi yubormoqchi bo‘lgan kanalni aniqlaymiz
    selected_channel = next((ch for ch in user_channels if ch.id == channel_id), None)

    if not selected_channel:
        return HTMLResponse(content="Bu admin kanalga a'zo emas!", status_code=403)

    # HTML faylni o‘qish va dynamic joylarni to‘ldirish
    html_path = Path("webApp/static/send_question.html")
    html_content = html_path.read_text(encoding="utf-8")

    html_content = html_content.replace("{{admin_id}}", str(admin_id))
    html_content = html_content.replace("{{channel_id}}", str(channel_id))
    html_content = html_content.replace("{{channel_name}}", selected_channel.name)
    html_content = html_content.replace("{{admin_name}}", admin.full_name)  # yoki admin.username
    html_content = html_content.replace("{{base_url}}", URL)

    return HTMLResponse(content=html_content)

@app.get("/api/send_question")
async def send_question(admin_id: int, channel_id: int, question: str, user_id: int):
    print(f"Request received: admin_id={admin_id}, channel_id={channel_id}, user_id={user_id}, question={question}")  # Debug
    if not question:
        print("Error: Question is empty")  # Debug
        raise HTTPException(status_code=400, detail="Savol kiritilmagan")

    # Inline keyboardni yaratish
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    answer_url = f"{URL}/view_question?admin_id={admin_id}&channel_id={channel_id}&user_id={user_id}&question={quote(question)}"
    button = InlineKeyboardButton(text='Javob Berish', web_app=WebAppInfo(url=answer_url))
    keyboard.inline_keyboard.append([button])
    print(f"Answer URL: {answer_url}")  # Debug

    # Telegramga yuborish
    try:
        # Admin’ga xabar
        text = f"📩 Yangi savol:\n\n{question}\n\nJavob berish uchun tugmani bosing:"
        await bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
        print(f"Message sent to admin: {admin_id}")  # Debug

        # Foydalanuvchiga tasdiqlash xabari
        await bot.send_message(chat_id=user_id, text="✅ Savolingiz muvaffaqiyatli yuborildi!")
        print(f"Message sent to user: {user_id}")  # Debug

        return {"message": "Savol muvaffaqiyatli yuborildi"}
    except Exception as e:
        print(f"Error sending message: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=f"Telegramga yuborishda xatolik: {str(e)}")

@app.get("/ask_question")
async def ask_question():
    html_path = Path("webApp/static/ask_question.html")
    print(f"Serving HTML: {html_path.absolute()}")  # Debug
    if not html_path.exists():
        print("Error: HTML file not found")  # Debug
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")
    return FileResponse(html_path)

@app.get("/thankyou")
async def thankyou():
    html_path = Path("webApp/static/thanks.html")
    print(f"Serving HTML: {html_path.absolute()}")  # Debug
    if not html_path.exists():
        print("Error: HTML file not found")  # Debug
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")
    return FileResponse(html_path)

@app.get("/api/send_answer")
async def send_answer(admin_id: int, channel_id: int, user_id: int, question: str, answer: str):
    print(f"Request received: admin_id={admin_id}, channel_id={channel_id}, user_id={user_id}, question={question}, answer={answer}")  # Debug
    if not answer:
        print("Error: Answer is empty")  # Debug
        raise HTTPException(status_code=400, detail="Javob kiritilmagan")

    # Telegramga yuborish
    try:
        # Foydalanuvchiga javob
        text = f"📬 Sizning savolingizga javob:\n\n**Savol**: {question}\n**Javob**: {answer}"
        await bot.send_message(chat_id=user_id, text=text)
        print(f"Answer sent to user: {user_id}")  # Debug

        # Admin’ga tasdiqlash
        await bot.send_message(chat_id=admin_id, text=f"✅ Javob muvaffaqiyatli yuborildi:\n\n**Savol**: {question}\n**Javob**: {answer}")
        print(f"Confirmation sent to admin: {admin_id}")  # Debug

        return {"message": "Javob muvaffaqiyatli yuborildi"}
    except Exception as e:
        print(f"Error sending message: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=f"Telegramga yuborishda xatolik: {str(e)}")

@app.get("/api/reject_question")
async def reject_question(admin_id: int, channel_id: int, user_id: int, question: str):
    print(f"Request received: admin_id={admin_id}, channel_id={channel_id}, user_id={user_id}, question={question}")  # Debug

    # Telegramga yuborish
    try:
        # Foydalanuvchiga rad etish xabari
        text = f"❌ Sizning savolingiz rad etildi:\n\n**Savol**: {question}"
        await bot.send_message(chat_id=user_id, text=text)
        print(f"Rejection sent to user: {user_id}")  # Debug

        # Admin’ga tasdiqlash
        await bot.send_message(chat_id=admin_id, text=f"✅ Savol rad etildi:\n\n**Savol**: {question}")
        print(f"Confirmation sent to admin: {admin_id}")  # Debug

        return {"message": "Savol muvaffaqiyatli rad etildi"}
    except Exception as e:
        print(f"Error sending message: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=f"Telegramga yuborishda xatolik: {str(e)}")

@app.get("/view_question")
async def view_question():
    html_path = Path("webApp/static/view_question.html")
    print(f"Serving HTML: {html_path.absolute()}")  # Debug
    if not html_path.exists():
        print("Error: HTML file not found")  # Debug
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")
    return FileResponse(html_path)


@app.get("/answer_success")
async def answer_success():
    html_path = Path("webApp/static/answer_success.html")
    print(f"Serving HTML: {html_path.absolute()}")  # Debug
    if not html_path.exists():
        print("Error: HTML file not found")  # Debug
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")
    return FileResponse(html_path)

@app.get("/reject_success")
async def reject_success():
    html_path = Path("webApp/static/reject_success.html")
    print(f"Serving HTML: {html_path.absolute()}")  # Debug
    if not html_path.exists():
        print("Error: HTML file not found")  # Debug
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")
    return FileResponse(html_path)
