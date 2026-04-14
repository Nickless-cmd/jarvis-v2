# Browser Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis eight browser-control tools (navigate, read, click, type, submit, screenshot, find_tabs, switch_tab) via Playwright, connecting to the user's existing Chrome via CDP with a standalone-browser fallback.

**Architecture:** `core/browser/playwright_session.py` holds a module-level singleton Playwright session. `core/tools/browser_tools.py` defines all eight tool schemas and sync handlers that call the session. Tools are registered in `simple_tools.py`. `runtime_browser_body.py` gets a `set_browser_status()` helper so Mission Control reflects browser state in real time.

**Tech Stack:** Python 3.11, `playwright` (sync API), SQLite via existing `runtime_browser_body.py`, FastAPI lifespan hook.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `core/browser/__init__.py` | Create | Package marker |
| `core/browser/playwright_session.py` | Create | Session singleton — CDP connect + standalone fallback, page switching |
| `core/tools/browser_tools.py` | Create | 8 tool definitions + sync handlers |
| `core/tools/simple_tools.py` | Modify | Import + register browser tool definitions and handlers |
| `apps/api/jarvis_api/services/runtime_browser_body.py` | Modify | Add `set_browser_status()` convenience helper |
| `apps/api/jarvis_api/app.py` | Modify | Call `stop_browser_session()` in lifespan shutdown |
| `tests/test_browser_tools.py` | Create | Tests for all handlers and session behaviour |

---

### Task 1: Install Playwright

**Files:**
- No code changes — environment setup

- [ ] **Step 1: Install Playwright into conda env**

```bash
conda run -n ai pip install playwright==1.44.0
conda run -n ai playwright install chromium
```

Expected: `Successfully installed playwright-1.44.0` and Chromium browser binary downloaded.

- [ ] **Step 2: Verify import works**

```bash
conda run -n ai python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit requirements note**

```bash
# No pyproject.toml change needed — conda env is the dependency manager.
# Just verify it's there.
conda run -n ai pip show playwright | grep Version
```

Expected: `Version: 1.44.0`

---

### Task 2: Playwright Session Singleton

**Files:**
- Create: `core/browser/__init__.py`
- Create: `core/browser/playwright_session.py`
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_browser_tools.py
"""Tests for browser tool handlers and Playwright session management."""
from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
import pytest


def test_stop_browser_session_safe_when_never_started():
    """stop_browser_session should not raise if session was never initialised."""
    from core.browser import playwright_session as ps
    ps._playwright = None
    ps._browser = None
    ps._active_page = None
    ps.stop_browser_session()  # must not raise


def test_stop_browser_session_closes_browser():
    """stop_browser_session closes browser and stops playwright."""
    from core.browser import playwright_session as ps

    mock_browser = MagicMock()
    mock_pw = MagicMock()
    ps._playwright = mock_pw
    ps._browser = mock_browser
    ps._active_page = MagicMock()

    ps.stop_browser_session()

    mock_browser.close.assert_called_once()
    mock_pw.stop.assert_called_once()
    assert ps._playwright is None
    assert ps._browser is None
    assert ps._active_page is None


def test_get_all_pages_returns_empty_when_no_session():
    """get_all_pages returns [] when no browser is connected."""
    from core.browser import playwright_session as ps
    ps._browser = None
    ps._active_page = None
    assert ps.get_all_pages() == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_stop_browser_session_safe_when_never_started -v 2>&1 | tail -10
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.browser'`

- [ ] **Step 3: Create package and session module**

```python
# core/browser/__init__.py
```

```python
# core/browser/playwright_session.py
"""Playwright browser session — singleton managing one active browser page.

Priority:
  1. CDP connect to user's Chrome at localhost:9222 (existing sessions/cookies)
  2. Launch standalone Playwright Chromium (no user cookies)

Thread-safety: a threading.Lock guards all state mutations.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_CDP_URL = "http://localhost:9222"
_LOCK = threading.Lock()

# Module-level singletons
_playwright = None
_browser = None
_active_page = None  # currently selected page


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_page():
    """Return the active Playwright page, connecting/launching if needed.

    Raises RuntimeError if browser cannot be started at all.
    """
    global _playwright, _browser, _active_page
    with _LOCK:
        if _active_page is not None:
            try:
                if not _active_page.is_closed():
                    return _active_page
            except Exception:
                pass
        _active_page = None
        _active_page = _connect_or_launch()
        return _active_page


def get_all_pages() -> list:
    """Return all open pages in the current browser (empty if not connected)."""
    global _browser
    with _LOCK:
        if _browser is None:
            return []
        try:
            pages = []
            for ctx in _browser.contexts:
                pages.extend(ctx.pages)
            return pages
        except Exception:
            return []


def switch_to_page_by_index(index: int):
    """Switch active page to the one at *index* in the flat page list.

    Returns the new active page or raises IndexError.
    """
    global _active_page
    with _LOCK:
        pages = []
        if _browser is not None:
            try:
                for ctx in _browser.contexts:
                    pages.extend(ctx.pages)
            except Exception:
                pass
        if not pages or index >= len(pages):
            raise IndexError(f"No page at index {index} (have {len(pages)} pages)")
        _active_page = pages[index]
        _active_page.bring_to_front()
        return _active_page


def stop_browser_session() -> None:
    """Close browser and stop Playwright. Safe to call if never started."""
    global _playwright, _browser, _active_page
    with _LOCK:
        try:
            if _browser is not None:
                _browser.close()
        except Exception:
            pass
        try:
            if _playwright is not None:
                _playwright.stop()
        except Exception:
            pass
        _playwright = None
        _browser = None
        _active_page = None
    logger.info("browser_session: stopped")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _connect_or_launch():
    """Try CDP connect first, fall back to standalone launch. Returns page."""
    global _playwright, _browser

    from playwright.sync_api import sync_playwright

    if _playwright is None:
        _playwright = sync_playwright().start()

    # --- Attempt 1: CDP connect to existing Chrome ---
    try:
        _browser = _playwright.chromium.connect_over_cdp(_CDP_URL)
        contexts = _browser.contexts
        if contexts:
            pages = contexts[0].pages
            page = pages[0] if pages else contexts[0].new_page()
        else:
            page = _browser.new_context().new_page()
        logger.info("browser_session: connected via CDP to %s", _CDP_URL)
        return page
    except Exception as cdp_exc:
        logger.info("browser_session: CDP connect failed (%s) — launching standalone", cdp_exc)

    # --- Attempt 2: Standalone Chromium ---
    _browser = _playwright.chromium.launch(headless=False)
    ctx = _browser.new_context()
    page = ctx.new_page()
    logger.info("browser_session: launched standalone Playwright Chromium")
    return page
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_stop_browser_session_safe_when_never_started tests/test_browser_tools.py::test_stop_browser_session_closes_browser tests/test_browser_tools.py::test_get_all_pages_returns_empty_when_no_session -v 2>&1 | tail -15
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/browser/__init__.py core/browser/playwright_session.py tests/test_browser_tools.py
git commit -m "feat(browser): Playwright session singleton — CDP connect + standalone fallback"
```

---

### Task 3: `set_browser_status()` helper

**Files:**
- Modify: `apps/api/jarvis_api/services/runtime_browser_body.py:154` (append after last function)
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_browser_tools.py`:

```python
def test_set_browser_status_updates_body():
    """set_browser_status should call ensure + update without raising."""
    from unittest.mock import patch
    import apps.api.jarvis_api.services.runtime_browser_body as rbb

    fake_body = {"body_id": "test-body-1", "status": "idle", "last_url": "",
                 "last_title": "", "active_task_id": "", "active_flow_id": "",
                 "focused_tab_id": "", "tabs": [], "summary": "", "profile_name": "jarvis-browser",
                 "created_at": "2026-01-01T00:00:00+00:00"}

    with patch.object(rbb, "ensure_browser_body", return_value=fake_body), \
         patch.object(rbb, "update_browser_body", return_value=fake_body) as mock_update:
        rbb.set_browser_status("navigating", url="https://example.com", title="Example")

    mock_update.assert_called_once_with(
        "test-body-1",
        status="navigating",
        last_url="https://example.com",
        last_title="Example",
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_set_browser_status_updates_body -v 2>&1 | tail -10
```

Expected: FAIL with `AttributeError: module 'apps.api.jarvis_api.services.runtime_browser_body' has no attribute 'set_browser_status'`

- [ ] **Step 3: Add helper to runtime_browser_body.py**

Append to the end of `apps/api/jarvis_api/services/runtime_browser_body.py`:

```python


def set_browser_status(status: str, *, url: str = "", title: str = "") -> None:
    """Update the default browser body status — called from browser tool handlers."""
    try:
        body = ensure_browser_body()
        update_browser_body(
            body["body_id"],
            status=status,
            last_url=url,
            last_title=title,
        )
    except Exception:
        pass  # Never let status update crash a tool call
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_set_browser_status_updates_body -v 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/runtime_browser_body.py tests/test_browser_tools.py
git commit -m "feat(browser): add set_browser_status() helper to runtime_browser_body"
```

---

### Task 4: Browser Tool Handlers — navigate + read

**Files:**
- Create: `core/tools/browser_tools.py`
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_browser_tools.py`:

```python
def test_browser_navigate_returns_title_and_url():
    """browser_navigate should return url and title on success."""
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.title.return_value = "Example Domain"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_navigate({"url": "https://example.com"})

    assert result["status"] == "ok"
    assert result["title"] == "Example Domain"
    assert result["url"] == "https://example.com"
    mock_page.goto.assert_called_once_with("https://example.com", timeout=15000, wait_until="domcontentloaded")


def test_browser_navigate_requires_url():
    """browser_navigate should return error when url is missing."""
    import core.tools.browser_tools as bt
    result = bt._exec_browser_navigate({})
    assert result["status"] == "error"
    assert "url" in result["error"]


def test_browser_read_full_page():
    """browser_read without selector returns body text."""
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.inner_text.return_value = "Hello world"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_read({})

    assert result["status"] == "ok"
    assert result["text"] == "Hello world"
    mock_page.inner_text.assert_called_once_with("body", timeout=10000)


def test_browser_read_with_selector():
    """browser_read with selector calls inner_text on that selector."""
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.inner_text.return_value = "Article text"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_read({"selector": ".article-body"})

    assert result["text"] == "Article text"
    mock_page.inner_text.assert_called_once_with(".article-body", timeout=10000)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_browser_navigate_returns_title_and_url -v 2>&1 | tail -10
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.tools.browser_tools'`

- [ ] **Step 3: Create browser_tools.py with navigate + read**

```python
# core/tools/browser_tools.py
"""Browser control tools for Jarvis — Playwright-backed.

Tools:
  browser_navigate   — navigate to URL
  browser_read       — read page text (full or selector)
  browser_click      — click element
  browser_type       — type into field
  browser_submit     — submit form
  browser_screenshot — capture page as base64 PNG
  browser_find_tabs  — list open tabs
  browser_switch_tab — switch active tab by index
"""
from __future__ import annotations

import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_READ_CHARS = 24_000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_page():
    from core.browser.playwright_session import get_page
    return get_page()


def _update_status(status: str, *, url: str = "", title: str = "") -> None:
    try:
        from apps.api.jarvis_api.services.runtime_browser_body import set_browser_status
        set_browser_status(status, url=url, title=title)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tool definitions (Ollama-compatible JSON schema)
# ---------------------------------------------------------------------------

BROWSER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": (
                "Navigate the browser to a URL. Returns the page title and final URL. "
                "Use this to open a new page or follow a link."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to (https:// prefix added if missing)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": (
                "Read visible text from the current page. "
                "If selector is provided, reads only that element. "
                "Otherwise reads the full page body (capped at 24 000 chars)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Optional CSS selector, e.g. '.article-body' or '#main'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element on the current page identified by a CSS or text selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or text selector, e.g. \"button:has-text('Submit')\""},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Type text into a form field identified by a CSS selector. Clears the field first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the input field"},
                    "text": {"type": "string", "description": "Text to type"},
                },
                "required": ["selector", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_submit",
            "description": (
                "Submit a form. If selector is given, presses Enter on that element. "
                "Otherwise clicks the first visible submit button on the page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Optional CSS selector for the submit button or input"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current page. Returns a base64-encoded PNG image.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_find_tabs",
            "description": "List all open browser tabs with their index, URL, and title.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_switch_tab",
            "description": "Switch the active browser tab by its index (from browser_find_tabs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_index": {"type": "integer", "description": "Zero-based tab index from browser_find_tabs"},
                },
                "required": ["tab_index"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _exec_browser_navigate(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"status": "error", "error": "url is required"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        page = _get_page()
        _update_status("navigating", url=url)
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        title = page.title()
        final_url = page.url
        _update_status("idle", url=final_url, title=title)
        return {"status": "ok", "url": final_url, "title": title}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_read(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    try:
        page = _get_page()
        _update_status("observing", url=page.url)
        target = selector if selector else "body"
        text = page.inner_text(target, timeout=10000)
        if len(text) > _MAX_READ_CHARS:
            text = text[:_MAX_READ_CHARS] + "…"
        _update_status("idle", url=page.url)
        return {"status": "ok", "text": text, "url": page.url, "chars": len(text), "selector": selector or "body"}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_browser_navigate_returns_title_and_url tests/test_browser_tools.py::test_browser_navigate_requires_url tests/test_browser_tools.py::test_browser_read_full_page tests/test_browser_tools.py::test_browser_read_with_selector -v 2>&1 | tail -15
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add core/tools/browser_tools.py tests/test_browser_tools.py
git commit -m "feat(browser): browser_navigate + browser_read tool handlers"
```

---

### Task 5: Browser Tool Handlers — click, type, submit, screenshot, tabs

**Files:**
- Modify: `core/tools/browser_tools.py` (append handlers)
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_browser_tools.py`:

```python
def test_browser_click_calls_locator_click():
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_click({"selector": "#submit-btn"})

    assert result["status"] == "ok"
    mock_page.locator.assert_called_once_with("#submit-btn")
    mock_page.locator.return_value.click.assert_called_once_with(timeout=10000)


def test_browser_click_requires_selector():
    import core.tools.browser_tools as bt
    result = bt._exec_browser_click({})
    assert result["status"] == "error"


def test_browser_type_calls_fill():
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_type({"selector": "input[name='email']", "text": "test@example.com"})

    assert result["status"] == "ok"
    mock_page.locator.return_value.fill.assert_called_once_with("test@example.com", timeout=10000)


def test_browser_screenshot_returns_base64():
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.screenshot.return_value = b"fakepngbytes"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_screenshot({})

    assert result["status"] == "ok"
    import base64
    assert result["image_b64"] == base64.b64encode(b"fakepngbytes").decode()


def test_browser_find_tabs_returns_list():
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page1 = MagicMock()
    mock_page1.url = "https://example.com"
    mock_page1.title.return_value = "Example"
    mock_page2 = MagicMock()
    mock_page2.url = "https://github.com"
    mock_page2.title.return_value = "GitHub"

    with patch("core.tools.browser_tools._get_all_pages", return_value=[mock_page1, mock_page2]):
        result = bt._exec_browser_find_tabs({})

    assert result["status"] == "ok"
    assert len(result["tabs"]) == 2
    assert result["tabs"][0]["tab_index"] == 0
    assert result["tabs"][1]["url"] == "https://github.com"


def test_browser_switch_tab_switches_page():
    from unittest.mock import MagicMock, patch
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.url = "https://github.com"
    mock_page.title.return_value = "GitHub"

    with patch("core.browser.playwright_session.switch_to_page_by_index", return_value=mock_page) as mock_switch, \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_switch_tab({"tab_index": 1})

    assert result["status"] == "ok"
    mock_switch.assert_called_once_with(1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_browser_click_calls_locator_click -v 2>&1 | tail -10
```

Expected: FAIL with `AttributeError: module 'core.tools.browser_tools' has no attribute '_exec_browser_click'`

- [ ] **Step 3: Append remaining handlers to browser_tools.py**

Append to the end of `core/tools/browser_tools.py`:

```python

def _get_all_pages() -> list:
    from core.browser.playwright_session import get_all_pages
    return get_all_pages()


def _exec_browser_click(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    if not selector:
        return {"status": "error", "error": "selector is required"}
    try:
        page = _get_page()
        _update_status("acting", url=page.url)
        page.locator(selector).click(timeout=10000)
        _update_status("idle", url=page.url)
        return {"status": "ok", "url": page.url}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_type(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    text = str(args.get("text") or "")
    if not selector:
        return {"status": "error", "error": "selector is required"}
    try:
        page = _get_page()
        _update_status("acting", url=page.url)
        page.locator(selector).fill(text, timeout=10000)
        _update_status("idle", url=page.url)
        return {"status": "ok", "selector": selector}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_submit(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    try:
        page = _get_page()
        _update_status("acting", url=page.url)
        if selector:
            page.locator(selector).press("Enter", timeout=10000)
        else:
            page.locator("button[type=submit], input[type=submit]").first.click(timeout=10000)
        final_url = page.url
        _update_status("idle", url=final_url)
        return {"status": "ok", "url": final_url}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    try:
        page = _get_page()
        _update_status("observing", url=page.url)
        png_bytes = page.screenshot(type="png", timeout=15000)
        image_b64 = base64.b64encode(png_bytes).decode("ascii")
        _update_status("idle", url=page.url)
        return {"status": "ok", "image_b64": image_b64, "url": page.url, "format": "png"}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_find_tabs(args: dict[str, Any]) -> dict[str, Any]:
    try:
        pages = _get_all_pages()
        tabs = []
        for i, p in enumerate(pages):
            try:
                tabs.append({"tab_index": i, "url": p.url, "title": p.title()})
            except Exception:
                tabs.append({"tab_index": i, "url": "", "title": ""})
        return {"status": "ok", "tabs": tabs, "count": len(tabs)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_switch_tab(args: dict[str, Any]) -> dict[str, Any]:
    tab_index = args.get("tab_index")
    if tab_index is None:
        return {"status": "error", "error": "tab_index is required"}
    try:
        from core.browser.playwright_session import switch_to_page_by_index
        page = switch_to_page_by_index(int(tab_index))
        _update_status("idle", url=page.url, title=page.title())
        return {"status": "ok", "url": page.url, "title": page.title(), "tab_index": int(tab_index)}
    except IndexError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add core/tools/browser_tools.py tests/test_browser_tools.py
git commit -m "feat(browser): click, type, submit, screenshot, find_tabs, switch_tab handlers"
```

---

### Task 6: Register Tools in simple_tools.py

**Files:**
- Modify: `core/tools/simple_tools.py`
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_browser_tools.py`:

```python
def test_browser_tools_registered_in_simple_tools():
    """All 8 browser tools appear in TOOL_DEFINITIONS and _TOOL_HANDLERS."""
    from core.tools import simple_tools

    names_in_defs = {
        t["function"]["name"]
        for t in simple_tools.TOOL_DEFINITIONS
        if t.get("type") == "function"
    }
    expected = {
        "browser_navigate", "browser_read", "browser_click",
        "browser_type", "browser_submit", "browser_screenshot",
        "browser_find_tabs", "browser_switch_tab",
    }
    assert expected.issubset(names_in_defs), f"Missing: {expected - names_in_defs}"
    assert expected.issubset(set(simple_tools._TOOL_HANDLERS.keys())), \
        f"Missing handlers: {expected - set(simple_tools._TOOL_HANDLERS.keys())}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_browser_tools_registered_in_simple_tools -v 2>&1 | tail -10
```

Expected: FAIL with `AssertionError: Missing: {'browser_navigate', ...}`

- [ ] **Step 3: Register in simple_tools.py**

In `core/tools/simple_tools.py`, find the end of `TOOL_DEFINITIONS` list (the `]` closing it, currently after `queue_followup`). Add **before** the closing `]`:

```python
    # --- Browser tools (Playwright) ---
    *__import__("core.tools.browser_tools", fromlist=["BROWSER_TOOL_DEFINITIONS"]).BROWSER_TOOL_DEFINITIONS,
```

In `_TOOL_HANDLERS` dict, add after `"queue_followup": _exec_queue_followup,`:

```python
    # --- Browser tools ---
    **{
        name: handler
        for name, handler in (
            ("browser_navigate", __import__("core.tools.browser_tools", fromlist=["_exec_browser_navigate"])._exec_browser_navigate),
            ("browser_read", __import__("core.tools.browser_tools", fromlist=["_exec_browser_read"])._exec_browser_read),
            ("browser_click", __import__("core.tools.browser_tools", fromlist=["_exec_browser_click"])._exec_browser_click),
            ("browser_type", __import__("core.tools.browser_tools", fromlist=["_exec_browser_type"])._exec_browser_type),
            ("browser_submit", __import__("core.tools.browser_tools", fromlist=["_exec_browser_submit"])._exec_browser_submit),
            ("browser_screenshot", __import__("core.tools.browser_tools", fromlist=["_exec_browser_screenshot"])._exec_browser_screenshot),
            ("browser_find_tabs", __import__("core.tools.browser_tools", fromlist=["_exec_browser_find_tabs"])._exec_browser_find_tabs),
            ("browser_switch_tab", __import__("core.tools.browser_tools", fromlist=["_exec_browser_switch_tab"])._exec_browser_switch_tab),
        )
    },
```

**Note:** The `__import__` inline approach avoids a circular import (browser_tools imports from session which imports playwright; importing at module load time in simple_tools.py is fine since playwright is now installed). If the inline `__import__` style feels fragile, use this cleaner alternative at the top of `simple_tools.py` instead:

```python
# Near the bottom of imports in simple_tools.py, add:
from core.tools.browser_tools import (
    BROWSER_TOOL_DEFINITIONS,
    _exec_browser_navigate,
    _exec_browser_read,
    _exec_browser_click,
    _exec_browser_type,
    _exec_browser_submit,
    _exec_browser_screenshot,
    _exec_browser_find_tabs,
    _exec_browser_switch_tab,
)
```

Then in TOOL_DEFINITIONS add `*BROWSER_TOOL_DEFINITIONS,` and in `_TOOL_HANDLERS` add the eight entries directly. **Use this cleaner form** — the `__import__` inline was shown for reference only.

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_browser_tools_registered_in_simple_tools -v 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Compile check**

```bash
conda run -n ai python -m py_compile core/tools/simple_tools.py core/tools/browser_tools.py core/browser/playwright_session.py && echo OK
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add core/tools/simple_tools.py
git commit -m "feat(browser): register all 8 browser tools in simple_tools"
```

---

### Task 7: Wire shutdown in app.py

**Files:**
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_browser_tools.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_browser_tools.py`:

```python
def test_stop_browser_session_importable_from_app_context():
    """stop_browser_session should be importable (verifies no circular import)."""
    from core.browser.playwright_session import stop_browser_session
    assert callable(stop_browser_session)
```

- [ ] **Step 2: Run test to verify it passes already**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py::test_stop_browser_session_importable_from_app_context -v 2>&1 | tail -10
```

Expected: PASS (import works)

- [ ] **Step 3: Add shutdown call to app.py**

In `apps/api/jarvis_api/app.py`, find the shutdown block:

```python
        logger.info("jarvis api shutdown begin")
        stop_heartbeat_scheduler()
        stop_notification_bridge()
```

Change to:

```python
        logger.info("jarvis api shutdown begin")
        stop_heartbeat_scheduler()
        stop_notification_bridge()
        try:
            from core.browser.playwright_session import stop_browser_session
            stop_browser_session()
        except Exception:
            pass
```

- [ ] **Step 4: Compile check**

```bash
conda run -n ai python -m py_compile apps/api/jarvis_api/app.py && echo OK
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat(browser): stop Playwright session on API shutdown"
```

---

### Task 8: Full Regression

**Files:**
- Run existing test suites

- [ ] **Step 1: Run full browser test suite**

```bash
conda run -n ai python -m pytest tests/test_browser_tools.py -v 2>&1 | tail -20
```

Expected: All tests pass

- [ ] **Step 2: Run existing tool tests**

```bash
conda run -n ai python -m pytest tests/test_memory_path_guard.py tests/test_internal_tools.py tests/test_heartbeat_triggers.py tests/test_heartbeat_bridge_triggers.py -v 2>&1 | tail -15
```

Expected: All pass

- [ ] **Step 3: Full compileall**

```bash
conda run -n ai python -m compileall core apps/api scripts 2>&1 | grep -iE "error" | head -10
```

Expected: no output

- [ ] **Step 4: Restart API and verify no startup errors**

```bash
sudo systemctl restart jarvis-api && sleep 6 && sudo journalctl -u jarvis-api --since "10 seconds ago" --no-pager | grep -iE "error|startup complete"
```

Expected: `jarvis api startup complete` with no errors

- [ ] **Step 5: Commit if any fixes were needed**

If steps 1-4 required fixes, commit them:

```bash
git add -p
git commit -m "fix(browser): regression fixes from full test suite"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| CDP connect to user's Chrome | Task 2 (`_connect_or_launch`) |
| Standalone fallback | Task 2 (fallback branch) |
| browser_navigate | Tasks 4, 6 |
| browser_read | Tasks 4, 6 |
| browser_click | Tasks 5, 6 |
| browser_type | Tasks 5, 6 |
| browser_submit | Tasks 5, 6 |
| browser_screenshot | Tasks 5, 6 |
| browser_find_tabs | Tasks 5, 6 |
| browser_switch_tab | Tasks 5, 6 |
| set_browser_status in runtime_browser_body | Task 3 |
| Mission Control status updates | Tasks 4+5 (`_update_status` calls) |
| stop_browser_session in shutdown | Task 7 |
| No execute_js | Not present — correct by omission |
| Rate limit 30 actions/run | Enforced by existing visible_runs.py loop cap — no code needed |

**Placeholder scan:** No TBD/TODO. All code blocks are complete.

**Type consistency:** `_get_page()` used in Tasks 4+5; `_get_all_pages()` in Task 5; `switch_to_page_by_index(int)` defined in Task 2 and called in Task 5. All consistent.
