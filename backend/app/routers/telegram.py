from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, UserTelegramId
from app.models.ticket import Ticket
from app.config import settings

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


def verify_bot_secret(x_bot_secret: str | None = Header(default=None)):
    if x_bot_secret != settings.bot_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/allowed-users", dependencies=[Depends(verify_bot_secret)])
async def allowed_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.telegram_ids))
    )
    users = result.scalars().all()
    all_tg_ids = [t.telegram_id for u in users for t in u.telegram_ids]
    admin_tg_ids = [t.telegram_id for u in users if u.role == "admin" for t in u.telegram_ids]
    return {
        "users": all_tg_ids,
        "admins": admin_tg_ids,
    }


@router.get("/tickets/{ticket_id}/contacts", dependencies=[Depends(verify_bot_secret)])
async def ticket_contacts(ticket_id: int, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    return {
        "full_name": ticket.full_name,
        "email": ticket.email,
        "phone": ticket.phone,
        "company": ticket.company,
        "device_serials": ticket.device_serials or [],
        "device_type": ticket.device_type,
    }


@router.get("/tickets/{ticket_id}/generated-answer", dependencies=[Depends(verify_bot_secret)])
async def ticket_generated_answer(ticket_id: int, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    return {"ai_response": ticket.ai_response or "Ответ AI ещё не сгенерирован"}
