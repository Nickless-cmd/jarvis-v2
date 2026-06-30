"""request_app_action tool (spec 2026-06-15) — Jarvis foreslår mode/permission-skift.
   open_ui_panel tool (spec 2026-06-16) — workstation-support med scope-parameter.

Jarvis kan IKKE skifte appens tilstand selv. Dette tool *anmoder* kun: handleren
returnerer en `app_action`-markør i sit resultat, og visible_runs emitterer et
inline `app_action_request` system-event som jarvis-desk renderer som et
godkendelseskort. Kun brugerens klik skifter mode/permission. Backendens
permission_engine håndhæver stadig hvad brugeren faktisk må efter skiftet.
"""
from __future__ import annotations

from typing import Any

VALID_APP_ACTIONS: tuple[str, ...] = ("switch_to_code_mode", "request_full_access")
VALID_PANEL_ACTIONS: tuple[str, ...] = ("open", "close")
VALID_PANELS: tuple[str, ...] = ("preview", "right", "files", "file_tree", "settings")
VALID_SCOPES: tuple[str, ...] = ("repo", "workstation")

_ACTION_NOTE: dict[str, str] = {
    "switch_to_code_mode": "Jeg har bedt appen om at skifte til code mode. Godkend kortet i appen, så fortsætter jeg opgaven dér.",
    "request_full_access": "Jeg har bedt om fuld adgang (trust) til denne opgave. Godkend kortet i appen.",
}


def _exec_request_app_action(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if action not in VALID_APP_ACTIONS:
        return {
            "status": "error",
            "error": f"ukendt action '{action}' (gyldige: {', '.join(VALID_APP_ACTIONS)})",
        }
    reason = str(args.get("reason") or "").strip()
    return {
        "status": "ok",
        "text": _ACTION_NOTE[action],
        "app_action": {"action": action, "reason": reason},
        # Sikkerhed til Jarvis: når dette resultat returneres, emitterer run-loopet
        # GARANTERET et app_action_request-event til desk (både i first-pass OG
        # agentiske runder, rod-fix 2026-06-30) → kortet vises. Du behøver ikke
        # gætte: request er afsendt. Afslut turen med en kort note + afvent klik.
        "dispatched": True,
        "note": "Anmodning afsendt til desk-appen → godkendelseskort vises hos brugeren.",
    }


def _exec_open_ui_panel(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "open").strip()
    if action not in VALID_PANEL_ACTIONS:
        return {
            "status": "error",
            "error": f"ukendt action '{action}' (gyldige: {', '.join(VALID_PANEL_ACTIONS)})",
        }
    panel = str(args.get("panel") or "").strip()
    if action == "open" and not panel:
        return {"status": "error", "error": "panel er påkrævet når action='open'"}
    if action == "open" and panel not in VALID_PANELS:
        return {
            "status": "error",
            "error": f"ukendt panel '{panel}' (gyldige: {', '.join(VALID_PANELS)})",
        }
    detail = str(args.get("detail") or "").strip()
    scope = str(args.get("scope") or "repo").strip()
    if scope not in VALID_SCOPES:
        return {
            "status": "error",
            "error": f"ukendt scope '{scope}' (gyldige: {', '.join(VALID_SCOPES)})",
        }
    return {
        "status": "ok",
        "text": f"Desk-appen {action} panelet. (Kun synligt i jarvis-desk.)",
        "panel_request": {
            "action": action,
            "panel": panel,
            "detail": detail,
            "scope": scope,
        },
    }


def build_app_action_event(
    result: dict[str, Any] | None,
    *,
    user_message: str,
    session_id: str,
) -> dict[str, Any] | None:
    """Ren helper: hvis et tool-resultat bærer en app_action-markør, byg payloaden
    til et `app_action_request` system-event. Returnér None hvis ingen gyldig markør.

    visible_runs kalder denne efter en tool-eksekvering og yield'er et SSE-event
    med returværdien. Holdes ren (ingen sideeffekt) så den er unit-testbar.
    """
    if not result:
        return None
    app_action = result.get("app_action")
    if not app_action or not isinstance(app_action, dict):
        return None
    return {
        "type": "app_action_request",
        "action": app_action.get("action", ""),
        "reason": app_action.get("reason", ""),
        "original_message": user_message,
        "session_id": session_id,
    }


APP_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "function": {
            "name": "request_app_action",
            "description": "Bed jarvis-desk-appen om at skifte tilstand når den nuværende mode eller permission ikke rækker til opgaven. To handlinger: 'switch_to_code_mode' (fra chat til code mode — giver terminal + fil-adgang) og 'request_full_access' (fra 'spørg' til 'fuld adgang' i code mode). Du skifter ALDRIG selv: tool'et viser brugeren et godkendelseskort, og kun deres klik skifter. Når de godkender, gen-sendes beskeden automatisk så du fortsætter. Virker kun i desk-appen (ikke web/Discord). Kald det når du selv mærker at opgaven kræver mere — og afslut din tur med en kort note om at du afventer godkendelse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(VALID_APP_ACTIONS),
                        "description": "Hvilket skift du anmoder om",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Kort forklaring vist på kortet (fx 'kræver terminal og filer')",
                    },
                },
                "required": ["action"],
            },
        }
    },
    {
        "function": {
            "name": "open_ui_panel",
            "description": "Åbn et panel i jarvis-desk-appen for at vise noget for brugeren: 'preview' (preview-panel), 'right' (højre side-panel), 'files' (fil-træ), 'file_tree' (åbn code-mode fil-træet og HIGHLIGHT en bestemt fil — sæt detail til den repo-relative sti, fx 'core/tools/ui_panel_tools.py', så scroller appen til filen og markerer den). Brug file_tree når brugeren ikke kan finde en fil. VIS EN FIL i preview: panel='preview' + detail=den repo-relative filsti (fx 'docs/spec.md') → appen loader og renderer filen. ÅBN INDSTILLINGER: panel='settings' → appen skifter til cowork og viser indstillingszonen (konto/kvote/tema/permissions m.m.). scope='workstation' for at highlighte i brugerens lokale workspace i stedet for server-repoet. Virker kun i desk-appen (ikke Discord/web). Du behøver ikke spørge om lov — appen åbner panelet for owner. action='close' lukker igen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": list(VALID_PANEL_ACTIONS),
                        "description": "'open' (default) åbner panelet; 'close' lukker det igen",
                    },
                    "panel": {
                        "type": "string",
                        "enum": list(VALID_PANELS),
                        "description": "Hvilket panel der skal åbnes (ved action='open')",
                    },
                    "detail": {
                        "type": "string",
                        "description": "Repository-relativ sti (scope='repo') eller workspace-relativ sti (scope='workstation') til filen der skal highlightes",
                    },
                    "scope": {
                        "type": "string",
                        "enum": list(VALID_SCOPES),
                        "description": "'repo' (default) — highlight i serverens repo. 'workstation' — highlight i brugerens lokale workspace.",
                    },
                },
                "required": ["panel"],
            },
        }
    },
]

APP_CONTROL_TOOL_HANDLERS: dict[str, Any] = {
    "request_app_action": _exec_request_app_action,
    "open_ui_panel": _exec_open_ui_panel,
}
