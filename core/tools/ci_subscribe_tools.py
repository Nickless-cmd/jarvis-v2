"""CI-abonnement — «sig til når DENNE kørsel er afgjort».

Hullet, målt 24/11-2026: vagtposten (`ci_status_watch`) kunne kun melde det der
gik GALT (`conclusion not in _ROEDE: continue`). Men det jeg venter på efter et
push er næsten altid en **grøn** kørsel — og den var usynlig. Prisen blev målt
samme dag: jeg pollede `gh run list` i hånden to gange, 7-14 forsøg pr. gang,
for at se noget systemet allerede kunne se.

Det er samme fejlklasse som vagtposten selv blev bygget for at fjerne:
beskyttelsen var en vane («husk at tjekke CI efter push»), ikke en mekanisme.
Et abonnement gør ventetiden til noget systemet bærer.

**Abonnementet er en forventning, ikke en alarm.** Derfor kildetypen `ci_svar`
og ikke `ci_alarm`: en grøn kørsel er ikke en fejl. Men posten kan vække —
ellers ville svaret stå stille til næste hjerteslag, og så var der ingen gevinst
over at polle i hånden.

**Det udløber.** Et workflow der ikke blev trigget, en SHA der ikke findes, eller
Actions der er nede må ikke holde et abonnement i live for evigt: det ville
både love et svar der aldrig kommer og spise rate-limit-budgettet. Efter 30
minutter indfries det med udfaldet `intet_run`, som siger netop det.
"""
from __future__ import annotations

from typing import Any

from core.services import ci_status_watch


def _exec_ci_vent_paa(args: dict[str, Any]) -> dict[str, Any]:
    sha = args.get("sha")
    if not isinstance(sha, str) or not sha.strip():
        return {
            "status": "error",
            "error": (
                "ci_vent_paa: 'sha' er påkrævet — commit-SHA'en du venter på. "
                "En forkortet SHA på mindst 7 tegn accepteres."
            ),
        }
    try:
        svar = ci_status_watch.abonner(
            sha,
            note=str(args.get("note") or ""),
            workflow=str(args.get("workflow") or ""),
        )
    except ValueError as exc:  # ugyldig SHA — fejlen ER svaret
        return {"status": "error", "error": str(exc)}
    return {
        **svar,
        "besked": (
            f"Venter på {svar['sha'][:9]}. Du bliver vækket når kørslen er "
            "afgjort — grøn eller rød — eller efter 30 minutter hvis der "
            "aldrig kom en kørsel. Poll ikke selv imens."
        ),
    }


def _exec_ci_venter(args: dict[str, Any]) -> dict[str, Any]:
    aktive = ci_status_watch._abonnementer()
    if not aktive:
        return {"status": "ok", "antal": 0, "venter": []}
    return {
        "status": "ok",
        "antal": len(aktive),
        "venter": [
            {
                "sha": sha[:9],
                "oprettet": meta.get("oprettet"),
                "note": meta.get("note") or "",
                "workflow": meta.get("workflow") or "",
            }
            for sha, meta in aktive.items()
        ],
    }


CI_SUBSCRIBE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "ci_vent_paa",
            "description": (
                "Abonnér på en CI-kørsel: bliv vækket når den er afgjort, uanset "
                "om den er grøn eller rød. Brug den i stedet for at polle selv — "
                "ventetiden bliver båret af systemet, ikke af gentagne kald. "
                "Udløber efter 30 minutter hvis der aldrig kom en kørsel."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sha": {
                        "type": "string",
                        "description": (
                            "Commit-SHA'en du venter på. Mindst 7 tegn."
                        ),
                    },
                    "note": {
                        "type": "string",
                        "description": (
                            "Kort note om HVAD du venter på — den følger med "
                            "svaret, så du ved hvad kørslen gjaldt."
                        ),
                    },
                    "workflow": {
                        "type": "string",
                        "description": (
                            "Valgfrit: filtrér på workflow-navn eller -sti "
                            "(fx 'ci' eller 'desk-release'). Tom = alle "
                            "kørsler for SHA'en."
                        ),
                    },
                },
                "required": ["sha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ci_venter",
            "description": (
                "Vis hvilke CI-abonnementer der venter lige nu. Brug den når du "
                "vil vide om et svar allerede er på vej, før du sætter et nyt."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


CI_SUBSCRIBE_TOOL_HANDLERS: dict[str, Any] = {
    "ci_vent_paa": _exec_ci_vent_paa,
    "ci_venter": _exec_ci_venter,
}
