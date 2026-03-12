"""
Reply Detection Agent.
Monitors an inbox (IMAP) and classifies incoming replies as
Positive / Negative / Neutral.
"""

from __future__ import annotations

import email
import imaplib
import logging
from typing import Callable

from ai_sdr_agent.services.openai_service import chat_completion
from ai_sdr_agent.config.settings import SMTP_USER, SMTP_PASSWORD

logger = logging.getLogger(__name__)

# Keywords used for quick heuristic classification before calling the LLM
_POSITIVE_KEYWORDS = [
    "interested",
    "tell me more",
    "schedule a call",
    "let's connect",
    "sounds good",
    "would love to",
    "yes",
    "sure",
]
_NEGATIVE_KEYWORDS = [
    "not interested",
    "unsubscribe",
    "remove me",
    "stop emailing",
    "do not contact",
    "opt out",
    "no thanks",
]

_CLASSIFICATION_SYSTEM_PROMPT = (
    "You are an email classifier. Given an email reply, classify it as one of: "
    "'positive', 'negative', or 'neutral'. "
    "Positive means the recipient is interested (e.g., wants more info, "
    "wants to schedule a call). "
    "Negative means they are not interested or want to unsubscribe. "
    "Neutral means anything else (out-of-office, unclear, etc.). "
    "Reply with ONLY one word: positive, negative, or neutral."
)


def classify_reply(reply_text: str) -> str:
    """
    Classify an email reply as 'positive', 'negative', or 'neutral'.

    First performs a fast keyword check; falls back to the LLM for
    ambiguous cases.

    Args:
        reply_text: The plain-text body of the reply email.

    Returns:
        One of ``'positive'``, ``'negative'``, or ``'neutral'``.
    """
    lower = reply_text.lower()

    # Fast heuristic – check negative first to avoid false positives
    # (e.g. "not interested" contains "interested")
    for kw in _NEGATIVE_KEYWORDS:
        if kw in lower:
            return "negative"
    for kw in _POSITIVE_KEYWORDS:
        if kw in lower:
            return "positive"

    # Fall back to LLM classification
    result = chat_completion(
        prompt=f"Email reply:\n{reply_text}",
        system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
        max_tokens=5,
        temperature=0.0,
    ).lower().strip().rstrip(".")

    if result in {"positive", "negative", "neutral"}:
        return result
    return "neutral"


def check_inbox(
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    mailbox: str = "INBOX",
    on_positive_reply: Callable[[str, str, str], None] | None = None,
    on_negative_reply: Callable[[str, str, str], None] | None = None,
) -> list[dict[str, str]]:
    """
    Connect to IMAP, fetch unseen emails, classify replies, and invoke
    the appropriate callback.

    Args:
        imap_host: IMAP server hostname.
        imap_port: IMAP server port (SSL).
        mailbox: Mailbox to check (default ``"INBOX"``).
        on_positive_reply: Optional callback called with
            ``(sender, subject, body)`` for positive replies.
        on_negative_reply: Optional callback called with
            ``(sender, subject, body)`` for negative replies.

    Returns:
        A list of dicts ``{sender, subject, body, classification}`` for
        every reply processed.

    Raises:
        ValueError: When SMTP_USER or SMTP_PASSWORD are not configured.
        imaplib.IMAP4.error: On IMAP connection / authentication failures.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set to enable reply detection."
        )

    processed: list[dict[str, str]] = []

    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port) as mail:
            mail.login(SMTP_USER, SMTP_PASSWORD)
            mail.select(mailbox)

            _, message_ids = mail.search(None, "UNSEEN")
            for msg_id in message_ids[0].split():
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]  # type: ignore[index]
                msg = email.message_from_bytes(raw)

                sender = msg.get("From", "")
                subject = msg.get("Subject", "")
                body = _extract_text(msg)

                classification = classify_reply(body)
                logger.info(
                    "Reply from %s classified as: %s", sender, classification
                )

                if classification == "positive" and on_positive_reply:
                    on_positive_reply(sender, subject, body)
                elif classification == "negative" and on_negative_reply:
                    on_negative_reply(sender, subject, body)

                processed.append(
                    {
                        "sender": sender,
                        "subject": subject,
                        "body": body,
                        "classification": classification,
                    }
                )
    except imaplib.IMAP4.error as exc:
        logger.error("IMAP error: %s", exc)
        raise

    return processed


def _extract_text(msg: email.message.Message) -> str:
    """
    Extract plain-text content from an email message, handling multipart.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode(errors="replace")
    return ""
