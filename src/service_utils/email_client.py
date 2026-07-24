"""
Gmail SMTP email sending.

The Gmail address and app password are fetched from SSM Parameter Store on
first use and cached in-process, so subsequent warm Lambda invocations skip
SSM entirely (mirrors the GOOGLE_API_KEY caching in react_agent.py).
"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional
import boto3
from src.service_utils.logger import get_logger

logger = get_logger()

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465

# Populated on first call, reused for the lifetime of the Lambda container.
_CREDENTIALS_CACHE: dict[str, str] = {}


def _load_credentials() -> tuple[str, str]:
    """Fetch the Gmail address/app-password from SSM once, then reuse the cache."""
    if "address" not in _CREDENTIALS_CACHE or "password" not in _CREDENTIALS_CACHE:
        address_path = os.environ["GMAIL_ADDRESS_PATH"]
        password_path = os.environ["GMAIL_APP_PASSWORD_PATH"]
        client = boto3.client("ssm")
        _CREDENTIALS_CACHE["address"] = client.get_parameter(
            Name=address_path, WithDecryption=True
        )["Parameter"]["Value"]
        _CREDENTIALS_CACHE["password"] = client.get_parameter(
            Name=password_path, WithDecryption=True
        )["Parameter"]["Value"]
        logger.info("Gmail credentials loaded from SSM")
    return _CREDENTIALS_CACHE["address"], _CREDENTIALS_CACHE["password"]


def send_email(subject: str, body: str, to_address: Optional[str] = None) -> None:
    """
    Send a plain-text email via Gmail SMTP.
    to_address defaults to the Gmail account itself (self-notification).
    """
    address, password = _load_credentials()
    recipient = to_address or address

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = address
    message["To"] = recipient

    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
        server.login(address, password)
        server.sendmail(address, [recipient], message.as_string())
    logger.info("Email sent to %s", recipient)


def send_meeting_notification(
    title: str,
    scheduled_at: datetime,
    description: Optional[str] = None,
    attendee_email: Optional[str] = None,
) -> None:
    """Notify the Gmail account owner of a new meeting, and confirm it with the attendee if provided."""
    details = (
        f"Title: {title}\n"
        f"Scheduled at: {scheduled_at.isoformat()}\n"
        f"Description: {description or '-'}"
    )
    send_email(
        subject=f"New meeting scheduled: {title}",
        body=f"{details}\nAttendee: {attendee_email or '-'}",
    )
    if attendee_email:
        send_email(
            subject=f"Meeting confirmed: {title}",
            body=f"Your meeting has been scheduled.\n\n{details}",
            to_address=attendee_email,
        )
