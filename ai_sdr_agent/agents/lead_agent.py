"""
Lead Finder Agent.
Uses Apollo to discover decision makers at a target company.
"""

from __future__ import annotations

import logging

from ai_sdr_agent.services.apollo_service import search_decision_makers

logger = logging.getLogger(__name__)


def find_decision_makers(company_name: str) -> list[dict[str, str]]:
    """
    Return a list of decision makers for *company_name*.

    Each item in the list is a dict with keys:
    ``name``, ``title``, ``email``, ``linkedin``

    Args:
        company_name: The name of the target company.

    Returns:
        A list of decision-maker dicts (may be empty if none are found).
    """
    logger.info("Finding decision makers for: %s", company_name)
    leads = search_decision_makers(company_name)
    logger.info(
        "Lead agent found %d lead(s) for '%s'", len(leads), company_name
    )
    return leads
