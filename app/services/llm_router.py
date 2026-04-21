"""LLM router — single entry point for every LLM call the pipeline makes.

Strategy:
  1. Try Gemini 2.5 Flash-Lite (1000 RPD free, cheapest).
  2. On 429 or 5xx → fall through to Groq Llama 3.3 70B (fast, generous free cap).
  3. On Groq failure → raise.

All providers return a dict conforming to the caller's JSON schema. The router
handles prompt templating, retry on transient errors, and token accounting logs.

If both `GEMINI_API_KEY` and `GROQ_API_KEY` are empty (dev mode), every call
raises `LLMUnavailableError` — callers should gracefully skip AI enrichment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger

log = get_logger(__name__)


class LLMUnavailableError(AppError):
    code = "llm_unavailable"
    status_code = 503
    message = "No LLM provider is configured or all providers failed."


@dataclass
class LLMResponse:
    """Structured result from any provider."""

    provider: str
    model: str
    data: dict[str, Any]
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


# ---------------- Gemini ----------------


_GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    reraise=True,
)
async def _call_gemini(
    client: httpx.AsyncClient, prompt: str, api_key: str, model: str
) -> dict[str, Any]:
    url = _GEMINI_ENDPOINT.format(model=model)
    body = {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }
    resp = await client.post(url, params={"key": api_key}, json=body, timeout=45.0)
    if resp.status_code == 429:
        raise _Retriable(f"gemini rate limited: {resp.text[:200]}")
    if resp.status_code >= 500:
        raise _Retriable(f"gemini 5xx: {resp.status_code}")
    resp.raise_for_status()

    payload = resp.json()
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise _Unretriable(f"gemini malformed response: {payload}") from e
    return json.loads(text)


# ---------------- Groq ----------------


_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    reraise=True,
)
async def _call_groq(
    client: httpx.AsyncClient, prompt: str, api_key: str, model: str
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await client.post(_GROQ_ENDPOINT, json=body, headers=headers, timeout=45.0)
    if resp.status_code == 429:
        raise _Retriable(f"groq rate limited: {resp.text[:200]}")
    if resp.status_code >= 500:
        raise _Retriable(f"groq 5xx: {resp.status_code}")
    resp.raise_for_status()

    payload = resp.json()
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise _Unretriable(f"groq malformed response: {payload}") from e
    return json.loads(text)


# ---------------- Internal exceptions (don't leak to callers) ----------------


class _Retriable(Exception):
    """Signal to the router: try the next provider."""


class _Unretriable(Exception):
    """Signal to the router: don't bother trying others (e.g. bad prompt)."""


# ---------------- Public entry point ----------------


async def complete_json(prompt: str) -> LLMResponse:
    """Run a prompt through the router. Returns structured JSON or raises."""
    has_gemini = bool(settings.gemini_api_key)
    has_groq = bool(settings.groq_api_key)

    if not has_gemini and not has_groq:
        raise LLMUnavailableError(
            "No LLM provider configured. Set GEMINI_API_KEY or GROQ_API_KEY."
        )

    async with httpx.AsyncClient() as client:
        # Attempt Gemini
        if has_gemini:
            try:
                data = await _call_gemini(
                    client, prompt, settings.gemini_api_key, settings.gemini_model
                )
                return LLMResponse(
                    provider="gemini", model=settings.gemini_model, data=data
                )
            except _Retriable as e:
                log.info("llm_fallback", reason=str(e))
            except httpx.HTTPStatusError as e:
                # 4xx other than 429 — likely a content-policy or auth issue; still try Groq
                log.warning("llm_gemini_4xx", status=e.response.status_code)
            except (_Unretriable, json.JSONDecodeError, KeyError) as e:
                log.warning("llm_gemini_bad_output", error=str(e))

        # Attempt Groq
        if has_groq:
            try:
                data = await _call_groq(
                    client, prompt, settings.groq_api_key, settings.groq_model
                )
                return LLMResponse(
                    provider="groq", model=settings.groq_model, data=data
                )
            except (_Retriable, _Unretriable, httpx.HTTPError, json.JSONDecodeError) as e:
                log.warning("llm_groq_failed", error=str(e))

    raise LLMUnavailableError("All LLM providers failed or are unconfigured.")
