"""web_scrape_tool — structured content extraction from URLs.

Hybrid fetch: urllib fast-path → Playwright fallback if content sparse.
Extraction: readability-lxml preferred, BeautifulSoup heuristic fallback.
Caching: URL-keyed via web_cache_store/web_cache_lookup with mode TTL.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

_MIN_CONTENT_CHARS = 200
_FETCH_TIMEOUT = 15
_MAX_CONTENT_CHARS = 32_000
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_TTL_MAP: dict[str, tuple[str, timedelta]] = {
    "article": ("medium", timedelta(hours=24)),
    "auto":    ("medium", timedelta(hours=24)),
    "listing": ("short",  timedelta(hours=2)),
    "product": ("short",  timedelta(hours=2)),
    "social":  ("short",  timedelta(minutes=30)),
}


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _url_cache_key(url: str) -> str:
    """SHA256 of the normalised URL string."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _scrape_ttl(mode: str) -> tuple[str, timedelta]:
    """Return (policy_name, timedelta) for a scrape mode."""
    return _TTL_MAP.get(mode, _TTL_MAP["article"])


def _cache_lookup(url: str) -> dict[str, Any] | None:
    """Return cached scrape result for URL, or None on miss/error."""
    try:
        from core.runtime.db import _ensure_web_cache_table, connect, web_cache_lookup
        key = _url_cache_key(url)
        with connect() as conn:
            _ensure_web_cache_table(conn)
            hit = web_cache_lookup(conn=conn, cache_key=key)
        if hit is None:
            return None
        body = hit.get("body") or "{}"
        return json.loads(body) if body.startswith("{") else None
    except Exception:
        return None


def _cache_store(*, url: str, mode: str, result: dict[str, Any]) -> None:
    """Store scrape result in web cache. Non-fatal on error."""
    try:
        from core.runtime.db import _ensure_web_cache_table, connect, web_cache_store
        key = _url_cache_key(url)
        policy, ttl = _scrape_ttl(mode)
        expires_at = (datetime.now(UTC) + ttl).isoformat()
        storable = {k: v for k, v in result.items() if k != "soup"}
        with connect() as conn:
            _ensure_web_cache_table(conn)
            web_cache_store(
                conn=conn,
                cache_key=key,
                query_raw=url,
                query_normalized=url.lower().strip(),
                source_url=url,
                title=result.get("title", ""),
                body=json.dumps(storable, ensure_ascii=False),
                ttl_policy=policy,
                expires_at=expires_at,
            )
    except Exception as exc:
        logger.debug("web_scrape: cache store failed: %s", exc)


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_urllib(url: str) -> tuple[str, str]:
    """Fetch URL via urllib. Returns (html, final_url). Raises on error."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        final_url = resp.url if hasattr(resp, "url") else url
    return html, final_url


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _extract_content(html: str, *, url: str) -> dict[str, Any]:
    """Extract title, content, metadata from HTML.

    Tries readability-lxml first, falls back to BeautifulSoup heuristic.
    Returns dict with title, content, metadata, soup, status.
    """
    title = ""
    content = ""
    metadata: dict[str, str] = {}

    # --- readability pass ---
    try:
        from readability import Document  # type: ignore
        doc = Document(html)
        title = doc.title() or ""
        content_html = doc.summary(html_partial=True)
        from bs4 import BeautifulSoup
        content = BeautifulSoup(content_html, "html.parser").get_text(" ", strip=True)
    except Exception:
        content = ""

    # --- BS4 pass (fallback or title fill-in) ---
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    if not title:
        title = (soup.title.string or "").strip() if soup.title else ""

    if len(content) < _MIN_CONTENT_CHARS:
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.find("body")
        content = (main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True))

    # --- metadata from <meta> tags ---
    def _meta(name: str, prop: str | None = None) -> str:
        tag = soup.find("meta", attrs={"name": name})
        if not tag and prop:
            tag = soup.find("meta", attrs={"property": prop})
        return (tag.get("content") or "").strip() if tag else ""  # type: ignore

    metadata["author"] = _meta("author") or _meta("", "article:author")
    metadata["date"] = (
        _meta("", "article:published_time")
        or _meta("date")
        or _meta("pubdate")
        or ""
    )
    if metadata["date"] and "T" in metadata["date"]:
        metadata["date"] = metadata["date"].split("T")[0]

    lang_tag = soup.find("html")
    metadata["language"] = (lang_tag.get("lang") or "").split("-")[0] if lang_tag else ""  # type: ignore

    metadata = {k: v for k, v in metadata.items() if v}

    if len(content) > _MAX_CONTENT_CHARS:
        content = content[:_MAX_CONTENT_CHARS - 1] + "…"

    return {
        "title": title,
        "content": content,
        "metadata": metadata,
        "soup": soup,
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Mode detection and handlers
# ---------------------------------------------------------------------------

def _detect_mode(soup: Any) -> str:
    """Heuristically detect the best scrape mode from page structure."""
    text = soup.get_text(" ", strip=True)
    if re.search(r"(kr\.?|€|\$|usd|dkk)\s*[\d,.]+", text, re.IGNORECASE):
        if soup.find(class_=re.compile(r"product|item|title", re.I)):
            return "product"
    li_count = len(soup.find_all("li"))
    article_count = len(soup.find_all("article"))
    if li_count >= 3 or article_count >= 3:
        return "listing"
    return "article"


def _apply_mode(soup: Any, *, mode: str, extract: str) -> list[dict[str, Any]]:
    """Extract structured items for listing/product modes. Returns [] for article/social."""
    if mode == "listing":
        items = []
        candidates = soup.find_all("li") or soup.find_all("article")
        for el in candidates[:30]:
            text = el.get_text(" ", strip=True)
            if not text or len(text) < 3:
                continue
            link = el.find("a")
            item: dict[str, Any] = {"text": text[:200]}
            if link and link.get("href"):
                item["href"] = str(link["href"])
            items.append(item)
        return items

    if mode == "product":
        title_el = (
            soup.find(class_=re.compile(r"product.?title|item.?title|product.?name", re.I))
            or soup.find("h1")
        )
        price_el = soup.find(class_=re.compile(r"price|pris", re.I))
        desc_el = soup.find(class_=re.compile(r"description|desc|summary", re.I))
        item: dict[str, Any] = {}
        if title_el:
            item["title"] = title_el.get_text(" ", strip=True)[:200]
        if price_el:
            item["price"] = price_el.get_text(" ", strip=True)[:50]
        if desc_el:
            item["description"] = desc_el.get_text(" ", strip=True)[:500]
        if not item.get("price"):
            m = re.search(
                r"(kr\.?\s*[\d,.]+|[\d,.]+\s*kr\.?|€\s*[\d,.]+|\$\s*[\d,.]+)",
                soup.get_text(), re.IGNORECASE,
            )
            if m:
                item["price"] = m.group(0).strip()
        return [item] if item else []

    return []


def _extract_links(soup: Any, *, base_url: str) -> list[dict[str, str]]:
    """Extract all non-empty links from page."""
    links = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        seen.add(full)
        text = a.get_text(" ", strip=True)[:100]
        links.append({"text": text, "href": full})
    return links


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def web_scrape(
    url: str,
    *,
    mode: str = "auto",
    extract: str = "",
    include_links: bool = False,
) -> dict[str, Any]:
    """Fetch a URL and return structured, cleaned content.

    Args:
        url: URL to scrape (https:// added if missing)
        mode: article|listing|product|social|auto
        extract: free-text hint about what to extract
        include_links: include extracted links in output

    Returns dict with: title, url, domain, content, metadata, items,
        links, mode_used, source, from_cache, chars, status.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    domain = urlparse(url).netloc or url

    # Cache hit
    cached = _cache_lookup(url)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    # --- urllib fast-path ---
    html = ""
    final_url = url
    source = "urllib"
    try:
        html, final_url = _fetch_urllib(url)
    except Exception as exc:
        logger.debug("web_scrape: urllib failed for %s: %s", url, exc)

    # --- Playwright fallback if content sparse ---
    extracted = _extract_content(html, url=final_url) if html else {"content": "", "soup": None}
    if len(extracted.get("content", "")) < _MIN_CONTENT_CHARS:
        try:
            from core.browser.playwright_session import run_in_playwright

            def _pw_fetch(page: Any) -> tuple[str, str]:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                return page.content(), page.url

            pw_html, pw_url = run_in_playwright(_pw_fetch)
            if pw_html:
                html = pw_html
                final_url = pw_url
                source = "playwright"
                extracted = _extract_content(html, url=final_url)
        except Exception as exc:
            logger.debug("web_scrape: playwright fallback failed: %s", exc)

    if not html:
        return {"status": "error", "error": "Could not fetch URL", "url": url, "domain": domain}

    soup = extracted.get("soup")

    mode_used = mode
    if mode == "auto" and soup is not None:
        mode_used = _detect_mode(soup)

    items = _apply_mode(soup, mode=mode_used, extract=extract) if soup else []
    links = _extract_links(soup, base_url=final_url) if (include_links and soup) else []

    content = extracted.get("content", "")
    result: dict[str, Any] = {
        "title": extracted.get("title", ""),
        "url": final_url,
        "domain": domain,
        "content": content,
        "metadata": extracted.get("metadata", {}),
        "items": items,
        "links": links,
        "mode_used": mode_used,
        "source": source,
        "from_cache": False,
        "chars": len(content),
        "status": "ok",
    }

    _cache_store(url=url, mode=mode_used, result=result)
    return result
