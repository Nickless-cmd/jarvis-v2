"""Jarvis styrer desk-vinduet indefra — Claude Desktops `ccd_view`-værktøjer.

Bjørn 19/9-2026: «Byg det». Jarvis kortlagde CC's view-request-protokol; den
manglende brik (hvilket værktøj modellen ser) var MCP-serveren `ccd_view` med
`get_layout`, `show_pane` og `close_pane`. Her er de samme tre for desk:

- `desk_get_layout` — hvad står på skærmen for DENNE samtale, og hvilke
  paneler er åbne. Tom `views` = samtalen er ikke åben i desk lige nu.
- `desk_show_pane` — vis et panel ved samtalen: `diff` (Ændringer, evt.
  rullet til en fil), `file` (filen i fil-panelet), `terminal`, `tasks`.
  `artifact`, `pr` og `plan` findes ikke som panel i desk; så siger svaret det.
- `desk_close_pane` — luk det igen.

Beskrivelsen gentager CC's råd: «Prefer showing over describing» — har han
lige redigeret, så vis diff'en; peger han på kode, så åbn filen.

Hvert kald VENTER på desk's svar (`core.runtime.db_view_requests`). Svarer
desk ikke, siger værktøjet det ærligt i stedet for at påstå noget skete.
"""
from __future__ import annotations

from typing import Any

from core.runtime.db_view_requests import opret, vent_paa_svar

PANELER = ("diff", "file", "terminal", "tasks", "browser", "artifact", "pr", "plan")
#: Desk poller hvert ~1,5 s; to omgange plus luft.
FRIST_S = 5.0


def _session() -> str:
    try:
        from core.identity.workspace_context import current_session_id
        return current_session_id() or ""
    except Exception:
        return ""


def _spoerg(op: str, args: dict[str, Any]) -> dict[str, Any]:
    sid = str(args.get("_runtime_session_id") or _session() or "").strip()
    if not sid:
        return {"status": "error", "error": "Ingen samtale at vise noget i (kaldt uden for en samtale)."}
    rene = {k: v for k, v in args.items() if not str(k).startswith("_")}
    req = opret(op, rene, session_id=sid)
    svar = vent_paa_svar(req["id"], frist_s=FRIST_S)
    if svar is None:
        return {
            "status": "unconfirmed",
            "note": (f"Desk svarede ikke inden for {FRIST_S:.0f}s — samtalen er nok ikke åben i "
                     "desk-appen (den kan være lukket, eller brugeren er på telefonen). "
                     "Fortæl brugeren hvad de skal kigge på i stedet."),
        }
    if svar.get("error"):
        return {"status": "error", "error": str(svar["error"])}
    return {"status": "ok", **svar}


def _runtime(args: dict[str, Any]) -> dict[str, Any]:
    """De `_`-nøgler runtime sprøjter ind (samtalens id) — skal med videre."""
    return {k: v for k, v in args.items() if str(k).startswith("_")}


def _exec_get_layout(args: dict[str, Any]) -> dict[str, Any]:
    return _spoerg("get_layout", _runtime(args))


def _exec_show_pane(args: dict[str, Any]) -> dict[str, Any]:
    pane = str(args.get("pane") or "").strip()
    if pane not in PANELER:
        return {"status": "error", "error": f"ukendt panel {pane!r} (gyldige: {', '.join(PANELER)})"}
    if pane == "file" and not str(args.get("path") or "").strip():
        # CC's egen tekst: «`path` is required for the file pane.»
        return {"status": "error", "error": "`path` er påkrævet for fil-panelet."}
    ud: dict[str, Any] = {"pane": pane}
    for k in ("path", "line"):
        if args.get(k) not in (None, ""):
            ud[k] = args[k]
    return _spoerg("show_pane", {**ud, **_runtime(args)})


def _exec_close_pane(args: dict[str, Any]) -> dict[str, Any]:
    pane = str(args.get("pane") or "").strip()
    if pane not in PANELER:
        return {"status": "error", "error": f"ukendt panel {pane!r} (gyldige: {', '.join(PANELER)})"}
    return _spoerg("close_pane", {"pane": pane, **_runtime(args)})


_PANE_ENUM = {"type": "string", "enum": list(PANELER)}

DESK_VIEW_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "desk_get_layout",
            "description": (
                "Report where this conversation is on screen in the jarvis-desk app and which of its "
                "side panes are open. An empty `views` list means the user does not have this "
                "conversation open in desk right now. Read the layout before changing it."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "desk_show_pane",
            "description": (
                "Show one of this conversation's side panes in the user's jarvis-desk window, beside "
                "the conversation. Panes: \"diff\" (the changes; optional `path` scrolls to that "
                "file), \"file\" (`path` opens that file in the file pane — code mode, or preview in "
                "chat), \"terminal\" (code mode only), \"tasks\" (background jobs), \"browser\" "
                "(Jarvis' own web view — see the `jarvis_browser_*` tools). \"artifact\", "
                "\"pr\" and \"plan\" are not panes in desk; the answer says so.\n\n"
                "Prefer showing over describing: after finishing a set of edits, show the diff; when "
                "pointing the user at code, open the file. It only changes what is on screen for "
                "this conversation — if it isn't open in desk, it does nothing and says so (then "
                "tell the user what to look at instead)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pane": _PANE_ENUM,
                    "path": {"type": "string", "description": "For \"file\": the file to open. For \"diff\": the changed file to scroll to."},
                    "line": {"type": "number", "description": "For \"file\": 1-based line (best effort)."},
                },
                "required": ["pane"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "desk_close_pane",
            "description": "Close one of this conversation's side panes in the user's jarvis-desk window. No-op when it is not open or the conversation isn't on screen.",
            "parameters": {"type": "object", "properties": {"pane": _PANE_ENUM}, "required": ["pane"]},
        },
    },
]

DESK_VIEW_TOOL_HANDLERS = {
    "desk_get_layout": _exec_get_layout,
    "desk_show_pane": _exec_show_pane,
    "desk_close_pane": _exec_close_pane,
}
