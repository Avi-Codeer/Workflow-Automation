"""
Follow-up Scheduler Agent.
Schedules and generates follow-up emails for leads that have not replied.

NOTE: Follow-up state is stored in memory. On process restart all pending
follow-up records will be lost. For production use, replace ``_followup_store``
with a persistent store (database, Redis, etc.).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ai_sdr_agent.config.settings import FOLLOWUP_DAYS
from ai_sdr_agent.services.openai_service import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a B2B sales development representative. "
    "Write a brief, friendly follow-up email (40–70 words). "
    "Vary the tone slightly from the initial email. "
    "End with a soft CTA. No buzzwords. "
    "Respond ONLY in the format:\n"
    "Subject: <subject>\n"
    "Body:\n"
    "<body>"
)

# In-memory store: lead_email → list of scheduled follow-up records
# Each record: {due_at, follow_up_number, lead_name, job_title, company_name, sent}
_followup_store: dict[str, list[dict[str, Any]]] = {}


def schedule_followups(
    lead: dict[str, str],
    company_name: str,
    initial_sent_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Create follow-up schedule entries for a lead.

    Args:
        lead: Dict with at minimum ``name``, ``title``, and ``email``.
        company_name: Name of the lead's company.
        initial_sent_at: When the initial email was sent (defaults to now).

    Returns:
        List of follow-up schedule records created.
    """
    email = lead.get("email", "")
    if not email:
        logger.warning("Cannot schedule follow-ups: lead has no email.")
        return []

    sent_at = initial_sent_at or datetime.now(tz=timezone.utc)
    schedule: list[dict[str, Any]] = []

    for i, day_offset in enumerate(FOLLOWUP_DAYS, start=1):
        due = sent_at + timedelta(days=day_offset)
        record: dict[str, Any] = {
            "lead_email": email,
            "lead_name": lead.get("name", ""),
            "job_title": lead.get("title", ""),
            "company_name": company_name,
            "follow_up_number": i,
            "due_at": due,
            "sent": False,
        }
        schedule.append(record)

    _followup_store[email] = schedule
    logger.info(
        "Scheduled %d follow-up(s) for %s (%s)",
        len(schedule),
        lead.get("name", email),
        company_name,
    )
    return schedule


def get_due_followups(as_of: datetime | None = None) -> list[dict[str, Any]]:
    """
    Return all unsent follow-ups that are due as of *as_of* (defaults to now).

    Args:
        as_of: The reference datetime. Defaults to ``datetime.now(tz=utc)``.

    Returns:
        List of due follow-up records.
    """
    now = as_of or datetime.now(tz=timezone.utc)
    due: list[dict[str, Any]] = []
    for records in _followup_store.values():
        for record in records:
            if not record["sent"] and record["due_at"] <= now:
                due.append(record)
    return due


def generate_followup_email(record: dict[str, Any]) -> dict[str, str]:
    """
    Use the LLM to write a follow-up email for *record*.

    Args:
        record: A follow-up schedule record (from :func:`schedule_followups`).

    Returns:
        Dict with ``email_subject`` and ``email_body``.
    """
    follow_up_number = record.get("follow_up_number", 1)
    ordinal = {1: "first", 2: "second", 3: "third"}.get(
        follow_up_number, f"#{follow_up_number}"
    )

    prompt = (
        f"Recipient: {record.get('lead_name', 'there')}\n"
        f"Title: {record.get('job_title', '')}\n"
        f"Company: {record.get('company_name', '')}\n"
        f"This is the {ordinal} follow-up email (no response to the initial outreach).\n"
        "Write the follow-up now."
    )

    raw = chat_completion(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        max_tokens=200,
    )

    subject = ""
    body = ""

    subject_match = re.search(r"(?i)^subject:\s*(.+)", raw, re.MULTILINE)
    if subject_match:
        subject = subject_match.group(1).strip()

    body_match = re.search(r"(?i)^body:\s*\n([\s\S]+)", raw, re.MULTILINE)
    if body_match:
        body = body_match.group(1).strip()
    else:
        body = re.sub(r"(?i)^subject:.+\n?", "", raw, count=1).strip()
        body = re.sub(r"(?i)^body:\s*\n?", "", body, count=1).strip()

    return {"email_subject": subject, "email_body": body}


def mark_followup_sent(lead_email: str, follow_up_number: int) -> None:
    """
    Mark a specific follow-up as sent so it is not re-sent.

    Args:
        lead_email: Email address of the lead.
        follow_up_number: The 1-based follow-up number to mark.
    """
    for record in _followup_store.get(lead_email, []):
        if record["follow_up_number"] == follow_up_number:
            record["sent"] = True
            logger.debug(
                "Marked follow-up #%d as sent for %s",
                follow_up_number,
                lead_email,
            )
            return


def cancel_followups(lead_email: str) -> None:
    """
    Cancel all pending follow-ups for a lead (e.g., after a positive reply).

    Args:
        lead_email: Email address of the lead.
    """
    if lead_email in _followup_store:
        for record in _followup_store[lead_email]:
            record["sent"] = True  # Mark as sent so they won't fire
        logger.info("Cancelled all follow-ups for %s", lead_email)
