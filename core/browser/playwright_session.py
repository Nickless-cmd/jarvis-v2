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
