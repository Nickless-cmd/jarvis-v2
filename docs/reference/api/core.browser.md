# `core.browser` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/browser/__init__.py`

_(no top-level classes or functions)_

## `core/browser/playwright_session.py`
_Playwright browser session — dedicated worker thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cdp_port_open` | `()` | Return True if something is already listening on the CDP port. | [src](../../../core/browser/playwright_session.py#L51) |
| function | `_start_headless_chrome` | `()` | Launch a headless Chrome subprocess if the CDP port is not open. | [src](../../../core/browser/playwright_session.py#L60) |
| function | `_stop_headless_chrome` | `()` | Terminate the Chrome subprocess if we started it. | [src](../../../core/browser/playwright_session.py#L113) |
| class | `_WorkerState` | `` | Mutable state owned entirely by the worker thread. | [src](../../../core/browser/playwright_session.py#L131) |
| method | `_WorkerState.__init__` | `(self)` | — | [src](../../../core/browser/playwright_session.py#L135) |
| class | `_BrowserCtx` | `` | Context passed to each run_in_playwright callable. | [src](../../../core/browser/playwright_session.py#L141) |
| method | `_BrowserCtx.__init__` | `(self, page, browser, state)` | — | [src](../../../core/browser/playwright_session.py#L151) |
| method | `_BrowserCtx.all_pages` | `(self)` | Return all open pages across all browser contexts. | [src](../../../core/browser/playwright_session.py#L156) |
| method | `_BrowserCtx.switch_page` | `(self, page)` | Update the worker's active page (used by tab-switch operations). | [src](../../../core/browser/playwright_session.py#L168) |
| function | `_playwright_worker` | `(state, ready)` | Runs in its own thread.  Owns all Playwright sync API objects. | [src](../../../core/browser/playwright_session.py#L184) |
| function | `_ensure_worker` | `()` | Start the worker thread if it is not already running. | [src](../../../core/browser/playwright_session.py#L264) |
| function | `run_in_playwright` | `(fn, timeout=…)` | Execute *fn* in the Playwright worker thread and return its result. | [src](../../../core/browser/playwright_session.py#L289) |
| function | `stop_browser_session` | `()` | Signal the worker to close the browser and stop.  Also stops any | [src](../../../core/browser/playwright_session.py#L313) |
| function | `get_all_pages` | `()` | Return all open pages.  Returns [] if no session is active. | [src](../../../core/browser/playwright_session.py#L328) |
| function | `switch_to_page_by_index` | `(index)` | Switch active page to the one at *index*.  Returns the new page. | [src](../../../core/browser/playwright_session.py#L339) |

## `core/browser/screencast.py`
_CDP-screencast af Jarvis' server-side browser — kilden til PWA'ens delte browser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `normaliser_url` | `(url)` | Kun http(s) og about:blank. file:, javascript:, chrome: m.fl. afvises. | [src](../../../core/browser/screencast.py#L33) |
| function | `_tal` | `(v, lo, hi)` | — | [src](../../../core/browser/screencast.py#L48) |
| class | `ScreencastSession` | `` | Én WS-forbindelses skærmstrøm + input mod den aktive side. | [src](../../../core/browser/screencast.py#L58) |
| method | `ScreencastSession.__init__` | `(self, *, quality=…, max_queue=…)` | — | [src](../../../core/browser/screencast.py#L61) |
| method | `ScreencastSession._on_frame` | `(self, params)` | — | [src](../../../core/browser/screencast.py#L70) |
| method | `ScreencastSession._detach` | `(self)` | — | [src](../../../core/browser/screencast.py#L93) |
| method | `ScreencastSession._attach` | `(self, ctx)` | — | [src](../../../core/browser/screencast.py#L103) |
| method | `ScreencastSession._start_fn` | `(self, ctx)` | — | [src](../../../core/browser/screencast.py#L113) |
| method | `ScreencastSession._pump_fn` | `(self, ctx)` | — | [src](../../../core/browser/screencast.py#L117) |
| method | `ScreencastSession._stop_fn` | `(self, ctx)` | — | [src](../../../core/browser/screencast.py#L132) |
| method | `ScreencastSession.start` | `(self)` | — | [src](../../../core/browser/screencast.py#L137) |
| method | `ScreencastSession.pump` | `(self)` | — | [src](../../../core/browser/screencast.py#L140) |
| method | `ScreencastSession.stop` | `(self)` | — | [src](../../../core/browser/screencast.py#L143) |
| method | `ScreencastSession.next_frame` | `(self, timeout=…)` | — | [src](../../../core/browser/screencast.py#L149) |
| function | `bygg_input` | `(msg)` | Oversaet en klientbesked til en worker-funktion, eller None hvis ugyldig. | [src](../../../core/browser/screencast.py#L158) |
| function | `hent_faner` | `(ctx)` | Faneliste i samme form som Electron-broens `faner()`. | [src](../../../core/browser/screencast.py#L263) |

