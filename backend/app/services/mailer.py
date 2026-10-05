"""Outgoing e-mail. SMTP when SMTP_HOST is configured (e.g. Mailpit in docker-compose), else log."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("mailer")


def send_email(to: str, subject: str, body: str) -> None:
    s = get_settings()
    if not s.smtp_host:
        log.warning("E-mail to %s: %s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=5) as smtp:
            smtp.send_message(msg)
    except OSError:
        log.exception("Failed to send e-mail to %s", to)
