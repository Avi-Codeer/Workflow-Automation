"""
Email Personalization Agent.
Generates a personalized cold email given lead and company context.
"""

from __future__ import annotations

import logging
import re

from ai_sdr_agent.services.openai_service import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert B2B copywriter specializing in cold outreach. "
    "Your emails:\n"
    "- Are 80–120 words long\n"
    "- Have a conversational tone\n"
    "- Are personalized to the recipient's role\n"
    "- End with a soft call-to-action (e.g., 'Would you have 15 minutes this week?')\n"
    "- Avoid buzzwords and generic phrases\n\n"
    "Respond ONLY in the following format (no markdown, no extra text):\n"
    "Subject: <email subject>\n"
    "Body:\n"
    "<email body>"
)


def generate_email(
    lead_name: str,
    job_title: str,
    company_name: str,
    company_summary: str,
) -> dict[str, str]:
    """
    Generate a personalized cold email.

    Args:
        lead_name: Full name of the recipient.
        job_title: Job title of the recipient.
        company_name: Name of the recipient's company.
        company_summary: 2-3 sentence summary of the company.

    Returns:
        A dict with keys ``email_subject`` and ``email_body``.
    """
    logger.info(
        "Generating email for %s (%s) at %s", lead_name, job_title, company_name
    )

    prompt = (
        f"Recipient name: {lead_name}\n"
        f"Job title: {job_title}\n"
        f"Company: {company_name}\n"
        f"Company summary: {company_summary}\n\n"
        "Write the cold email now."
    )

    raw = chat_completion(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        max_tokens=300,
    )

    subject, body = _parse_email_response(raw)

    logger.debug("Generated subject for %s: %s", lead_name, subject)
    return {"email_subject": subject, "email_body": body}


def _parse_email_response(raw: str) -> tuple[str, str]:
    """
    Parse the LLM response into (subject, body).

    Expected format::

        Subject: <subject line>
        Body:
        <body text>
    """
    subject = ""
    body = ""

    subject_match = re.search(r"(?i)^subject:\s*(.+)", raw, re.MULTILINE)
    if subject_match:
        subject = subject_match.group(1).strip()

    body_match = re.search(r"(?i)^body:\s*\n([\s\S]+)", raw, re.MULTILINE)
    if body_match:
        body = body_match.group(1).strip()
    else:
        # Fallback: everything after the subject line
        body = re.sub(r"(?i)^subject:.+\n?", "", raw, count=1).strip()
        body = re.sub(r"(?i)^body:\s*\n?", "", body, count=1).strip()

    if not subject:
        logger.warning("Could not extract subject from LLM response.")
    if not body:
        logger.warning("Could not extract body from LLM response.")

    return subject, body
