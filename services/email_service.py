"""
=========================================================
Project : Sridevi Enterprises
File    : email_service.py
Purpose : Minimal outgoing email (Password Management - reset links).

          Standard library only (smtplib + email.message) - no new
          dependency. Configured entirely from Config.SMTP_* and
          Config.PUBLIC_BASE_URL (see config.py and .env.example).

          Never logs message bodies: a reset email's body contains a live
          reset token. Failures are logged with the exception type only.

Author  : Srikar
=========================================================
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from config import Config

logger = logging.getLogger(__name__)


class EmailNotConfigured(Exception):
    """Raised when outgoing email (or the public base URL) is not configured."""


def public_base_url() -> str | None:
    """
    Return the configured public site URL to build emailed links from, or
    None when it is missing or unsafe. Outside DEBUG only https:// is
    accepted, so a production reset link can never travel over plain HTTP.
    """

    base = Config.PUBLIC_BASE_URL
    if not base:
        return None

    lowered = base.lower()
    if lowered.startswith("https://"):
        return base
    if lowered.startswith("http://") and Config.DEBUG:
        return base
    return None


def is_email_configured() -> bool:
    """True when reset emails can actually be sent."""

    return bool(Config.SMTP_HOST and Config.SMTP_SENDER and public_base_url())


def send_email(to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email. Raises EmailNotConfigured when SMTP is not set
    up, or the underlying smtplib/OSError on delivery failure - callers
    decide what the user sees.
    """

    if not is_email_configured():
        raise EmailNotConfigured()

    message = EmailMessage()
    message["From"] = Config.SMTP_SENDER
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()

    if Config.SMTP_USE_SSL:
        server = smtplib.SMTP_SSL(
            Config.SMTP_HOST, Config.SMTP_PORT, timeout=Config.SMTP_TIMEOUT_SECONDS, context=context
        )
    else:
        server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=Config.SMTP_TIMEOUT_SECONDS)

    try:
        if not Config.SMTP_USE_SSL and Config.SMTP_USE_TLS:
            server.starttls(context=context)
        if Config.SMTP_USERNAME:
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.send_message(message)
    finally:
        try:
            server.quit()
        except Exception:
            pass
