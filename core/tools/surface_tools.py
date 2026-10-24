"""`vaelg_flade` — fladebeslutningen, truffet før formuleringen.

Reglen om at vælge flade efter læseopgaven stod i system-prompten og blev ikke
brugt: `vis_graf` var kaldt tre gange i hele runtime'ens levetid, mod 51.215
`bash`-kald. Årsagen var ikke at reglen var uklar, men at den skulle huskes midt
i formuleringen — langt fra det sted hvor valget træffes.

Dette værktøj flytter beslutningen ind i tool-skemaet, hvor den ses hver tur.
Det er DeepSeek-harnessens lærdom målt 24/10-2026: otte af ni kort-typer blev
fremkaldt gennem vores eget endpoint uden ét ord om formatering i deres
system-prompt, fordi værktøjerne erklærede deres egen visning.

Værktøjet tegner intet. Modellen leverer læseopgaven; runtime ejer tærsklerne
(`surface_for_reading_task`) og vokabularet. Svaret bærer sin egen begrundelse,
så modellen kan rette sin vurdering frem for at gætte hvorfor den fik nej.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _as_int(value: Any) -> int:
    """Negative og ikke-numeriske tal betyder «ved det ikke», ikke en fejl."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):  # «ved det ikke» er et gyldigt svar, ikke en fejl at logge
        return 0


def _exec_vaelg_flade(args: dict[str, Any]) -> dict[str, Any]:
    """Afgør fladen. Kaster aldrig — en fejl her må ikke vælte turen."""
    from core.services.chat_response_policy import decide_surface

    try:
        dom = decide_surface(
            str(args.get("opgave") or ""),
            item_count=_as_int(args.get("antal")),
            shared_dimensions=_as_int(args.get("delte_akser")),
            already_rendered=bool(args.get("allerede_vist") or False),
        )
    except Exception as exc:  # uventet fejl i beslutningen må ikke stoppe svaret
        logger.warning("vaelg_flade: kunne ikke afgoere", exc_info=True)
        return {
            "status": "error",
            "error": f"kunne ikke afgøre fladen: {str(exc)[:120]}",
        }

    valg = dom.get("flade") or dom.get("vaerktoej") or "prosa"
    return {
        "status": "ok",
        "valg": valg,
        "flade": dom.get("flade"),
        "vaerktoej": dom.get("vaerktoej"),
        # Teksten er til HAM, ikke til brugeren: den siger hvad valget blev og
        # hvorfor, så han ikke skal gætte — og ikke nævner kaldet i svaret.
        "text": (
            f"Valg: {dom.get('navn')}. {dom.get('reason')}. "
            f"Næste skridt: {dom.get('next')}. "
            "Nævn ikke dette kald i svaret."
        ),
    }


SURFACE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "vaelg_flade",
            "description": (
                "Decide whether a reply needs a visual surface, BEFORE writing it. "
                "Call this when the answer could contain a comparison, an ordered sequence, "
                "a set of numbers, a choice between options, or a structure. It returns prose, "
                "one native jarvis-ui surface, or one drawing tool — with the reason. "
                "It draws nothing itself. Do not mention the call in the reply."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "opgave": {
                        "type": "string",
                        "enum": [
                            "none",
                            "compare",
                            "sequence",
                            "scan_numbers",
                            "choose",
                            "locate",
                            "warn",
                            "numbers",
                            "flow",
                            "interactive",
                        ],
                        "description": (
                            "none = a plain answer needs no surface. compare = several things on "
                            "shared axes. sequence = ordered steps. scan_numbers = independent key "
                            "figures. choose = actionable options. locate = a concrete place. "
                            "warn = exactly one risk. numbers = figures whose SHAPE is the point "
                            "(a trend, a before/after). flow = structure or process. interactive = "
                            "the reader must click, sort or calculate."
                        ),
                    },
                    "antal": {
                        "type": "integer",
                        "description": "How many items the reading task covers.",
                    },
                    "delte_akser": {
                        "type": "integer",
                        "description": "For compare: how many dimensions the items genuinely share.",
                    },
                    "allerede_vist": {
                        "type": "boolean",
                        "description": "True when the content is already shown on a surface.",
                    },
                },
                "required": ["opgave"],
            },
        },
    },
]
