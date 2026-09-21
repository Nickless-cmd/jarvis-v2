"""Jarvis' EGEN browser inde i desk — otte værktøjer over broen.

Bjørn 21/9-2026: «brug din browser i desk». Der findes allerede en browser i
desk-appen — `apps/jarvis-desk/electron/jarvisBrowser.ts` — en rigtig Electron
`WebContentsView` lagt oven på vinduet, så Bjørn kan SE hvad der sker og selv
gribe ind med musen midt i det. Den er ikke puppeteer og ikke en fremmed
Chrome: den er en flade vi deler.

Handlersne lå færdige i desk'ens `electron/bridge.ts` (otte stk.), men de var
**ikke registreret i runtimen** — der fandtes ingen tool-definition og ingen
wrapper. Maalt 21/9-2026: `bridge_registry.dispatch(tool="jarvis_browser_open")`
nåede frem og virkede, men kun ad den interne cross-process-dispatch
(`POST /api/internal/jarvisx-bridge/dispatch` med shared-secret). Altså en
bagdør. Dette modul lukker den: værktøjerne bliver rigtige, kaldbare som alle
andre, uden omvejen.

Hvorfor et eget modul og ikke `operator_tools.py`: de er desk-specifikke, ikke
generelle operator-værktøjer. De deler hylde med `desk_view_tools.py`
(`desk_get_layout` m.fl.) — men hvor den taler med desk gennem en DB-tabel
desk poller, taler disse gennem JarvisX-broen, ligesom `operator_*`.

Et værktøj er ikke færdigt når det er skrevet: det skal ogsaa staa i
`tool_scoping.py`, ellers annonceres det ikke for modellen og findes reelt ikke.
Se noten dér (6/9-2026) om netop det.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Browser-operationer gaar over en WebSocket til en anden maskine. `read` af
#: 24.000 tegn og et PNG-skaermbillede er de tunge; resten er smaa.
_TIMEOUT_LET = 30.0
_TIMEOUT_TUNG = 60.0


async def _bro(*, tool: str, args: dict[str, Any], user_id: str, timeout_s: float) -> Any:
    """Kald desk-broen. Returnerer den UDPAKKEDE resultat-værdi."""
    from core.tools.operator_tools import _bridge_call

    return await _bridge_call(
        tool=tool, args=args, user_id=user_id, timeout_s=timeout_s,
    )


def _koer(tool: str, args: dict[str, Any], runtime_args: dict[str, Any], *,
          timeout_s: float) -> dict[str, Any]:
    """Fælles vej: find brugeren, kald broen i hoved-loopet, svar ærligt.

    `_run_operator_async` leverer `{"status": "ok", "result": <udpakket>}` —
    eller en fejl vi sender videre uændret. Vi pakker ikke om: et svar der
    siger hvad der gik galt er mere værd end et pænt et der skjuler det.
    """
    from core.tools.simple_tools_operator import _operator_user_id, _run_operator_async

    user_id = _operator_user_id(runtime_args)
    return _run_operator_async(
        lambda: _bro(tool=tool, args=args, user_id=user_id, timeout_s=timeout_s),
        tool_name=tool,
        timeout_s=timeout_s,
    )


def _tab_id(args: dict[str, Any]) -> dict[str, Any]:
    """`tab_id` er valgfri; udelades den, rammer broen den AKTIVE fane."""
    t = args.get("tab_id")
    if t in (None, ""):
        return {}
    try:
        return {"tab_id": int(t)}
    except (TypeError, ValueError):  # ikke et tal → behandl som «den aktive fane»
        return {}


# ── de otte handlinger ──────────────────────────────────────────────────


def _exec_jarvis_browser_open(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"status": "error", "error": "url er påkrævet"}
    return _koer("jarvis_browser_open", {"url": url}, args, timeout_s=_TIMEOUT_TUNG)


def _exec_jarvis_browser_navigate(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    if not url:
        return {"status": "error", "error": "url er påkrævet"}
    return _koer("jarvis_browser_navigate", {"url": url, **_tab_id(args)}, args,
                 timeout_s=_TIMEOUT_TUNG)


def _exec_jarvis_browser_read(args: dict[str, Any]) -> dict[str, Any]:
    ud: dict[str, Any] = {**_tab_id(args)}
    if args.get("max_chars") not in (None, ""):
        try:
            ud["max_chars"] = int(args["max_chars"])
        except (TypeError, ValueError):  # ugyldigt tal → lad siden bruge sin egen grænse
            pass
    return _koer("jarvis_browser_read", ud, args, timeout_s=_TIMEOUT_TUNG)


def _exec_jarvis_browser_click(args: dict[str, Any]) -> dict[str, Any]:
    try:
        x, y = float(args["x"]), float(args["y"])
    except (KeyError, TypeError, ValueError):  # mangler eller ikke tal → sig det frem for at kaste
        return {"status": "error", "error": "x og y er påkrævet som tal"}
    return _koer("jarvis_browser_click", {"x": x, "y": y, **_tab_id(args)}, args,
                 timeout_s=_TIMEOUT_LET)


def _exec_jarvis_browser_type(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if text in (None, ""):
        return {"status": "error", "error": "text er påkrævet"}
    return _koer("jarvis_browser_type", {"text": str(text), **_tab_id(args)}, args,
                 timeout_s=_TIMEOUT_LET)


def _exec_jarvis_browser_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    return _koer("jarvis_browser_screenshot", _tab_id(args), args,
                 timeout_s=_TIMEOUT_TUNG)


def _exec_jarvis_browser_tabs(args: dict[str, Any]) -> dict[str, Any]:
    return _koer("jarvis_browser_tabs", {}, args, timeout_s=_TIMEOUT_LET)


def _exec_jarvis_browser_close(args: dict[str, Any]) -> dict[str, Any]:
    t = args.get("tab_id")
    if t in (None, ""):
        return {"status": "error", "error": "tab_id er påkrævet for at lukke en fane"}
    try:
        return _koer("jarvis_browser_close", {"tab_id": int(t)}, args,
                     timeout_s=_TIMEOUT_LET)
    except (TypeError, ValueError):  # ikke et tal → svar med fejlen frem for at kaste
        return {"status": "error", "error": "tab_id skal være et tal"}


def _nr(desc: str) -> dict[str, Any]:
    return {"type": "number", "description": desc}


_TAB = _nr("Fane-id fra `jarvis_browser_tabs`. Udelades den, rammes den aktive fane.")

DESK_BROWSER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_open",
            "description": (
                "Open a URL in Jarvis' OWN browser — a real web view inside the jarvis-desk "
                "window, visible to the user, who can also click in it. This is NOT the "
                "operator's external Chrome and not a headless session: it is a shared surface. "
                "Returns {id, url, titel, aktiv}. Use `jarvis_browser_read` to see the page and "
                "`jarvis_browser_screenshot` to look at it."
            ),
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to open (https:// added if missing)."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_navigate",
            "description": "Navigate an existing tab in Jarvis' own desk browser to a new URL. Use `jarvis_browser_open` to create a new tab instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to."},
                    "tab_id": _TAB,
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_read",
            "description": (
                "Read the visible text of the page in Jarvis' desk browser — the cheapest way to "
                "see what is on screen. Returns {text, chars}. Read before you click: you cannot "
                "see the page otherwise, and the coordinates for `jarvis_browser_click` come from "
                "`jarvis_browser_screenshot`."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_id": _TAB,
                    "max_chars": _nr("Cap on returned characters (default 24000)."),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_click",
            "description": (
                "Click at viewport coordinates (x, y) in Jarvis' desk browser. Coordinates come "
                "from `jarvis_browser_screenshot` — take one first, then click. Returns "
                "{clicked, x, y}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x": _nr("X in viewport pixels."),
                    "y": _nr("Y in viewport pixels."),
                    "tab_id": _TAB,
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_type",
            "description": (
                "Type text into the focused element in Jarvis' desk browser. Click the field "
                "first. Returns {typed, length}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type."},
                    "tab_id": _TAB,
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_screenshot",
            "description": (
                "Take a PNG screenshot of the page in Jarvis' desk browser. Returns "
                "{image_base64, format}. Use it to actually LOOK at the page — for layout, "
                "images and anything `jarvis_browser_read` cannot express — and to find the "
                "coordinates for `jarvis_browser_click`."
            ),
            "parameters": {"type": "object", "properties": {"tab_id": _TAB}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_tabs",
            "description": "List the open tabs in Jarvis' desk browser and which is active. Returns {tabs, aktiv, antal, synlig}. Call it first if you are unsure whether the browser is open.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_browser_close",
            "description": "Close one tab in Jarvis' desk browser by id. Returns {closed}.",
            "parameters": {
                "type": "object",
                "properties": {"tab_id": _nr("Tab id to close (required).")},
                "required": ["tab_id"],
            },
        },
    },
]

DESK_BROWSER_TOOL_HANDLERS = {
    "jarvis_browser_open": _exec_jarvis_browser_open,
    "jarvis_browser_navigate": _exec_jarvis_browser_navigate,
    "jarvis_browser_read": _exec_jarvis_browser_read,
    "jarvis_browser_click": _exec_jarvis_browser_click,
    "jarvis_browser_type": _exec_jarvis_browser_type,
    "jarvis_browser_screenshot": _exec_jarvis_browser_screenshot,
    "jarvis_browser_tabs": _exec_jarvis_browser_tabs,
    "jarvis_browser_close": _exec_jarvis_browser_close,
}

#: Navnene ét sted, saa scoping-lister og pruning ikke kan komme ud af trit.
DESK_BROWSER_TOOL_NAMES: tuple[str, ...] = tuple(DESK_BROWSER_TOOL_HANDLERS)
