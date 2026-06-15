"""request_app_action tool (spec 2026-06-15) — Jarvis foreslår mode/permission-skift.

Jarvis kan IKKE skifte appens tilstand selv. Dette tool *anmoder* kun: handleren
returnerer en `app_action`-markør i sit resultat, og visible_runs emitterer et
inline `app_action_request` system-event som jarvis-desk renderer som et
godkendelseskort. Kun brugerens klik skifter mode/permission. Backendens
permission_engine håndhæver stadig hvad brugeren faktisk må efter skiftet.
"""
from __future__ import annotations

from typing import Any

# De eneste gyldige app-actions (spec: "De to konkrete handlinger").
VALID_APP_ACTIONS: tuple[str, ...] = ("switch_to_code_mode", "request_full_access")

_ACTION_NOTE: dict[str, str] = {
    "switch_to_code_mode": (
        "Jeg har bedt appen om at skifte til code mode. Godkend kortet i appen, "
        "så fortsætter jeg opgaven dér."
    ),
    "request_full_access": (
        "Jeg har bedt om fuld adgang (trust) til denne opgave. Godkend kortet i "
        "appen, så fortsætter jeg."
    ),
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
        "note": "Afventer brugerens godkendelse i appen.",
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
    if not isinstance(result, dict):
        return None
    marker = result.get("app_action")
    if not isinstance(marker, dict):
        return None
    action = str(marker.get("action") or "")
    if action not in VALID_APP_ACTIONS:
        return None
    return {
        "type": "app_action_request",
        "action": action,
        "reason": str(marker.get("reason") or ""),
        "original_message": str(user_message or ""),
        "session_id": str(session_id or ""),
    }


APP_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "request_app_action",
            "description": (
                "Bed jarvis-desk-appen om at skifte tilstand når den nuværende mode "
                "eller permission ikke rækker til opgaven. To handlinger: "
                "'switch_to_code_mode' (fra chat til code mode — giver terminal + "
                "fil-adgang) og 'request_full_access' (fra 'spørg' til 'fuld adgang' "
                "i code mode). Du skifter ALDRIG selv: tool'et viser brugeren et "
                "godkendelseskort, og kun deres klik skifter. Når de godkender, "
                "gen-sendes beskeden automatisk så du fortsætter. Virker kun i "
                "desk-appen (ikke web/Discord). Kald det når du selv mærker at "
                "opgaven kræver mere — og afslut din tur med en kort note om at du "
                "afventer godkendelse."
            ),
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
        },
    },
]

APP_CONTROL_TOOL_HANDLERS: dict[str, Any] = {
    "request_app_action": _exec_request_app_action,
}
