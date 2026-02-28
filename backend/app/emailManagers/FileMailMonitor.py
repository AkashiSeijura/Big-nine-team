import imaplib
import email
import os
import re
import time
import signal
import sys
from email.header import decode_header
from datetime import datetime
from typing import Tuple
import hashlib
import json


class FileMailMonitor:
    """Монитор почты с сохранением в файлы"""

    def __init__(self, email_address: str, app_password: str,
                 storage_dir: str = 'saved_emails', check_interval: int = 5):
        """
        :param email_address: Gmail адрес
        :param app_password: пароль приложения Gmail
        :param storage_dir: директория для сохранения писем
        :param check_interval: интервал проверки в секундах
        """
        self.email_address = email_address
        self.app_password = app_password
        self.storage_dir = storage_dir
        self.check_interval = check_interval
        self.connection = None
        self.running = True

        # Создаем директорию для хранения
        os.makedirs(storage_dir, exist_ok=True)
        print(f"Директория для писем: {storage_dir}")

    def connect(self) -> bool:
        """Подключение к IMAP"""
        try:
            if self.connection:
                try:
                    self.connection.noop()
                    return True
                except:
                    self.disconnect()

            self.connection = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            self.connection.login(self.email_address, self.app_password)
            print("Подключено к Gmail")
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    def disconnect(self):
        """Отключение"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None

    def decode_header_value(self, header: str) -> str:
        """Декодирование заголовка"""
        if not header:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    if encoding:
                        decoded_parts.append(part.decode(encoding, errors='ignore'))
                    else:
                        decoded_parts.append(part.decode('utf-8', errors='ignore'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(part))

        return ' '.join(decoded_parts)

    def extract_email(self, from_str: str) -> Tuple[str, str]:
        """Извлечение имени и email из строки From"""
        if not from_str:
            return "", ""

        decoded = self.decode_header_value(from_str)

        # Ищем email в скобках
        email_match = re.search(r'<(.+?)>', decoded)
        if email_match:
            email_addr = email_match.group(1).lower()
            name = decoded.replace(f'<{email_addr}>', '').strip().strip('"')
            return name, email_addr

        # Ищем email в строке
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', decoded.lower())
        if email_match:
            email_addr = email_match.group(0)
            name = decoded.replace(email_addr, '').strip().strip('"')
            return name, email_addr

        return decoded, decoded.lower()

    def get_message_id(self, email_message) -> str:
        """Получение уникального ID письма"""
        msg_id = email_message.get('Message-ID', '')
        if msg_id:
            # Очищаем от скобок
            msg_id = re.sub(r'[<>]', '', msg_id)
            return msg_id

        subject = email_message.get('Subject', '')
        date = email_message.get('Date', '')
        return hashlib.md5(f"{subject}{date}".encode()).hexdigest()

    def get_text_content(self, email_message) -> str:
        """Извлечение текста из письма"""
        text_content = []

        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" in content_disposition.lower() or part.get_filename():
                        continue

                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                text = payload.decode(charset, errors='ignore')
                                text_content.append(text)
                            except:
                                text = payload.decode('utf-8', errors='ignore')
                                text_content.append(text)
            else:
                payload = email_message.get_payload(decode=True)
                if payload:
                    charset = email_message.get_content_charset() or 'utf-8'
                    try:
                        text = payload.decode(charset, errors='ignore')
                        text_content.append(text)
                    except:
                        text = payload.decode('utf-8', errors='ignore')
                        text_content.append(text)
        except Exception as e:
            print(f"Ошибка извлечения текста: {e}")

        return '\n'.join(text_content)

    def save_attachments(self, email_message, email_dir: str) -> list:
        """Сохранение вложений"""
        saved_files = []

        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    filename = part.get_filename()
                    if filename:
                        filename = self.decode_header_value(filename)
                        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

                        payload = part.get_payload(decode=True)
                        if payload:
                            filepath = os.path.join(email_dir, filename)

                            # Если файл существует, добавляем номер
                            if os.path.exists(filepath):
                                name, ext = os.path.splitext(filename)
                                counter = 1
                                while os.path.exists(os.path.join(email_dir, f"{name}_{counter}{ext}")):
                                    counter += 1
                                filepath = os.path.join(email_dir, f"{name}_{counter}{ext}")

                            with open(filepath, 'wb') as f:
                                f.write(payload)

                            saved_files.append({
                                'filename': os.path.basename(filepath),
                                'size': len(payload),
                                'type': part.get_content_type()
                            })
        except Exception as e:
            print(f"Ошибка сохранения вложений: {e}")

        return saved_files

    def email_exists(self, message_id: str) -> bool:
        """Проверка, есть ли уже письмо"""
        # Ищем файл с таким message_id
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.storage_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('message_id') == message_id:
                            return True
                except:
                    continue
        return False

    def process_email(self, msg_id, email_message) -> bool:
        """Обработка одного письма"""
        try:
            # Получаем уникальный ID
            message_id = self.get_message_id(email_message)

            # Проверяем, не сохранено ли уже
            if self.email_exists(message_id):
                return False

            # Извлекаем данные
            from_str = email_message.get('From', '')
            name, email_addr = self.extract_email(from_str)
            subject = self.decode_header_value(email_message.get('Subject', ''))

            # Парсим дату
            date_str = email_message.get('Date', '')
            try:
                from email.utils import parsedate_to_datetime
                date_received = parsedate_to_datetime(date_str)
                date_str = date_received.isoformat()
            except:
                date_received = datetime.now()
                date_str = date_received.isoformat()

            # Получаем текст
            text_content = self.get_text_content(email_message)

            # Создаем директорию для письма
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            email_dir_name = f"{timestamp}_{message_id[:8]}"
            email_dir = os.path.join(self.storage_dir, email_dir_name)
            os.makedirs(email_dir, exist_ok=True)

            # Сохраняем вложения
            attachments = self.save_attachments(email_message, email_dir)

            # Сохраняем метаданные
            metadata = {
                'message_id': message_id,
                'date_received': date_str,
                'from_name': name,
                'from_email': email_addr,
                'subject': subject,
                'attachments': attachments,
                'saved_at': datetime.now().isoformat()
            }

            with open(os.path.join(email_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # Сохраняем текст письма
            with open(os.path.join(email_dir, 'content.txt'), 'w', encoding='utf-8') as f:
                f.write(f"From: {from_str}\n")
                f.write(f"Subject: {subject}\n")
                f.write(f"Date: {date_str}\n")
                f.write(f"Email: {email_addr}\n\n")
                f.write(text_content)

            # Сохраняем сырое письмо (опционально)
            raw_email = email_message.as_string()
            with open(os.path.join(email_dir, 'raw.eml'), 'w', encoding='utf-8') as f:
                f.write(raw_email)

            print(f"Сохранено письмо от {email_addr} в {email_dir_name}")
            return True

        except Exception as e:
            print(f"Ошибка обработки письма: {e}")
            return False

    def check_mail(self) -> int:
        """Проверка новых писем"""
        processed = 0

        try:
            if not self.connect():
                return processed

            # Выбираем папку входящие
            status, _ = self.connection.select('inbox')
            if status != 'OK':
                print("Не удалось выбрать папку inbox")
                return processed

            # Ищем все непрочитанные письма
            status, message_ids = self.connection.search(None, 'UNSEEN')
            if status != 'OK':
                print("Ошибка поиска писем")
                return processed

            if not message_ids[0]:
                return processed

            ids = message_ids[0].split()

            for msg_id in ids:
                try:
                    status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    email_message = email.message_from_bytes(msg_data[0][1])

                    if self.process_email(msg_id, email_message):
                        processed += 1

                    # Помечаем как прочитанное
                    self.connection.store(msg_id, '+FLAGS', '\\Seen')

                except Exception as e:
                    print(f"Ошибка обработки письма: {e}")
                    continue

            return processed

        except Exception as e:
            print(f"Ошибка проверки почты: {e}")
            return processed

    def run(self):
        """Основной цикл работы"""
        print(f"Запуск монитора почты (интервал: {self.check_interval}с)")

        while self.running:
            try:
                processed = self.check_mail()

                # Ждем
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                print(f"Критическая ошибка: {e}")
                time.sleep(self.check_interval)

        self.disconnect()

    def stop(self):
        """Остановка монитора"""
        self.running = False


def main():
    """Точка входа"""

    # Настройки Gmail (обязательно использовать пароль приложения!)
    GMAIL_CONFIG = {
        'email': 'proftestium56@gmail.com',
        'app_password': 'lhnu gcsw jpyr tmhc'
    }

    # Создаем монитор
    monitor = FileMailMonitor(
        email_address=GMAIL_CONFIG['email'],
        app_password=GMAIL_CONFIG['app_password'],
        storage_dir='saved_emails',  # Папка для писем
        check_interval=5
    )

    # Обработчик сигналов
    def signal_handler(signum, frame):
        print("\nОстановка...")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запускаем монитор
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nОстановка")
        monitor.stop()
    except Exception as e:
        print(f"Ошибка: {e}")
        monitor.stop()

if __name__ == '__main__':
    main()


