import asyncio
import email
import logging
import re
from email import policy
from datetime import datetime, timezone

import aioimaplib

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ticket import Ticket
from app.routers.tickets import process_ticket_ai

logger = logging.getLogger(__name__)

async def process_email(raw_email_bytes: bytes):
    try:
        msg = email.message_from_bytes(raw_email_bytes, policy=policy.default)
        
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        
        # Разбираем email-адрес из строки 'Имя <email@example.com>'
        email_match = re.search(r'<([^>]+)>', sender)
        sender_email = email_match.group(1) if email_match else sender
        sender_name = sender.split('<')[0].strip() if '<' in sender else sender

        # Достаем текст письма (plaintext предпочтительнее)
        body_part = msg.get_body(preferencelist=('plain', 'html'))
        if body_part:
            body = body_part.get_content()
        else:
            body = ""
            
        full_text = f"Тема: {subject}\n\n{body}".strip()

        # Сохраняем заявку в БД
        async with AsyncSessionLocal() as session:
            ticket = Ticket(
                date_received=datetime.now(timezone.utc),
                full_name=sender_name,
                email=sender_email,
                original_email=full_text,
                status="open",
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            ticket_id = ticket.id

        # Передаем заявку AI на анализ в фоне
        asyncio.create_task(process_ticket_ai(ticket_id, full_text))
        logger.info(f"Успешно обработано письмо от {sender_email}, создана заявка #{ticket_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке письма: {e}")

async def email_listener_loop():
    if not settings.IMAP_HOST or not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        logger.warning("Пропущены настройки IMAP. Фоновый слушатель почты не запущен.")
        return

    logger.info(f"Запуск IMAP-слушателя для {settings.EMAIL_USER} на {settings.IMAP_HOST}:{settings.IMAP_PORT}")

    while True:
        try:
            imap_client = aioimaplib.IMAP4_SSL(host=settings.IMAP_HOST, port=settings.IMAP_PORT)
            await imap_client.wait_hello_from_server()
            await imap_client.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            await imap_client.select('INBOX')
            
            while True:
                # Ищем только новые (непрочитанные) письма
                resp, data = await imap_client.search('UNSEEN')
                
                if resp == 'OK' and data and data[0]:
                    message_numbers = data[0].split()
                    for num_bytes in message_numbers:
                        num = num_bytes.decode('utf-8')
                        res, msg_data = await imap_client.fetch(num, '(RFC822)')
                        
                        if res == 'OK':
                            raw_email = None
                            for response_part in msg_data:
                                if isinstance(response_part, tuple):
                                    raw_email = response_part[1]
                                    break
                            
                            if raw_email:
                                await process_email(raw_email)
                                
                await asyncio.sleep(10)  # Проверяем почту каждые 10 секунд
        except Exception as e:
            logger.error(f"Ошибка IMAP: {e}. Переподключение через 30 секунд...")
            await asyncio.sleep(30)
