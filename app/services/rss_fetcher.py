"""RSS fetching and article body extraction.

Two concerns, intentionally separate:

- `fetch_feed` just pulls and parses the RSS — fast, produces `FeedItem`s with
  metadata only (title, url, maybe a short summary).
- `fetch_article_body` fetches the full article HTML and extracts the main
  text with trafilatura. Only called for items that pass initial dedup, so we
  don't hammer publishers for articles we'd throw away anyway.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx
import trafilatura
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

log = get_logger(__name__)

USER_AGENT = "SherrByteBot/1.0 (+https://sherrbyte.com/bot)"
FETCH_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
MAX_FEED_ITEMS = 50  # per feed per pull


@dataclass
class FeedItem:
    title: str
    url: str
    published_at: datetime
    summary: str | None
    author: str | None
    image_url: str | None


def _parse_date(entry: dict[str, Any]) -> datetime:
    """Prefer published_parsed → updated_parsed → now."""
    for field in ("published_parsed", "updated_parsed"):
        tp = entry.get(field)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except (TypeError, ValueError):
                continue
    return datetime.now(UTC)


def _pick_image(entry: dict[str, Any]) -> str | None:
    # media:content / media:thumbnail
    for key in ("media_content", "media_thumbnail"):
        if entry.get(key):
            url = entry[key][0].get("url")
            if url:
                return url
    # enclosures
    for enc in entry.get("enclosures", []) or []:
        if enc.get("type", "").startswith("image") and enc.get("href"):
            return enc["href"]
    # links with rel=enclosure
    for link in entry.get("links", []) or []:
        if link.get("rel") == "enclosure" and link.get("type", "").startswith("image"):
            return link.get("href")
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    reraise=True,
)
async def _http_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    resp = await client.get(url, follow_redirects=True)
    resp.raise_for_status()
    return resp


async def fetch_feed(
    client: httpx.AsyncClient, rss_url: str
) -> list[FeedItem]:
    """Pull and parse an RSS/Atom feed. Returns up to MAX_FEED_ITEMS items."""
    try:
        resp = await _http_get(client, rss_url)
    except httpx.HTTPError as e:
        log.warning("rss_fetch_failed", url=rss_url, error=str(e))
        raise

    parsed = feedparser.parse(resp.content)
    items: list[FeedItem] = []
    for entry in parsed.entries[:MAX_FEED_ITEMS]:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue
        items.append(
            FeedItem(
                title=title.strip(),
                url=url.strip(),
                published_at=_parse_date(entry),
                summary=(entry.get("summary") or "").strip() or None,
                author=(entry.get("author") or "").strip() or None,
                image_url=_pick_image(entry),
            )
        )
    return items


async def fetch_article_body(
    client: httpx.AsyncClient, url: str
) -> tuple[str | None, str | None]:
    """Fetch an article page and extract its main body text + best image.
    Returns (body_text, image_url). Either may be None."""
    try:
        resp = await _http_get(client, url)
    except httpx.HTTPError as e:
        log.info("article_fetch_failed", url=url, error=str(e))
        return None, None

    html = resp.text
    # Trafilatura is CPU-bound; run off the event loop
    body = await asyncio.to_thread(
        trafilatura.extract,
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        deduplicate=True,
    )

    # Try to grab og:image as a higher-quality fallback
    image = None
    og_match = _OG_IMAGE_RE.search(html) if html else None
    if og_match:
        image = og_match.group(1).strip()

    return body, image


import re

_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def build_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en,hi;q=0.9"},
        timeout=FETCH_TIMEOUT,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
