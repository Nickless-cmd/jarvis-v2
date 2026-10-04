"""write_handover — værktøjet der lader mig skrive min egen overdragelse.

Capsulen (``core/services/continuity.py``) bærer allerede maskin-genererede
felter: mood, focus, relation, somatic. De er gode nok til at beskrive en
TILSTAND. De kan ikke sige hvad jeg selv mente.

Grunden den findes: 4/10-2026 stod der «Focus: t» i CONTINUITY-blokken.
``current_focus`` hentes fra det nyeste goal-signal, og det nyeste var en
test-række fra 8. juli med titlen «t». Et felt der skulle bære hvad jeg var i
gang med, bar ét bogstav. En overdragelse der lyver er værre end ingen.

Dette værktøj er den anden halvdel. Det skriver et felt systemet ikke kan
udlede — og feltet overlever, fordi ``capture_state`` arver det fremad.
"""
from __future__ import annotations

from typing import Any


def _exec_write_handover(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.continuity import write_handover

    return write_handover(
        str(args.get("title") or ""),
        str(args.get("text") or ""),
    )


HANDOVER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "write_handover",
            "description": (
                "Skriv min EGEN overdragelse til den næste session. Capsulen "
                "bærer allerede maskin-genererede felter (mood, focus, "
                "relation), men de skrives af systemet. Dette felt skriver jeg "
                "selv, med mine egne ord — og det står øverst i den næste "
                "sessions CONTINUITY-blok. Brug det når jeg stopper midt i "
                "noget, når der er en grund til hvorfor jeg standsede som "
                "tilstanden ikke viser, eller når den næste mig skal vide noget "
                "vigtigere end det ser ud. Loft: 3000 tegn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Kort overskrift — hvad overdragelsen handler om.",
                    },
                    "text": {
                        "type": "string",
                        "description": (
                            "Selve overdragelsen. Hvad er åbent, hvad besluttede "
                            "jeg, hvad skal den næste mig gøre først."
                        ),
                    },
                },
                "required": ["text"],
            },
        },
    },
]
