"""Tests for browser tool handlers and Playwright session management."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# set_browser_status tests
# ---------------------------------------------------------------------------

def test_set_browser_status_updates_body():
    """set_browser_status should call ensure + update without raising."""
    import apps.api.jarvis_api.services.runtime_browser_body as rbb

    fake_body = {
        "body_id": "test-body-1", "status": "idle", "last_url": "",
        "last_title": "", "active_task_id": "", "active_flow_id": "",
        "focused_tab_id": "", "tabs": [], "summary": "",
        "profile_name": "jarvis-browser",
        "created_at": "2026-01-01T00:00:00+00:00",
    }

    with patch.object(rbb, "ensure_browser_body", return_value=fake_body), \
         patch.object(rbb, "update_browser_body", return_value=fake_body) as mock_update:
        rbb.set_browser_status("navigating", url="https://example.com", title="Example")

    mock_update.assert_called_once_with(
        "test-body-1",
        status="navigating",
        last_url="https://example.com",
        last_title="Example",
    )


# ---------------------------------------------------------------------------
# browser_navigate tests
# ---------------------------------------------------------------------------

def test_browser_navigate_returns_title_and_url():
    """browser_navigate should return url and title on success."""
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
    mock_page.goto.assert_called_once_with(
        "https://example.com", timeout=15000, wait_until="domcontentloaded"
    )


def test_browser_navigate_requires_url():
    """browser_navigate should return error when url is missing."""
    import core.tools.browser_tools as bt
    result = bt._exec_browser_navigate({})
    assert result["status"] == "error"
    assert "url" in result["error"]


def test_browser_navigate_adds_https_prefix():
    """browser_navigate prepends https:// when missing."""
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.title.return_value = "Example"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        bt._exec_browser_navigate({"url": "example.com"})

    mock_page.goto.assert_called_once_with(
        "https://example.com", timeout=15000, wait_until="domcontentloaded"
    )


# ---------------------------------------------------------------------------
# browser_read tests
# ---------------------------------------------------------------------------

def test_browser_read_full_page():
    """browser_read without selector returns body text."""
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
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.inner_text.return_value = "Article text"
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_read({"selector": ".article-body"})

    assert result["text"] == "Article text"
    mock_page.inner_text.assert_called_once_with(".article-body", timeout=10000)


# ---------------------------------------------------------------------------
# browser_click, browser_type, browser_submit tests
# ---------------------------------------------------------------------------

def test_browser_click_calls_locator_click():
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
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.url = "https://example.com"

    with patch("core.tools.browser_tools._get_page", return_value=mock_page), \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_type({"selector": "input[name='email']", "text": "test@example.com"})

    assert result["status"] == "ok"
    mock_page.locator.return_value.fill.assert_called_once_with("test@example.com", timeout=10000)


def test_browser_screenshot_returns_base64():
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
    import core.tools.browser_tools as bt

    mock_page = MagicMock()
    mock_page.url = "https://github.com"
    mock_page.title.return_value = "GitHub"

    with patch("core.browser.playwright_session.switch_to_page_by_index", return_value=mock_page) as mock_switch, \
         patch("core.tools.browser_tools._update_status"):
        result = bt._exec_browser_switch_tab({"tab_index": 1})

    assert result["status"] == "ok"
    mock_switch.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# Registration test
# ---------------------------------------------------------------------------

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
    assert expected.issubset(names_in_defs), f"Missing from defs: {expected - names_in_defs}"
    assert expected.issubset(set(simple_tools._TOOL_HANDLERS.keys())), \
        f"Missing handlers: {expected - set(simple_tools._TOOL_HANDLERS.keys())}"


def test_stop_browser_session_importable_from_app_context():
    """stop_browser_session should be importable (verifies no circular import)."""
    from core.browser.playwright_session import stop_browser_session
    assert callable(stop_browser_session)
