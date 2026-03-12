"""
OpenAI service wrapper.
Provides a single helper to call the chat-completion endpoint so all agents
share the same retry / error-handling logic.
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI, OpenAIError

from ai_sdr_agent.config.settings import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
)

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. Please add it to your .env file."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def chat_completion(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 512,
) -> str:
    """
    Send a chat completion request to OpenAI and return the response text.

    Args:
        prompt: The user message / instruction.
        system_prompt: The system-level instruction for the assistant.
        model: Override the default model.
        temperature: Override the default temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant's reply as a plain string.

    Raises:
        OpenAIError: On API-level errors.
        ValueError: When the API key is missing.
    """
    client = _get_client()
    resolved_model = model or OPENAI_MODEL
    resolved_temp = temperature if temperature is not None else OPENAI_TEMPERATURE

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=resolved_temp,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        return content.strip()
    except OpenAIError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise
