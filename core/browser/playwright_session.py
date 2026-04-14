"""Playwright browser session — dedicated worker thread.

Playwright's sync API cannot be called from within a running asyncio event
loop (e.g. FastAPI/uvicorn).  All Playwright calls run in a single daemon
thread (*jarvis-playwright*) that owns the sync Playwright instance.

Public API
----------
run_in_playwright(fn, timeout=30.0)
    Execute fn(_BrowserCtx) in the worker thread.  fn receives a
    _BrowserCtx that exposes .page, .browser, and helpers.

stop_browser_session()
    Signal the worker to close the browser and exit cleanly.

get_all_pages() / switch_to_page_by_index(index)
    Convenience wrappers; both use run_in_playwright internally.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

_CDP_URL = "http://localhost:9222"

# ---------------------------------------------------------------------------
# Internal state types
# ---------------------------------------------------------------------------

class _WorkerState:
    """Mutable state owned entirely by the worker thread."""
    __slots__ = ("pw", "browser", "active_page")

    def __init__(self) -> None:
        self.pw = None
        self.browser = None
        self.active_page = None


class _BrowserCtx:
    """Context passed to each run_in_playwright callable.

    Attributes
    ----------
    page    : current active Playwright Page
    browser : the underlying Browser (CDP or standalone)
    """
    __slots__ = ("page", "browser", "_state")

    def __init__(self, page, browser, state: _WorkerState) -> None:
        self.page = page
        self.browser = browser
        self._state = state

    def all_pages(self) -> list:
        """Return all open pages across all browser contexts."""
        if self._state.browser is None:
            return []
        try:
            pages: list = []
            for ctx in self._state.browser.contexts:
                pages.extend(ctx.pages)
            return pages
        except Exception:
            return []

    def switch_page(self, page) -> None:
        """Update the worker's active page (used by tab-switch operations)."""
        self._state.active_page = page


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

_STOP = object()  # sentinel value

_THREAD_LOCK = threading.Lock()
_CMD_QUEUE: queue.Queue = queue.Queue()
_WORKER_THREAD: threading.Thread | None = None


def _playwright_worker(state: _WorkerState, ready: threading.Event) -> None:
    """Runs in its own thread.  Owns all Playwright sync API objects."""
    from playwright.sync_api import sync_playwright

    def _connect_or_launch():
        # CDP first (existing Chrome session / cookies)
        try:
            state.browser = state.pw.chromium.connect_over_cdp(_CDP_URL)
            contexts = state.browser.contexts
            if contexts:
                pages = contexts[0].pages
                page = pages[0] if pages else contexts[0].new_page()
            else:
                page = state.browser.new_context().new_page()
            logger.info("browser_session: connected via CDP to %s", _CDP_URL)
            return page
        except Exception as cdp_exc:
            logger.info(
                "browser_session: CDP connect failed (%s) — launching standalone", cdp_exc
            )
        # Standalone Chromium
        state.browser = state.pw.chromium.launch(headless=False)
        ctx = state.browser.new_context()
        page = ctx.new_page()
        logger.info("browser_session: launched standalone Playwright Chromium")
        return page

    def _get_page():
        if state.active_page is not None:
            try:
                if not state.active_page.is_closed():
                    return state.active_page
            except Exception:
                pass
        state.active_page = None
        state.active_page = _connect_or_launch()
        return state.active_page

    try:
        state.pw = sync_playwright().start()
        ready.set()

        while True:
            item = _CMD_QUEUE.get()
            if item is _STOP:
                break
            fn, done, holder = item
            try:
                page = _get_page()
                ctx = _BrowserCtx(page, state.browser, state)
                holder["result"] = fn(ctx)
            except Exception as exc:
                holder["error"] = exc
            finally:
                done.set()

    except Exception as exc:
        logger.error("browser_session: worker crashed: %s", exc)
        ready.set()  # unblock callers even on startup failure
    finally:
        try:
            if state.browser:
                state.browser.close()
        except Exception:
            pass
        try:
            if state.pw:
                state.pw.stop()
        except Exception:
            pass
        state.pw = None
        state.browser = None
        state.active_page = None
        logger.info("browser_session: worker stopped")


def _ensure_worker() -> None:
    """Start the worker thread if it is not already running."""
    global _WORKER_THREAD, _CMD_QUEUE
    with _THREAD_LOCK:
        if _WORKER_THREAD is not None and _WORKER_THREAD.is_alive():
            return
        # Fresh queue so stale commands from a previous crashed worker are gone
        _CMD_QUEUE = queue.Queue()
        state = _WorkerState()
        ready = threading.Event()
        _WORKER_THREAD = threading.Thread(
            target=_playwright_worker,
            args=(state, ready),
            name="jarvis-playwright",
            daemon=True,
        )
        _WORKER_THREAD.start()
        if not ready.wait(timeout=15.0):
            logger.warning("browser_session: worker did not signal ready in time")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_in_playwright(fn: Callable[[_BrowserCtx], Any], timeout: float = 30.0) -> Any:
    """Execute *fn* in the Playwright worker thread and return its result.

    Parameters
    ----------
    fn      : Callable that receives a _BrowserCtx and returns any value.
    timeout : Seconds to wait for the operation to complete.

    Raises
    ------
    RuntimeError  if the operation times out.
    Any exception raised inside *fn* is re-raised in the caller's thread.
    """
    _ensure_worker()
    done: threading.Event = threading.Event()
    holder: dict = {}
    _CMD_QUEUE.put((fn, done, holder))
    if not done.wait(timeout=timeout):
        raise RuntimeError(f"Playwright operation timed out after {timeout}s")
    if "error" in holder:
        raise holder["error"]
    return holder["result"]


def stop_browser_session() -> None:
    """Signal the worker to close the browser and stop.  Safe if never started."""
    global _WORKER_THREAD
    with _THREAD_LOCK:
        if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
            return
    _CMD_QUEUE.put(_STOP)
    if _WORKER_THREAD is not None:
        _WORKER_THREAD.join(timeout=10.0)
    logger.info("browser_session: stopped")


def get_all_pages() -> list:
    """Return all open pages.  Returns [] if no session is active."""
    global _WORKER_THREAD
    if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
        return []
    try:
        return run_in_playwright(lambda ctx: ctx.all_pages(), timeout=5.0)
    except Exception:
        return []


def switch_to_page_by_index(index: int):
    """Switch active page to the one at *index*.  Returns the new page.

    Raises IndexError if the index is out of range.
    """
    def _switch(ctx: _BrowserCtx):
        pages = ctx.all_pages()
        if not pages or index >= len(pages):
            raise IndexError(f"No page at index {index} (have {len(pages)} pages)")
        page = pages[index]
        page.bring_to_front()
        ctx.switch_page(page)
        return page

    return run_in_playwright(_switch)
