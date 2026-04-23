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


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Mode handler tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main web_scrape() tests
# ---------------------------------------------------------------------------

def test_web_scrape_returns_structured_output(monkeypatch):
    from core.tools.web_scrape_tool import web_scrape
    import urllib.request as ur

    class FakeResp:
        url = "https://example.com/art"
        def read(self): return ARTICLE_HTML.encode()
        def __enter__(self): return self
        def __exit__(self, *_): pass

    monkeypatch.setattr(ur, "urlopen", lambda *a, **kw: FakeResp())
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
