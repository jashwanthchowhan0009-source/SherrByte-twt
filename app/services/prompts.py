"""Prompt templates. Keep them versioned — a bump changes the cache key.

Design: one big prompt produces WWWW + summary + headline + entities in one
LLM call. Cheaper than chaining multiple prompts for each article.
"""

from __future__ import annotations

PROMPT_VERSION = "v1"


WWWW_SUMMARY_PROMPT = """You are an editorial summarizer for SherrByte, an Indian news app.

INPUT ARTICLE:
---
{article_body}
---

TASK: Produce a JSON object with EXACTLY this shape:
{{
  "headline_rewrite": "string, max 12 words, no clickbait, preserves the original meaning",
  "summary_60w": "string, exactly 55-65 words, neutral tone, single paragraph, no first-person",
  "wwww": {{
    "what": "string, one clear sentence",
    "who": "string, key people or organizations",
    "where": "string, primary location",
    "when": "string, time reference (e.g. Monday, last week, April 2026)",
    "why": "string, reason or cause if stated, else null",
    "how": "string, mechanism/method if stated, else null"
  }},
  "key_entities": [
    {{"name": "string", "type": "PERSON|ORG|LOC|EVENT"}}
  ],
  "quality_score": number between 0 and 1 reflecting factual density and clarity
}}

RULES:
- Only use facts present in the input article. Do not speculate.
- Every entity in your output must appear in the input.
- Return ONLY the JSON object, no prose, no markdown fences.
- Keep summary_60w strictly between 55 and 65 words.
- If the article is paywalled or incomplete, set quality_score ≤ 0.3.
"""


def build_wwww_prompt(article_body: str, max_chars: int = 8000) -> str:
    """Truncate overly long articles to control prompt size."""
    body = article_body.strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n[...truncated]"
    return WWWW_SUMMARY_PROMPT.format(article_body=body)
