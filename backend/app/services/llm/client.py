"""OpenRouter client, used ONLY where judgement is genuinely required.

Deliberate constraints:
  * every call must return strict JSON, parsed and validated here
  * a failure (no key, timeout, bad JSON) returns None -> the caller degrades to
    REVIEW, never to PASS. An unreachable model must not be able to ship a sale.
"""
import json
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    pass


def complete_json(system: str, user: str, *, max_tokens: int = 700) -> dict | None:
    if not settings.llm_available:
        log.warning("LLM disabled or missing OPENROUTER_API_KEY; degrading to REVIEW.")
        return None

    payload = {
        "model": settings.openrouter_model,
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "X-Title": "CIMET QA Gate",
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            resp = client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                json=payload, headers=headers,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - any failure degrades the same way
        log.warning("OpenRouter call failed: %s", exc)
        return None

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        log.warning("OpenRouter returned non-JSON content.")
        return None
    return parsed if isinstance(parsed, dict) else None
