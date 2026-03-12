"""
Apollo.io service wrapper.
Provides helpers to search for people (decision makers) at a given company.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ai_sdr_agent.config.settings import (
    APOLLO_API_KEY,
    APOLLO_BASE_URL,
    DECISION_MAKER_TITLES,
)

logger = logging.getLogger(__name__)

_PEOPLE_SEARCH_ENDPOINT = f"{APOLLO_BASE_URL}/mixed_people/search"


def _build_headers() -> dict[str, str]:
    if not APOLLO_API_KEY:
        raise ValueError(
            "APOLLO_API_KEY is not set. Please add it to your .env file."
        )
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }


def search_decision_makers(
    company_name: str,
    page: int = 1,
    per_page: int = 10,
) -> list[dict[str, str]]:
    """
    Query Apollo for decision makers at *company_name*.

    Args:
        company_name: Name of the target company.
        page: Pagination page number (1-based).
        per_page: Number of results per page.

    Returns:
        A list of dicts, each containing:
        ``{name, title, email, linkedin}``

    Raises:
        ValueError: When the API key is missing.
        requests.HTTPError: On non-2xx responses.
    """
    headers = _build_headers()

    payload: dict[str, Any] = {
        "q_organization_name": company_name,
        "person_titles": DECISION_MAKER_TITLES,
        "page": page,
        "per_page": per_page,
    }

    try:
        response = requests.post(
            _PEOPLE_SEARCH_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.error(
            "Apollo API error for company '%s': %s – %s",
            company_name,
            exc,
            exc.response.text if exc.response is not None else "",
        )
        raise

    data = response.json()
    people: list[dict[str, Any]] = data.get("people", [])

    results: list[dict[str, str]] = []
    for person in people:
        email = (person.get("email") or "").strip()
        if not email:
            # Skip contacts without a verified e-mail address
            continue
        results.append(
            {
                "name": (person.get("name") or "").strip(),
                "title": (person.get("title") or "").strip(),
                "email": email,
                "linkedin": (person.get("linkedin_url") or "").strip(),
            }
        )

    logger.info(
        "Found %d decision maker(s) for '%s'", len(results), company_name
    )
    return results
