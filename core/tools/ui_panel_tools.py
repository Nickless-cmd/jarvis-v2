"""open_ui_panel-tool (spec §8.2, Fase 6 #3).

Lader Jarvis bede desk-appen om at åbne et panel (preview / højre side-panel /
fil-træ) når han vil vise noget. Forespørgslen lægges i ui_panel_store; desk poller
+ åbner. Ren tilføjelse — registreres i simple_tools via UI_PANEL_TOOL_DEFINITIONS/
HANDLERS (samme mønster som de øvrige tool-moduler).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.services.ui_panel_store import request_panel

_PANELS = ("preview", "right", "files", "file_tree")


def _exec_open_ui_panel(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "open").strip().lower()
    if action not in ("open", "close"):
        return {"status": "error", "error": f"ukendt action '{action}' (open/close)"}
    panel = str(args.get("panel") or "preview").strip().lower()
    if action == "open" and panel not in _PANELS:
        return {"status": "error", "error": f"ukendt panel '{panel}' (gyldige: {', '.join(_PANELS)})"}
    detail = str(args.get("detail") or "")
    session_id = str(args.get("session_id") or "")
    rec = request_panel(
        request_id=f"panel-{uuid4().hex[:12]}",
        panel=panel,
        session_id=session_id,
        detail=detail,
        created_at=datetime.now(UTC).isoformat(),
        action=action,
    )
    verb = "lukker" if action == "close" else "åbner"
    return {"status": "ok", "panel": panel, "action": action, "request_id": rec["id"],
            "note": f"Desk-appen {verb} panelet. (Kun synligt i jarvis-desk.)"}


UI_PANEL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_ui_panel",
            "description": (
                "Åbn et panel i jarvis-desk-appen for at vise noget for brugeren: "
                "'preview' (preview-panel), 'right' (højre side-panel), 'files' "
                "(fil-træ) eller 'file_tree' (åbn code-mode fil-træet og HIGHLIGHT en "
                "bestemt fil — sæt detail til den repo-relative sti, fx "
                "'core/tools/ui_panel_tools.py', så scroller appen til filen og "
                "markerer den). Brug file_tree når brugeren ikke kan finde en fil. "
                "Virker kun i desk-appen (ikke Discord/web). Du behøver ikke spørge "
                "om lov — appen åbner panelet for owner. action='close' lukker igen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "close"],
                        "description": "'open' (default) åbner panelet; 'close' lukker det igen",
                    },
                    "panel": {
                        "type": "string",
                        "enum": list(_PANELS),
                        "description": "Hvilket panel der skal åbnes (ved action='open')",
                    },
                    "detail": {
                        "type": "string",
                        "description": "Valgfri kort note om hvad panelet skal vise",
                    },
                },
                "required": [],
            },
        },
    },
]

UI_PANEL_TOOL_HANDLERS: dict[str, Any] = {
    "open_ui_panel": _exec_open_ui_panel,
}
