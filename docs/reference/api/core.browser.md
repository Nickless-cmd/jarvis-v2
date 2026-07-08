# `core.browser` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/browser/__init__.py`

_(no top-level classes or functions)_

## `core/browser/playwright_session.py`
_Playwright browser session — dedicated worker thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cdp_port_open` | `()` | Return True if something is already listening on the CDP port. | [src](../../../core/browser/playwright_session.py#L51) |
| function | `_start_headless_chrome` | `()` | Launch a headless Chrome subprocess if the CDP port is not open. | [src](../../../core/browser/playwright_session.py#L60) |
| function | `_stop_headless_chrome` | `()` | Terminate the Chrome subprocess if we started it. | [src](../../../core/browser/playwright_session.py#L98) |
| class | `_WorkerState` | `` | Mutable state owned entirely by the worker thread. | [src](../../../core/browser/playwright_session.py#L116) |
| method | `_WorkerState.__init__` | `(self)` | — | [src](../../../core/browser/playwright_session.py#L120) |
| class | `_BrowserCtx` | `` | Context passed to each run_in_playwright callable. | [src](../../../core/browser/playwright_session.py#L126) |
| method | `_BrowserCtx.__init__` | `(self, page, browser, state)` | — | [src](../../../core/browser/playwright_session.py#L136) |
| method | `_BrowserCtx.all_pages` | `(self)` | Return all open pages across all browser contexts. | [src](../../../core/browser/playwright_session.py#L141) |
| method | `_BrowserCtx.switch_page` | `(self, page)` | Update the worker's active page (used by tab-switch operations). | [src](../../../core/browser/playwright_session.py#L153) |
| function | `_playwright_worker` | `(state, ready)` | Runs in its own thread.  Owns all Playwright sync API objects. | [src](../../../core/browser/playwright_session.py#L169) |
| function | `_ensure_worker` | `()` | Start the worker thread if it is not already running. | [src](../../../core/browser/playwright_session.py#L249) |
| function | `run_in_playwright` | `(fn, timeout=…)` | Execute *fn* in the Playwright worker thread and return its result. | [src](../../../core/browser/playwright_session.py#L274) |
| function | `stop_browser_session` | `()` | Signal the worker to close the browser and stop.  Also stops any | [src](../../../core/browser/playwright_session.py#L298) |
| function | `get_all_pages` | `()` | Return all open pages.  Returns [] if no session is active. | [src](../../../core/browser/playwright_session.py#L313) |
| function | `switch_to_page_by_index` | `(index)` | Switch active page to the one at *index*.  Returns the new page. | [src](../../../core/browser/playwright_session.py#L324) |

