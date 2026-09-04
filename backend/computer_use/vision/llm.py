"""Small adapter between computer-use code and Sara's auxiliary LLM router."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


def _extract_response_text(response: Any) -> str:
    """Return assistant text from Sara auxiliary responses."""
    if not response:
        return ""
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        return str(response.get("content") or response.get("analysis") or "").strip()
    try:
        from agent.auxiliary_client import extract_content_or_reasoning

        return extract_content_or_reasoning(response).strip()
    except Exception as e:
        logger.debug("Primary LLM parser failed: %s", e)
    try:
        return str(response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def call_text_llm(
    prompt: str,
    *,
    config: Optional[ComputerUseConfig] = None,
    max_tokens: int = 1000,
) -> str:
    """Call the configured auxiliary model with a text-only prompt."""
    try:
        from agent.auxiliary_client import call_llm

        response = call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return _extract_response_text(response)
    except Exception as exc:
        logger.debug("Computer-use text LLM call failed: %s", exc)
        return ""


def call_vision_llm(
    prompt: str,
    screenshot_b64: str,
    *,
    config: ComputerUseConfig,
    max_tokens: int = 1500,
) -> str:
    """Analyze a screenshot with the configured auxiliary vision route."""
    if not screenshot_b64:
        return ""

    data_url = screenshot_b64
    if not data_url.startswith("data:image/"):
        data_url = f"data:image/png;base64,{screenshot_b64}"

    provider = config.vision_provider if config.vision_provider != "auto" else None
    model = config.vision_model or None

    try:
        from agent.auxiliary_client import call_llm

        response = call_llm(
            task="vision",
            provider=provider,
            model=model,
            base_url=config.vision_base_url or None,
            api_key=config.vision_api_key or None,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        return _extract_response_text(response)
    except Exception as exc:
        logger.debug("Computer-use vision LLM call failed: %s", exc)
        return ""
