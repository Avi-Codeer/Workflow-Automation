"""
Company Research Agent.
Uses an LLM to generate a short company summary including industry,
main activity, and potential growth signals.
"""

from __future__ import annotations

import json
import logging
import re

from ai_sdr_agent.services.openai_service import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a business analyst. When given a company name, respond ONLY with "
    "a JSON object in the following format (no markdown, no extra text):\n"
    '{"industry": "<industry>", "summary": "<2-3 sentence summary>"}\n\n'
    "The summary must mention the industry, main business activities, and at "
    "least one potential growth signal."
)


def research_company(company_name: str) -> dict[str, str]:
    """
    Generate a research summary for *company_name*.

    Args:
        company_name: Name of the company to research.

    Returns:
        A dict with keys ``industry`` and ``summary``.
        Falls back to empty strings on parse errors.
    """
    logger.info("Researching company: %s", company_name)

    prompt = f"Company: {company_name}"
    raw_response = chat_completion(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        max_tokens=256,
    )

    # Strip potential markdown code fences (```json ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        result = {
            "industry": str(data.get("industry", "")).strip(),
            "summary": str(data.get("summary", "")).strip(),
        }
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "Could not parse research JSON for '%s'. Raw: %s",
            company_name,
            raw_response,
        )
        result = {"industry": "", "summary": raw_response}

    logger.debug("Research result for '%s': %s", company_name, result)
    return result
