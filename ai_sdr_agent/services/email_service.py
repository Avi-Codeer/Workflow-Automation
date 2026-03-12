"""
Email sender service.
Supports Gmail SMTP with rate-limiting to avoid being flagged as spam.
"""

from __future__ import annotations

import logging
import smtplib
import time
from collections import deque
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ai_sdr_agent.config.settings import (
    EMAIL_RATE_LIMIT,
    SENDER_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token-bucket style rate limiter.
    Allows at most *max_calls* calls per *period* seconds.
    """

    def __init__(self, max_calls: int, period: float = 60.0) -> None:
        self._max_calls = max_calls
        self._period = period
        self._timestamps: deque[float] = deque()

    def wait(self) -> None:
        """Block until sending the next email is within the allowed rate."""
        now = time.monotonic()
        # Remove timestamps older than the rate window
        while self._timestamps and now - self._timestamps[0] >= self._period:
            self._timestamps.popleft()

        if len(self._timestamps) >= self._max_calls:
            oldest = self._timestamps[0]
            sleep_for = self._period - (now - oldest)
            if sleep_for > 0:
                logger.debug("Rate limit reached. Sleeping %.1fs …", sleep_for)
                time.sleep(sleep_for)

        self._timestamps.append(time.monotonic())


# Module-level singleton so the limiter state is shared across all calls
_rate_limiter = RateLimiter(max_calls=EMAIL_RATE_LIMIT)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email via SMTP.

    Args:
        to_email: Recipient email address.
        subject:  Email subject line.
        body:     Email body text (plain text).

    Returns:
        ``True`` on success, ``False`` on failure.

    Raises:
        ValueError: When required SMTP settings are missing.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set in your .env file."
        )
    if not SENDER_EMAIL:
        raise ValueError("SENDER_EMAIL must be set in your .env file.")

    # Enforce rate limit before attempting to send
    _rate_limiter.wait()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        logger.info("Email sent to %s | subject: %s", to_email, subject)
        return True
    except smtplib.SMTPException as exc:
        logger.error(
            "Failed to send email to %s via %s:%d: %s",
            to_email,
            SMTP_HOST,
            SMTP_PORT,
            exc,
        )
        return False
