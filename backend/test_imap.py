import imaplib
from email.header import decode_header
import email
from datetime import datetime, timezone

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
EMAIL_USER = "proftestium56@gmail.com"
EMAIL_PASSWORD = "lhnugcswjpyrtmhc"

def test_imap():
    print("Connecting to IMAP...")
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            print("Logging in...")
            imap.login(EMAIL_USER, EMAIL_PASSWORD)
            print("Select INBOX...")
            imap.select("INBOX")
            print("Searching UNSEEN...")
            status, id_list = imap.search(None, "UNSEEN")
            print(f"Status: {status}, id_list: {id_list}")
            
            message_ids = id_list[0].split()
            print(f"Found {len(message_ids)} unseen messages.")
            for msg_id in message_ids:
                print(f"Fetching {msg_id}...")
                _, data = imap.fetch(msg_id, "(RFC822)")
                print(f"Data length: len({data})")
    except Exception as e:
        print(f"Error: {e}")

test_imap()
