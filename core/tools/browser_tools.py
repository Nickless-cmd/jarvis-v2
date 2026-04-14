"""Browser control tools for Jarvis — Playwright-backed.

All Playwright operations are dispatched through run_in_playwright() so they
run in the dedicated worker thread and never block the asyncio event loop.

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

from core.browser.playwright_session import run_in_playwright

logger = logging.getLogger(__name__)

_MAX_READ_CHARS = 24_000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
        _update_status("navigating", url=url)

        def _do(ctx):
            ctx.page.goto(url, timeout=15000, wait_until="domcontentloaded")
            return {"title": ctx.page.title(), "url": ctx.page.url}

        r = run_in_playwright(_do)
        _update_status("idle", url=r["url"], title=r["title"])
        return {"status": "ok", "url": r["url"], "title": r["title"]}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_read(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    try:
        def _do(ctx):
            _update_status("observing", url=ctx.page.url)
            target = selector if selector else "body"
            text = ctx.page.inner_text(target, timeout=10000)
            if len(text) > _MAX_READ_CHARS:
                text = text[:_MAX_READ_CHARS] + "…"
            return {"text": text, "url": ctx.page.url}

        r = run_in_playwright(_do)
        _update_status("idle", url=r["url"])
        return {
            "status": "ok",
            "text": r["text"],
            "url": r["url"],
            "chars": len(r["text"]),
            "selector": selector or "body",
        }
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_click(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    if not selector:
        return {"status": "error", "error": "selector is required"}
    try:
        def _do(ctx):
            _update_status("acting", url=ctx.page.url)
            ctx.page.locator(selector).click(timeout=10000)
            return ctx.page.url

        url = run_in_playwright(_do)
        _update_status("idle", url=url)
        return {"status": "ok", "url": url}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_type(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    text = str(args.get("text") or "")
    if not selector:
        return {"status": "error", "error": "selector is required"}
    try:
        def _do(ctx):
            _update_status("acting", url=ctx.page.url)
            ctx.page.locator(selector).fill(text, timeout=10000)

        run_in_playwright(_do)
        _update_status("idle")
        return {"status": "ok", "selector": selector}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_submit(args: dict[str, Any]) -> dict[str, Any]:
    selector = str(args.get("selector") or "").strip()
    try:
        def _do(ctx):
            _update_status("acting", url=ctx.page.url)
            if selector:
                ctx.page.locator(selector).press("Enter", timeout=10000)
            else:
                ctx.page.locator("button[type=submit], input[type=submit]").first.click(timeout=10000)
            return ctx.page.url

        url = run_in_playwright(_do)
        _update_status("idle", url=url)
        return {"status": "ok", "url": url}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    try:
        def _do(ctx):
            _update_status("observing", url=ctx.page.url)
            png_bytes = ctx.page.screenshot(type="png", timeout=15000)
            return {"image_b64": base64.b64encode(png_bytes).decode("ascii"), "url": ctx.page.url}

        r = run_in_playwright(_do)
        _update_status("idle", url=r["url"])
        return {"status": "ok", "image_b64": r["image_b64"], "url": r["url"], "format": "png"}
    except Exception as exc:
        _update_status("idle")
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_find_tabs(args: dict[str, Any]) -> dict[str, Any]:
    try:
        def _do(ctx):
            pages = ctx.all_pages()
            tabs = []
            for i, p in enumerate(pages):
                try:
                    tabs.append({"tab_index": i, "url": p.url, "title": p.title()})
                except Exception:
                    tabs.append({"tab_index": i, "url": "", "title": ""})
            return tabs

        tabs = run_in_playwright(_do)
        return {"status": "ok", "tabs": tabs, "count": len(tabs)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}


def _exec_browser_switch_tab(args: dict[str, Any]) -> dict[str, Any]:
    tab_index = args.get("tab_index")
    if tab_index is None:
        return {"status": "error", "error": "tab_index is required"}
    try:
        def _do(ctx):
            pages = ctx.all_pages()
            idx = int(tab_index)
            if not pages or idx >= len(pages):
                raise IndexError(f"No page at index {idx} (have {len(pages)} pages)")
            page = pages[idx]
            page.bring_to_front()
            ctx.switch_page(page)
            return {"url": page.url, "title": page.title()}

        r = run_in_playwright(_do)
        _update_status("idle", url=r["url"], title=r["title"])
        return {"status": "ok", "url": r["url"], "title": r["title"], "tab_index": int(tab_index)}
    except IndexError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}
