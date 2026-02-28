#!/usr/bin/env python3
"""
Класс для отправки писем через SMTP с поддержкой вложений
"""

import smtplib
import os
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders, message_from_bytes
from typing import List, Optional, Union
from pathlib import Path


class EmailSender:
    """
    Класс для отправки писем через SMTP с поддержкой вложений
    """

    def __init__(self, email_address: str, password: str,
                 smtp_server: str = 'smtp.gmail.com',
                 smtp_port: int = 587):
        """
        :param email_address: email отправителя
        :param password: пароль (для Gmail - пароль приложения)
        :param smtp_server: SMTP сервер
        :param smtp_port: порт SMTP (587 для TLS)
        """
        self.email_address = email_address
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def _get_mime_type(self, file_path: Path) -> str:
        """Определение MIME типа файла"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def _attach_file(self, msg: MIMEMultipart, file_path: Union[str, Path]) -> bool:
        """Прикрепление файла к сообщению"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"Файл не найден: {file_path}")
                return False

            mime_type = self._get_mime_type(file_path)
            main_type, sub_type = mime_type.split('/', 1)

            with open(file_path, 'rb') as f:
                if main_type == 'text':
                    part = MIMEText(f.read().decode('utf-8', errors='ignore'),
                                    sub_type, 'utf-8')
                else:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(f.read())
                    encoders.encode_base64(part)

            part.add_header('Content-Disposition', f'attachment; filename="{file_path.name}"')
            msg.attach(part)
            return True

        except Exception as e:
            print(f"Ошибка прикрепления файла {file_path}: {e}")
            return False

    def send_mail(self,
                  to_email: str,
                  subject: str,
                  html_content: str,
                  attachments: Optional[List[Union[str, Path]]] = None,
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None) -> bool:
        """
        Отправка HTML письма (опционально с вложениями)

        :param to_email: email получателя
        :param subject: тема письма
        :param html_content: HTML код письма
        :param attachments: список путей к файлам (опционально)
        :param cc: список email для копии (опционально)
        :param bcc: список email для скрытой копии (опционально)
        :return: True если отправка успешна
        """
        try:
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)

            # Добавляем HTML тело
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Прикрепляем файлы (если есть)
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            # Отправляем
            all_recipients = [to_email]
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.password)
                server.send_message(msg)

            print(f"Письмо отправлено на {to_email}")
            return True

        except Exception as e:
            print(f"Ошибка отправки: {e}")
            return False


# Примеры использования:
if __name__ == '__main__':
    # Создаем отправителя
    sender = EmailSender(
        email_address='proftestium56@gmail.com',
        password='lhnu gcsw jpyr tmhc'  # Пароль приложения для Gmail
    )

    # # 1. Простое HTML письмо без вложений
    # sender.send_mail(
    #     to_email='client@example.com',
    #     subject='Привет',
    #     html_content='<h1>Здравствуйте!</h1><p>Это простое письмо</p>'
    # )
    heading = ''
    message_text = ''
    # 2. HTML письмо с вложениями
    sender.send_mail(
        to_email='yaSemiYT@bk.ru',
        subject='🛠️Ответ поддержки компании ЭРИС🛠️',
        html_content=f'<h1>{heading}</h1>'
                     f'<p1>{message_text}</p1>'
                     f'<p>©2006-2026  Компания «ЭРИС»</p>',
        attachments=['Beggar.png']
    )

    # # 3. С копией и скрытой копией
    # sender.send_mail(
    #     to_email='client@example.com',
    #     subject='Важно',
    #     html_content='<b>Важное сообщение</b>',
    #     cc=['manager@example.com'],
    #     bcc=['archive@example.com']
    # )