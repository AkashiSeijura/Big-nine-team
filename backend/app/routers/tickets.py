from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSessionLocal
from app.models.ticket import Ticket
from app.models.chat_message import ChatMessage
from app.schemas.ticket import TicketOut, TicketUpdate, TicketCreate
from app.schemas.chat import ChatMessageOut, ChatMessageCreate
from app.routers.auth import get_current_user
from app.models.user import User
from app.services.ai_service import analyze_ticket_with_ai, generate_chat_reply
from app.services.email_service import send_email_response

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

async def process_ticket_ai(ticket_id: int, ticket_text: str):
    """Background task to analyze ticket with AI and update DB."""
    ai_result = await analyze_ticket_with_ai(ticket_text)
    
    async with AsyncSessionLocal() as session:
        ticket = await session.get(Ticket, ticket_id)
        if ticket:
            ticket.sentiment = ai_result.get("sentiment")
            ticket.category = ai_result.get("category")
            ticket.ai_response = ai_result.get("draft_response")
            ticket.full_name = ticket.full_name or ai_result.get("full_name")
            ticket.company = ticket.company or ai_result.get("company")
            ticket.phone = ticket.phone or ai_result.get("phone")
            ticket.device_serials = ticket.device_serials or ai_result.get("device_serials") or []
            ticket.device_type = ticket.device_type or ai_result.get("device_type")
            ticket.summary = ticket.summary or ai_result.get("summary")
            await session.commit()


# ── Список заявок ─────────────────────────────────────
@router.get("", response_model=list[TicketOut])
async def list_tickets(
    status: str | None = None,
    sentiment: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Ticket).order_by(desc(Ticket.date_received))
    if status:
        q = q.where(Ticket.status == status)
    if sentiment:
        q = q.where(Ticket.sentiment == sentiment)
    if category:
        q = q.where(Ticket.category == category)
    result = await db.execute(q)
    return result.scalars().all()


# ── Создать заявку (вручную / AI-агент) ───────────────
@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = Ticket(**payload.model_dump())
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    ticket_text = ticket.original_email or ticket.summary or ""
    if ticket_text:
        background_tasks.add_task(process_ticket_ai, ticket.id, ticket_text)
        
    return ticket


# ── Получить заявку ────────────────────────────────────
@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return ticket


# ── Обновить заявку ────────────────────────────────────
@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    await db.commit()
    await db.refresh(ticket)
    return ticket


# ── Отправить ответ ────────────────────────────────────
@router.post("/{ticket_id}/send")
async def send_response(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if not ticket.ai_response:
        raise HTTPException(status_code=400, detail="Нет текста ответа")

    if not ticket.email:
        raise HTTPException(status_code=400, detail="У заявки нет email адреса отправителя")

    try:
        subject = "Ответ на ваше обращение"
        await send_email_response(ticket.email, subject, ticket.ai_response)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки письма: {exc}")

    ticket.status = "closed"
    await db.commit()
    return {"success": True, "message": "Ответ отправлен"}


# ── Чат заявки ────────────────────────────────────────
@router.get("/{ticket_id}/chat", response_model=list[ChatMessageOut])
async def get_chat(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.ticket_id == ticket_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()


@router.post("/{ticket_id}/chat", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def add_chat_message(
    ticket_id: int,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    msg = ChatMessage(ticket_id=ticket_id, role=payload.role, text=payload.text)
    db.add(msg)

    # Если оператор запрашивает человека — обновляем статус
    if "вызвать оператора" in payload.text.lower():
        ticket.status = "needs_operator"

    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/{ticket_id}/chat/reply", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def ai_chat_reply(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Generate and save an AI bot reply based on the full chat history."""
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.ticket_id == ticket_id)
        .order_by(ChatMessage.created_at)
    )
    history = [{"role": m.role, "text": m.text} for m in result.scalars().all()]

    ticket_context = ticket.original_email or ticket.summary or ""
    reply_text = await generate_chat_reply(ticket_context, history)

    bot_msg = ChatMessage(ticket_id=ticket_id, role="bot", text=reply_text)
    db.add(bot_msg)
    await db.commit()
    await db.refresh(bot_msg)
    return bot_msg
