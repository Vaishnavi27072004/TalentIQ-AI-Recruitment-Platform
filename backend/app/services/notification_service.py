"""Email + in-app notifications.

HONESTY RULE: if SMTP is not configured we do NOT pretend to send. The message is written to
notification_log.txt and the function returns "logged" (never "sent").
Returns one of: "sent", "logged", "failed".
"""
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings, BACKEND_DIR
from app.models.tables import Notification

DEV_LOG_FILE = Path(BACKEND_DIR) / "notification_log.txt"


def send_email(to_address: str, subject: str, body: str) -> str:
    if not settings.smtp_host:
        with open(DEV_LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"[DEV LOG - NOT SENT] {datetime.utcnow().isoformat()} to={to_address} subject={subject}\n{body}\n---\n")
        return "logged"
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.smtp_from, to_address, subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return "sent"
    except Exception as error:  # a mail problem must never break the recruitment action
        with open(DEV_LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"[EMAIL FAILED] to={to_address} subject={subject} error={error}\n")
        return "failed"


def notify(db: Session, user_id: int | None, email: str | None, subject: str, body: str) -> str:
    """Create the in-app notification (if the person has an account) and attempt the email."""
    if user_id:
        db.add(Notification(user_id=user_id, message=subject))
    return send_email(email, subject, body) if email else "logged"
