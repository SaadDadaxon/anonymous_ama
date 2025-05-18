from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/view_question", response_class=HTMLResponse)
async def view_question(admin_id: int, channel_id: int, user_id: int, question: str):
    # HTML faylni o‘qish
    html_path = Path("view_question.html")  # HTML fayl joylashgan manzil
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="HTML fayl topilmadi")

    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    return HTMLResponse(content=html_content)