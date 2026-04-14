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


def _get_all_pages() -> list:
    from core.browser.playwright_session import get_all_pages
    return get_all_pages()


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
