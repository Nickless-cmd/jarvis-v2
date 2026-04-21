# Browser Control Design — Jarvis v2

## Goal

Give Jarvis the ability to read, navigate, and fully interact with a web browser — using the user's existing Chrome session (authenticated, cookies intact) via CDP, with a clean fallback to a standalone Playwright browser.

## Architecture

Three layers:

```
Jarvis LLM
    ↓ tool call
core/tools/browser_tools.py         ← tool definitions + handlers
    ↓
core/browser/playwright_session.py  ← Playwright singleton, CDP connection
    ↓ CDP                               ↓ fallback
User's Chrome (port 9222)          Standalone Playwright Chromium

    ↕ status updates
runtime_browser_body (existing)     ← Mission Control live view
```

**New files:**
- `core/tools/browser_tools.py` — tool definitions + handlers (registered in `simple_tools.py`)
- `core/browser/__init__.py`
- `core/browser/playwright_session.py` — session singleton, CDP connect + launch fallback

**Modified files:**
- `core/tools/simple_tools.py` — import and register browser tool handlers
- `apps/api/jarvis_api/app.py` — call `stop_browser_session()` in lifespan shutdown
- `apps/api/jarvis_api/services/runtime_browser_body.py` — add `set_browser_status(status, url, title)` helper if not present

## Tools Exposed to Jarvis

| Tool | Parameters | Returns |
|------|-----------|---------|
| `browser_navigate` | `url: str` | `{url, title, status}` |
| `browser_read` | `selector?: str` | `{text, url, chars}` |
| `browser_click` | `selector: str` | `{status, url}` |
| `browser_type` | `selector: str, text: str` | `{status}` |
| `browser_submit` | `selector?: str` | `{status, url}` |
| `browser_screenshot` | — | `{image_b64, url, width, height}` |
| `browser_find_tabs` | — | `[{tab_id, url, title}]` |
| `browser_switch_tab` | `tab_id: str` | `{status, url, title}` |

All tools are auto-executed (no approval gate). All actions update `runtime_browser_body` status so Mission Control reflects what Jarvis is doing in real time.

## Session Lifecycle

```
First browser tool call
  → try CDP connect to localhost:9222
  → success? → use existing Chrome (user's cookies and sessions)
  → failure?  → launch standalone Playwright Chromium (no user cookies)
  → store session in module-level singleton

Subsequent calls
  → reuse existing session
  → if session died (Chrome closed, CDP lost) → reconnect automatically on next call

API shutdown
  → stop_browser_session() called in lifespan shutdown
  → session closed cleanly
```

The singleton is module-level in `playwright_session.py`. No persistent storage across API restarts — session reconnects on first call after restart.

## CDP Setup (One-Time)

Chrome must be started with `--remote-debugging-port=9222`. Recommended: create a launcher alias or `.desktop` entry:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.config/google-chrome
```

If port 9222 is not reachable, `playwright_session.py` logs an info message and launches a standalone Playwright browser as fallback. No error is raised.

## Selector Model

Jarvis uses CSS selectors and Playwright text selectors:

```python
browser_click(selector="button:has-text('Login')")
browser_click(selector="#submit-btn")
browser_type(selector="input[name='email']", text="user@example.com")
browser_read(selector=".article-body")
```

If Jarvis is unsure of the correct selector, he calls `browser_screenshot()` to see the page, then selects based on what he observes. This is standard agentic loop — no special handling required.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| CDP port not open | Fall back to launch mode, log info |
| Selector not found | Return `{status: "not_found", hint: "element not found"}` — Jarvis retries with different selector |
| Navigation timeout (15s) | Return partial page text + `{partial: true}` |
| Chrome closes mid-session | Auto-reconnect on next tool call |
| Page requires login, no session | `browser_read` returns login form text — Jarvis uses `browser_type` + `browser_submit` |

## Security Boundaries

| Blocked action | Reason |
|---------------|--------|
| File downloads to arbitrary paths | Downloads limited to `/tmp/jarvis-browser/` only |
| Opening new browser profiles | Only existing profile or Playwright default |
| `browser_execute_js(code)` | Not exposed — unconstrained exfil channel |
| OS-level keyboard shortcuts | Playwright keyboard is scoped to page |

**No `execute_js` tool.** All JS interaction goes through Playwright's `click()`, `fill()`, `select_option()` which trigger JS events correctly without exposing arbitrary code execution.

**Rate limit:** Max 30 browser actions per visible run (same loop cap as other tools).

## Mission Control Integration

`runtime_browser_body.py` (existing) tracks browser state. Every tool action calls:

```python
set_browser_status(status="navigating", url="https://...", title="Page Title")
# → "acting" during click/type/submit
# → "idle" when done
```

MC shows current browser status, URL, and title in real time. User can observe Jarvis's browser activity without any approval gates. A kill-switch (stop session via MC endpoint) will be added as a follow-up if needed.

## Testing Strategy

- Unit tests mock the Playwright session (`AsyncMock` for page methods)
- Test each tool handler independently: correct params → correct result shape
- Test fallback path: CDP connect fails → standalone browser launched
- Test error cases: selector not found, navigation timeout, dead session reconnect
- `compileall` and full regression suite as final gate

## Out of Scope

- Browser extension for passive tab observation (separate project)
- Vision-model-based screenshot understanding (can be added later — screenshot tool provides the raw material)
- Multi-profile management
- Proxy/VPN routing
