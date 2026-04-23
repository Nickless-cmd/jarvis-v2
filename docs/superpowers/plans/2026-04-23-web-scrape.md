# web_scrape Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `web_scrape` tool that fetches a URL, extracts structured content (title, body, metadata, items, links) using readability + BeautifulSoup, and caches the result with mode-appropriate TTL.

**Architecture:** Hybrid urllib fast-path (< 200 char threshold triggers Playwright fallback). Extraction via `readability-lxml` with BS4 heuristic fallback. Mode-handlers for article/listing/product/social/auto. URL-keyed cache via existing `web_cache_store`/`web_cache_lookup`.

**Tech Stack:** Python 3.11+, `readability-lxml` (installed), `beautifulsoup4` (installed), `playwright` (existing session via `run_in_playwright`), `urllib` (stdlib)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `core/tools/web_scrape_tool.py` | All scraper logic: fetch, extract, mode-handlers, cache |
| Modify | `core/tools/simple_tools.py` | Tool definition, `_exec_web_scrape`, dispatch entry |
| Create | `tests/test_web_scrape.py` | Unit tests for extraction, mode detection, caching |

---

### Task 1: Scaffold `web_scrape_tool.py` with URL cache helpers

**Files:**
- Create: `core/tools/web_scrape_tool.py`
- Create: `tests/test_web_scrape.py`

- [ ] **Step 1: Write the failing tests for cache key and TTL helpers**

```python
# tests/test_web_scrape.py
from __future__ import annotations
from datetime import timedelta
import pytest


def test_url_cache_key_is_stable():
    from core.tools.web_scrape_tool import _url_cache_key
    k1 = _url_cache_key("https://example.com/page?q=1")
    k2 = _url_cache_key("https://example.com/page?q=1")
    assert k1 == k2
    assert len(k1) == 64  # SHA256 hex


def test_url_cache_key_differs_for_different_urls():
    from core.tools.web_scrape_tool import _url_cache_key
    assert _url_cache_key("https://a.com") != _url_cache_key("https://b.com")


def test_scrape_ttl_article():
    from core.tools.web_scrape_tool import _scrape_ttl
    policy, td = _scrape_ttl("article")
    assert policy == "medium"
    assert td == timedelta(hours=24)


def test_scrape_ttl_listing():
    from core.tools.web_scrape_tool import _scrape_ttl
    policy, td = _scrape_ttl("listing")
    assert policy == "short"
    assert td == timedelta(hours=2)


def test_scrape_ttl_product():
    from core.tools.web_scrape_tool import _scrape_ttl
    policy, td = _scrape_ttl("product")
    assert policy == "short"
    assert td == timedelta(hours=2)


def test_scrape_ttl_social():
    from core.tools.web_scrape_tool import _scrape_ttl
    policy, td = _scrape_ttl("social")
    assert policy == "short"
    assert td == timedelta(minutes=30)


def test_scrape_ttl_auto_defaults_to_article():
    from core.tools.web_scrape_tool import _scrape_ttl
    policy, td = _scrape_ttl("auto")
    assert td == timedelta(hours=24)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: No module named 'core.tools.web_scrape_tool'`

- [ ] **Step 3: Create `core/tools/web_scrape_tool.py` with cache helpers**

```python
"""web_scrape_tool — structured content extraction from URLs.

Hybrid fetch: urllib fast-path → Playwright fallback if content sparse.
Extraction: readability-lxml preferred, BeautifulSoup heuristic fallback.
Caching: URL-keyed via web_cache_store/web_cache_lookup with mode TTL.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
import urllib.error
import urllib.request

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


def _url_cache_key(url: str) -> str:
    """SHA256 of the normalised URL string."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _scrape_ttl(mode: str) -> tuple[str, timedelta]:
    """Return (policy_name, timedelta) for a scrape mode."""
    return _TTL_MAP.get(mode, _TTL_MAP["article"])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | head -30
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/tools/web_scrape_tool.py tests/test_web_scrape.py
git commit -m "feat(web_scrape): scaffold cache key and TTL helpers"
```

---

### Task 2: urllib + readability/BS4 extraction

**Files:**
- Modify: `core/tools/web_scrape_tool.py`
- Modify: `tests/test_web_scrape.py`

- [ ] **Step 1: Write failing tests for fetch and extraction**

Add to `tests/test_web_scrape.py`:

```python
ARTICLE_HTML = """<!DOCTYPE html>
<html lang="da">
<head><title>Test Artikel</title>
<meta name="author" content="Bjørn">
<meta property="article:published_time" content="2026-04-23T10:00:00Z">
</head>
<body>
<nav>Navigation garbage</nav>
<article>
<h1>Test Artikel</h1>
<p>Dette er en lang artikel med meget indhold der skal udtrækkes korrekt af readability.</p>
<p>Endnu et afsnit med mere indhold så readability ikke ignorerer artiklen.</p>
<p>Tredje afsnit med yderligere substans for at nå minimumsgrænsen.</p>
</article>
<footer>Footer garbage</footer>
</body></html>"""

SPARSE_HTML = "<html><body><div>ok</div></body></html>"


def test_extract_article_returns_title_and_content():
    from core.tools.web_scrape_tool import _extract_content
    result = _extract_content(ARTICLE_HTML, url="https://example.com/art")
    assert result["title"] == "Test Artikel"
    assert "artikel" in result["content"].lower()
    assert len(result["content"]) > 50


def test_extract_article_metadata():
    from core.tools.web_scrape_tool import _extract_content
    result = _extract_content(ARTICLE_HTML, url="https://example.com/art")
    assert result["metadata"].get("author") == "Bjørn"
    assert "2026-04-23" in (result["metadata"].get("date") or "")


def test_extract_sparse_html_returns_something():
    from core.tools.web_scrape_tool import _extract_content
    result = _extract_content(SPARSE_HTML, url="https://example.com/")
    assert result["status"] == "ok"
    assert isinstance(result["content"], str)


def test_fetch_urllib_returns_html(monkeypatch):
    from core.tools.web_scrape_tool import _fetch_urllib
    import urllib.request as ur

    class FakeResp:
        def read(self): return b"<html><body><p>hello</p></body></html>"
        def __enter__(self): return self
        def __exit__(self, *_): pass

    monkeypatch.setattr(ur, "urlopen", lambda *a, **kw: FakeResp())
    html, final_url = _fetch_urllib("https://example.com")
    assert "hello" in html
    assert final_url == "https://example.com"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v -k "extract or fetch_urllib" 2>&1 | head -30
```
Expected: 4 tests FAIL with `ImportError`

- [ ] **Step 3: Implement `_fetch_urllib` and `_extract_content`**

Add to `core/tools/web_scrape_tool.py`:

```python
def _fetch_urllib(url: str) -> tuple[str, str]:
    """Fetch URL via urllib. Returns (html, final_url). Raises on error."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        final_url = resp.url if hasattr(resp, "url") else url
    return html, final_url


def _extract_content(html: str, *, url: str) -> dict[str, Any]:
    """Extract title, content, metadata from HTML.

    Tries readability-lxml first, falls back to BeautifulSoup heuristic.
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
        # Strip tags from readability output
        from bs4 import BeautifulSoup
        content = BeautifulSoup(content_html, "html.parser").get_text(" ", strip=True)
    except Exception:
        content = ""

    # --- BS4 fallback if readability gave nothing useful ---
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    if not title:
        title = (soup.title.string or "").strip() if soup.title else ""

    if len(content) < _MIN_CONTENT_CHARS:
        # Remove boilerplate tags
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        # Prefer <article> or <main>, fall back to <body>
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
    # Trim date to ISO date part
    if metadata["date"] and "T" in metadata["date"]:
        metadata["date"] = metadata["date"].split("T")[0]

    lang_tag = soup.find("html")
    metadata["language"] = (lang_tag.get("lang") or "").split("-")[0] if lang_tag else ""  # type: ignore

    # Strip empty metadata values
    metadata = {k: v for k, v in metadata.items() if v}

    if len(content) > _MAX_CONTENT_CHARS:
        content = content[:_MAX_CONTENT_CHARS - 1] + "…"

    return {
        "title": title,
        "content": content,
        "metadata": metadata,
        "soup": soup,  # passed through for mode-handlers, not in final output
        "status": "ok",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | head -40
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/tools/web_scrape_tool.py tests/test_web_scrape.py
git commit -m "feat(web_scrape): urllib fetch and readability/BS4 extraction"
```

---

### Task 3: Mode-handlers (auto, listing, product, links)

**Files:**
- Modify: `core/tools/web_scrape_tool.py`
- Modify: `tests/test_web_scrape.py`

- [ ] **Step 1: Write failing tests for mode-handlers**

Add to `tests/test_web_scrape.py`:

```python
LISTING_HTML = """<html><body>
<ul>
  <li><a href="/a">Item Alpha</a> - kr. 99</li>
  <li><a href="/b">Item Beta</a> - kr. 149</li>
  <li><a href="/c">Item Gamma</a> - kr. 199</li>
</ul>
</body></html>"""

PRODUCT_HTML = """<html><body>
<h1 class="product-title">Super Widget 3000</h1>
<span class="price">kr. 599</span>
<p class="description">The best widget on the market.</p>
</body></html>"""

LINKS_HTML = """<html><body>
<a href="https://external.com/page">External link</a>
<a href="/internal/page">Internal link</a>
<a href="">Empty href</a>
</body></html>"""


def test_mode_listing_extracts_items():
    from core.tools.web_scrape_tool import _apply_mode
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    items = _apply_mode(soup, mode="listing", extract="")
    assert len(items) >= 2
    assert all(isinstance(i, dict) for i in items)
    assert any("Alpha" in str(i.values()) for i in items)


def test_mode_product_extracts_title_and_price():
    from core.tools.web_scrape_tool import _apply_mode
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(PRODUCT_HTML, "html.parser")
    items = _apply_mode(soup, mode="product", extract="")
    assert len(items) == 1
    first = items[0]
    assert "Super Widget 3000" in str(first.values())
    assert "599" in str(first.values())


def test_mode_auto_detects_listing():
    from core.tools.web_scrape_tool import _detect_mode
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(LISTING_HTML, "html.parser")
    assert _detect_mode(soup) == "listing"


def test_mode_auto_detects_article():
    from core.tools.web_scrape_tool import _detect_mode
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(ARTICLE_HTML, "html.parser")
    assert _detect_mode(soup) == "article"


def test_extract_links():
    from core.tools.web_scrape_tool import _extract_links
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(LINKS_HTML, "html.parser")
    links = _extract_links(soup, base_url="https://example.com")
    hrefs = [l["href"] for l in links]
    assert "https://external.com/page" in hrefs
    assert any("internal" in h for h in hrefs)
    assert all(l["href"] for l in links)  # no empty hrefs
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v -k "mode or links" 2>&1 | head -30
```
Expected: 5 tests FAIL with `ImportError`

- [ ] **Step 3: Implement mode-handlers**

Add to `core/tools/web_scrape_tool.py`:

```python
def _detect_mode(soup: Any) -> str:
    """Heuristically detect the best scrape mode from page structure."""
    from bs4 import BeautifulSoup
    # Price pattern → product
    import re
    text = soup.get_text(" ", strip=True)
    if re.search(r"(kr\.?|€|\$|usd|dkk)\s*[\d,.]+", text, re.IGNORECASE):
        # Only if there's a clear product heading too
        if soup.find(class_=re.compile(r"product|item|title", re.I)):
            return "product"
    # Many <li> or <article> children → listing
    li_count = len(soup.find_all("li"))
    article_count = len(soup.find_all("article"))
    if li_count >= 4 or article_count >= 3:
        return "listing"
    return "article"


def _apply_mode(soup: Any, *, mode: str, extract: str) -> list[dict[str, Any]]:
    """Extract structured items for listing/product modes. Returns [] for article/social."""
    import re
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
        # Try to find title, price, description
        import re
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
        # Fallback: find price pattern in text
        if not item.get("price"):
            m = re.search(r"(kr\.?\s*[\d,.]+|[\d,.]+\s*kr\.?|€\s*[\d,.]+|\$\s*[\d,.]+)", soup.get_text(), re.IGNORECASE)
            if m:
                item["price"] = m.group(0).strip()
        return [item] if item else []

    return []  # article and social: no structured items


def _extract_links(soup: Any, *, base_url: str) -> list[dict[str, str]]:
    """Extract all non-empty links from page."""
    from urllib.parse import urljoin
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | head -40
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/tools/web_scrape_tool.py tests/test_web_scrape.py
git commit -m "feat(web_scrape): mode-handlers for listing, product, auto, links"
```

---

### Task 4: Main `web_scrape()` function with cache + Playwright fallback

**Files:**
- Modify: `core/tools/web_scrape_tool.py`
- Modify: `tests/test_web_scrape.py`

- [ ] **Step 1: Write failing tests for main function**

Add to `tests/test_web_scrape.py`:

```python
def test_web_scrape_returns_structured_output(monkeypatch):
    from core.tools.web_scrape_tool import web_scrape
    import urllib.request as ur

    class FakeResp:
        url = "https://example.com/art"
        def read(self): return ARTICLE_HTML.encode()
        def __enter__(self): return self
        def __exit__(self, *_): pass

    monkeypatch.setattr(ur, "urlopen", lambda *a, **kw: FakeResp())
    # Patch cache to always miss
    import core.tools.web_scrape_tool as m
    monkeypatch.setattr(m, "_cache_lookup", lambda url: None)
    monkeypatch.setattr(m, "_cache_store", lambda **kw: None)

    result = web_scrape("https://example.com/art", mode="article")
    assert result["status"] == "ok"
    assert result["title"] == "Test Artikel"
    assert "artikel" in result["content"].lower()
    assert result["domain"] == "example.com"
    assert result["from_cache"] is False
    assert result["source"] == "urllib"
    assert result["mode_used"] == "article"
    assert isinstance(result["items"], list)
    assert isinstance(result["links"], list)
    assert isinstance(result["metadata"], dict)


def test_web_scrape_returns_cache_hit(monkeypatch):
    from core.tools.web_scrape_tool import web_scrape
    import core.tools.web_scrape_tool as m

    cached = {
        "title": "Cached Title", "url": "https://example.com/", "domain": "example.com",
        "content": "cached content here", "metadata": {}, "items": [], "links": [],
        "mode_used": "article", "source": "urllib", "chars": 19, "status": "ok",
    }
    monkeypatch.setattr(m, "_cache_lookup", lambda url: cached)

    result = web_scrape("https://example.com/", mode="article")
    assert result["from_cache"] is True
    assert result["title"] == "Cached Title"


def test_web_scrape_url_without_scheme(monkeypatch):
    from core.tools.web_scrape_tool import web_scrape
    import urllib.request as ur
    import core.tools.web_scrape_tool as m

    monkeypatch.setattr(m, "_cache_lookup", lambda url: None)
    monkeypatch.setattr(m, "_cache_store", lambda **kw: None)

    class FakeResp:
        url = "https://example.com/"
        def read(self): return ARTICLE_HTML.encode()
        def __enter__(self): return self
        def __exit__(self, *_): pass

    monkeypatch.setattr(ur, "urlopen", lambda *a, **kw: FakeResp())
    result = web_scrape("example.com", mode="article")
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v -k "web_scrape" 2>&1 | head -30
```
Expected: 3 tests FAIL with `ImportError`

- [ ] **Step 3: Implement cache helpers and `web_scrape()`**

Add to `core/tools/web_scrape_tool.py`:

```python
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

    from urllib.parse import urlparse
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
    extracted = _extract_content(html, url=final_url) if html else {"content": ""}
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

    # Detect mode if auto
    mode_used = mode
    if mode == "auto" and soup is not None:
        mode_used = _detect_mode(soup)

    # Mode-handler
    items = _apply_mode(soup, mode=mode_used, extract=extract) if soup else []

    # Links
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
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | tail -20
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/tools/web_scrape_tool.py tests/test_web_scrape.py
git commit -m "feat(web_scrape): main web_scrape() with cache and Playwright fallback"
```

---

### Task 5: Register tool in `simple_tools.py`

**Files:**
- Modify: `core/tools/simple_tools.py`

- [ ] **Step 1: Add tool definition after `web_fetch` definition**

In `simple_tools.py`, find the `web_fetch` tool definition block (around line 308) and add immediately after it:

```python
    {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": (
                "Fetch a URL and return structured, cleaned content: title, body text, "
                "metadata (author, date, language), and optionally links or item lists. "
                "Smarter than web_fetch — handles JS-rendered pages via Playwright fallback, "
                "removes nav/ads/footers, detects content type automatically. "
                "Use for articles, product pages, listings, or any structured web content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape (https:// added if missing)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "article", "listing", "product", "social"],
                        "description": "Extraction mode. 'auto' detects from page structure.",
                    },
                    "extract": {
                        "type": "string",
                        "description": "Optional free-text hint: what to extract (e.g. 'prices', 'contact info')",
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Include extracted links in output (default false)",
                    },
                },
                "required": ["url"],
            },
        },
    },
```

- [ ] **Step 2: Add `_exec_web_scrape` function after `_exec_web_fetch`**

Find `_exec_web_fetch` (around line 2246) and add after it:

```python
def _exec_web_scrape(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.web_scrape_tool import web_scrape
    url = str(args.get("url") or "").strip()
    if not url:
        return {"error": "url is required", "status": "error"}
    mode = str(args.get("mode") or "auto").strip()
    extract = str(args.get("extract") or "").strip()
    include_links = bool(args.get("include_links", False))
    return web_scrape(url, mode=mode, extract=extract, include_links=include_links)
```

- [ ] **Step 3: Add dispatch entry**

In the `_TOOL_DISPATCH` dict (around line 4680), add after `"web_fetch": _exec_web_fetch,`:

```python
    "web_scrape": _exec_web_scrape,
```

- [ ] **Step 4: Also add Danish label in `_TOOL_LABELS` in `visible_runs.py`**

In `core/services/visible_runs.py`, find `_TOOL_LABELS` and add:

```python
    "web_scrape": "Skraber webside",
```

- [ ] **Step 5: Verify syntax**

```bash
conda activate ai && python -m compileall core/tools/simple_tools.py core/tools/web_scrape_tool.py core/services/visible_runs.py -q
```
Expected: no output (clean)

- [ ] **Step 6: Run full test suite**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v 2>&1 | tail -10
```
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add core/tools/simple_tools.py core/tools/web_scrape_tool.py core/services/visible_runs.py
git commit -m "feat(web_scrape): register tool in simple_tools dispatch + Danish label"
```

---

### Task 6: Smoke test end-to-end

**Files:** none (verification only)

- [ ] **Step 1: Syntax check all changed files**

```bash
conda activate ai && python -m compileall core/tools/web_scrape_tool.py core/tools/simple_tools.py -q
```

- [ ] **Step 2: Import smoke test**

```bash
conda activate ai && python -c "
from core.tools.web_scrape_tool import web_scrape, _url_cache_key, _scrape_ttl, _detect_mode, _apply_mode, _extract_links, _extract_content
print('imports ok')
from core.tools.simple_tools import TOOL_DEFINITIONS
names = [t['function']['name'] for t in TOOL_DEFINITIONS]
assert 'web_scrape' in names, f'web_scrape missing from TOOL_DEFINITIONS, got: {names}'
print('tool registered ok')
"
```
Expected: `imports ok` and `tool registered ok`

- [ ] **Step 3: Full test run**

```bash
conda activate ai && pytest tests/test_web_scrape.py -v
```
Expected: all tests PASS, 0 failures

- [ ] **Step 4: Final commit**

```bash
git add -p  # review any stragglers
git commit -m "feat(web_scrape): complete tool — urllib+readability+BS4+Playwright fallback" --allow-empty
```
