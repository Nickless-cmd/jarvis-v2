"""open_ui_panel-tool (spec §8.2, Fase 6 #3).

Lader Jarvis bede desk-appen om at åbne et panel (preview / højre side-panel /
fil-træ) når han vil vise noget. Forespørgslen lægges i ui_panel_store; desk poller
+ åbner. Ren tilføjelse — registreres i simple_tools via UI_PANEL_TOOL_DEFINITIONS/
HANDLERS (samme mønster som de øvrige tool-moduler).
"""
from __future__ import annotations

from typing import Any

from core.services.ui_panel_store import request_panel

_PANELS = ("preview", "right", "files", "file_tree", "settings")


def _exec_open_ui_panel(args: dict[str, Any]) -> dict[str, Any]:
    # RUNTIME-FIX (2026-06-30): request_panel-signaturen ændredes til
    # request_panel(panel, *, detail, scope, session_id) — den auto-genererer id
    # og har hverken request_id/created_at/action længere. Det gamle kald sendte
    # netop de fjernede kwargs → TypeError → open_ui_panel var BRÆKKET i runtime
    # (ikke kun i test). Brug den nye signatur; 'close' er nu et tool-niveau-signal
    # til desk'en (store'n persisterer kun åbne-forespørgsler).
    action = str(args.get("action") or "open").strip().lower()
    if action not in ("open", "close"):
        return {"status": "error", "error": f"ukendt action '{action}' (open/close)"}
    panel = str(args.get("panel") or "preview").strip().lower()
    if action == "open" and panel not in _PANELS:
        return {"status": "error", "error": f"ukendt panel '{panel}' (gyldige: {', '.join(_PANELS)})"}
    detail = str(args.get("detail") or "")
    session_id = str(args.get("session_id") or "")
    if action == "close":
        # Ingen persisteret panel-request — signalér blot desk'en at lukke.
        return {"status": "ok", "panel": panel, "action": "close",
                "note": "Desk-appen lukker panelet. (Kun synligt i jarvis-desk.)"}
    rec = request_panel(panel, detail=detail, session_id=session_id)
    return {"status": "ok", "panel": panel, "action": "open", "request_id": rec["id"],
            "note": "Desk-appen åbner panelet. (Kun synligt i jarvis-desk.)"}


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
                "VIS EN FIL i preview: panel='preview' + detail=den repo-relative "
                "filsti (fx 'docs/spec.md') → appen loader og renderer filen. "
                "ÅBN INDSTILLINGER: panel='settings' → appen skifter til cowork og "
                "viser indstillingszonen (konto/kvote/tema/permissions m.m.). "
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
