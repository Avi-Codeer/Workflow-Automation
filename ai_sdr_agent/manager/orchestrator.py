"""
Orchestrator – the central manager agent.
Coordinates the full outbound sales pipeline:

  Company List
       ↓
  Lead Finder Agent
       ↓
  Company Research Agent
       ↓
  Email Personalization Agent
       ↓
  Email Sender
       ↓
  Follow-up Scheduler
       ↓
  Reply Detection
       ↓
  Human Notification
"""

from __future__ import annotations

import csv
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from ai_sdr_agent.agents import (
    email_agent,
    followup_agent,
    lead_agent,
    reply_agent,
    research_agent,
)
from ai_sdr_agent.config.settings import COMPANIES_CSV
from ai_sdr_agent.services.email_service import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def notify_human(sender: str, subject: str, body: str) -> None:
    """
    Notify a human when a positive reply is detected.

    Currently logs the notification; extend this to send a Slack message,
    a webhook, or an internal email.

    Args:
        sender: Email address of the lead who replied.
        subject: Subject of the reply.
        body: Body of the reply.
    """
    logger.info(
        "🔔 HUMAN NOTIFICATION – Positive reply received!\n"
        "  From   : %s\n"
        "  Subject: %s\n"
        "  Body   :\n%s",
        sender,
        subject,
        body,
    )


def _on_positive_reply(sender: str, subject: str, body: str) -> None:
    """Cancel follow-ups and notify a human on positive reply."""
    followup_agent.cancel_followups(sender)
    notify_human(sender, subject, body)


def _on_negative_reply(sender: str, subject: str, body: str) -> None:  # noqa: ARG001
    """Cancel follow-ups on negative reply (opt-out / not interested)."""
    logger.info("Negative reply from %s – cancelling follow-ups.", sender)
    followup_agent.cancel_followups(sender)


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_companies(csv_path: str = COMPANIES_CSV) -> list[str]:
    """
    Load the list of company names from a CSV file.

    The CSV must contain a ``company`` column (case-insensitive header match).

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of company name strings.
    """
    companies: list[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Case-insensitive key lookup
            name = next(
                (v for k, v in row.items() if k.strip().lower() == "company"),
                None,
            )
            if name and name.strip():
                companies.append(name.strip())
    logger.info(
        "Loaded %d %s from %s",
        len(companies),
        "company" if len(companies) == 1 else "companies",
        csv_path,
    )
    return companies


# ---------------------------------------------------------------------------
# Per-lead pipeline
# ---------------------------------------------------------------------------

def _process_lead(
    lead: dict[str, str],
    company_name: str,
    company_info: dict[str, str],
    sent_at: datetime,
) -> None:
    """Run the email + follow-up pipeline for a single lead."""
    lead_name = lead.get("name", "")
    job_title = lead.get("title", "")
    lead_email = lead.get("email", "")

    if not lead_email:
        logger.warning("Skipping lead '%s' – no email address.", lead_name)
        return

    # 1. Generate personalized email
    email_content: dict[str, str] = email_agent.generate_email(
        lead_name=lead_name,
        job_title=job_title,
        company_name=company_name,
        company_summary=company_info.get("summary", ""),
    )

    # 2. Send initial email
    success = send_email(
        to_email=lead_email,
        subject=email_content["email_subject"],
        body=email_content["email_body"],
    )

    if not success:
        logger.warning("Initial email to %s failed – skipping follow-ups.", lead_email)
        return

    # 3. Schedule follow-ups
    followup_agent.schedule_followups(
        lead=lead,
        company_name=company_name,
        initial_sent_at=sent_at,
    )


# ---------------------------------------------------------------------------
# Per-company pipeline
# ---------------------------------------------------------------------------

def _process_company(company_name: str) -> None:
    """Run the full pipeline for a single company."""
    logger.info("═══ Processing company: %s ═══", company_name)

    # 1. Find decision makers
    leads: list[dict[str, str]] = lead_agent.find_decision_makers(company_name)
    if not leads:
        logger.info("No leads found for '%s'. Skipping.", company_name)
        return

    # 2. Research the company
    company_info: dict[str, str] = research_agent.research_company(company_name)

    sent_at = datetime.now(tz=timezone.utc)

    # 3-5. For each lead: generate email, send, schedule follow-ups
    for lead in leads:
        _process_lead(lead, company_name, company_info, sent_at)


# ---------------------------------------------------------------------------
# Follow-up runner
# ---------------------------------------------------------------------------

def process_due_followups() -> None:
    """
    Check for due follow-ups and send them.
    Call this on a scheduler (e.g., cron / APScheduler) once per day.
    """
    due: list[dict[str, Any]] = followup_agent.get_due_followups()
    if not due:
        logger.info("No follow-ups are due right now.")
        return

    logger.info("Processing %d due follow-up(s) …", len(due))
    for record in due:
        follow_up_email = followup_agent.generate_followup_email(record)
        success = send_email(
            to_email=record["lead_email"],
            subject=follow_up_email["email_subject"],
            body=follow_up_email["email_body"],
        )
        if success:
            followup_agent.mark_followup_sent(
                record["lead_email"], record["follow_up_number"]
            )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(csv_path: str = COMPANIES_CSV) -> None:
    """
    Execute the full outbound sales pipeline.

    Args:
        csv_path: Path to the companies CSV file.
    """
    logger.info("Starting AI SDR Agent pipeline …")

    companies = load_companies(csv_path)
    for company in companies:
        try:
            _process_company(company)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error processing '%s': %s", company, exc, exc_info=True)

    # Check inbox for replies (positive → notify human; negative → cancel follow-ups)
    try:
        reply_agent.check_inbox(
            on_positive_reply=_on_positive_reply,
            on_negative_reply=_on_negative_reply,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reply detection skipped: %s", exc)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run()
