import asyncio
import email
import imaplib
import logging
from datetime import datetime, timezone
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.chat_message import ChatMessage
from app.models.ticket import Ticket
from sqlalchemy import select, desc
from app.services.ai_service import analyze_ticket_with_ai, generate_customer_reply

logger = logging.getLogger(__name__)


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _fetch_unseen_emails() -> list[dict]:
    """Sync IMAP fetch — runs in a thread executor."""
    if not settings.IMAP_HOST or not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        logger.warning("IMAP not configured, skipping email fetch")
        return []

    messages = []
    try:
        with imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT) as imap:
            imap.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            imap.select("INBOX")
            _, id_list = imap.search(None, "UNSEEN")

            for msg_id in id_list[0].split():
                _, data = imap.fetch(msg_id, "(RFC822)")
                raw = data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_header_value(msg.get("Subject"))
                from_ = _decode_header_value(msg.get("From"))

                # Extract plain-text body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="replace",
                                )
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(
                            msg.get_content_charset() or "utf-8",
                            errors="replace",
                        )

                # Pull bare email address from "Name <addr>" format
                sender_email = from_
                if "<" in from_ and ">" in from_:
                    sender_email = from_.split("<")[1].rstrip(">").strip()

                # Mark as Seen so we don't pick it up again
                imap.store(msg_id, "+FLAGS", "\\Seen")

                messages.append(
                    {
                        "subject": subject,
                        "from": from_,
                        "email": sender_email,
                        "body": body,
                        "date": datetime.now(timezone.utc),
                    }
                )
    except Exception as e:
        logger.error(f"IMAP error: {e}")

    return messages


async def poll_imap_once() -> None:
    """Fetch unseen emails, create/append Ticket records, trigger AI analysis."""
    loop = asyncio.get_event_loop()
    messages = await loop.run_in_executor(None, _fetch_unseen_emails)

    if not messages:
        return

    logger.info(f"Fetched {len(messages)} new email(s)")

    for msg in messages:
        try:
            async with AsyncSessionLocal() as session:
                query = select(Ticket).where(
                    Ticket.email == msg["email"],
                    Ticket.status != "closed"
                ).order_by(desc(Ticket.date_received)).limit(1)
                result = await session.execute(query)
                existing_ticket = result.scalars().first()

                if existing_ticket:
                    # APPEND TO EXISTING TICKET
                    ticket_id = existing_ticket.id
                    user_msg_text = f"От: {msg['from']}\nТема: {msg['subject']}\n\n{msg['body']}"
                    
                    user_msg = ChatMessage(ticket_id=ticket_id, role="user", text=user_msg_text)
                    session.add(user_msg)
                    
                    # Intercept call for operator
                    if "вызвать оператора" in msg["body"].lower():
                        existing_ticket.status = "needs_operator"
                        bot_text = "Оператор подключен к диалогу. Ожидайте ответа."
                        bot_msg = ChatMessage(ticket_id=ticket_id, role="bot", text=bot_text)
                        session.add(bot_msg)
                        await session.commit()
                        
                        await send_email_response(msg["email"], msg["subject"], bot_text)
                        continue
                    
                    await session.commit()
                    
                    # Generate AI Reply based on chat history
                    chat_query = select(ChatMessage).where(ChatMessage.ticket_id == ticket_id).order_by(ChatMessage.created_at)
                    chat_res = await session.execute(chat_query)
                    history = [{"role": m.role, "text": m.text} for m in chat_res.scalars().all()]
                    
                    draft = await generate_customer_reply(existing_ticket.original_email, history)
                    bot_text = draft + "\n\n💡 Если нужно вызвать оператора, напишите — вызвать оператора"
                    
                    bot_msg = ChatMessage(ticket_id=ticket_id, role="bot", text=bot_text)
                    session.add(bot_msg)
                    await session.commit()
                    
                    await send_email_response(msg["email"], msg["subject"], bot_text)
                    
                else:
                    # CREATE NEW TICKET
                    ticket = Ticket(
                        date_received=msg["date"],
                        email=msg["email"],
                        original_email=(f"От: {msg['from']}\nТема: {msg['subject']}\n\n{msg['body']}"),
                        status="open",
                    )
                    session.add(ticket)
                    await session.commit()
                    await session.refresh(ticket)
                    
                    # Out of transaction AI Call
                    ticket_id = ticket.id
                    ticket_text = ticket.original_email
                    ai_result = await analyze_ticket_with_ai(ticket_text)
                    
                    # Update fields
                    t = await session.get(Ticket, ticket_id)
                    t.sentiment = ai_result.get("sentiment")
                    t.category = ai_result.get("category")
                    t.ai_response = ai_result.get("draft_response")
                    t.full_name = ai_result.get("full_name")
                    t.company = ai_result.get("company")
                    t.phone = ai_result.get("phone")
                    t.device_serials = ai_result.get("device_serials") or []
                    t.device_type = ai_result.get("device_type")
                    t.summary = ai_result.get("summary")
                    
                    user_msg = ChatMessage(ticket_id=ticket_id, role="user", text=ticket_text)
                    session.add(user_msg)

                    draft = ai_result.get("draft_response", "")
                    bot_text = draft + "\n\n💡 Если нужно вызвать оператора, напишите — вызвать оператора"
                    bot_msg = ChatMessage(ticket_id=ticket_id, role="bot", text=bot_text)
                    session.add(bot_msg)
                    
                    if "вызвать оператора" in msg["body"].lower():
                         t.status = "needs_operator"
                         
                    await session.commit()
                    
                    await send_email_response(msg["email"], msg["subject"], bot_text)

        except Exception as e:
            logger.error(f"Error processing email from {msg.get('email')}: {e}")


async def send_email_response(to_email: str, subject: str, body: str) -> None:
    """Send an email via SMTP using aiosmtplib."""
    if not settings.SMTP_HOST or not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        raise RuntimeError("SMTP не настроен — задайте SMTP_HOST, EMAIL_USER, EMAIL_PASSWORD")

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = reply_subject
    msg["From"] = settings.EMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.EMAIL_USER,
        password=settings.EMAIL_PASSWORD,
        start_tls=True,
    )
    logger.info(f"Email sent to {to_email}")


async def start_email_polling(interval: int = 60) -> None:
    """Infinite async loop — polls IMAP every `interval` seconds."""
    logger.info(f"Email polling started (interval={interval}s)")
    while True:
        try:
            await poll_imap_once()
        except Exception as e:
            logger.error(f"Email polling iteration error: {e}")
        await asyncio.sleep(interval)
