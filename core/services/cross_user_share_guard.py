"""Altid-aktiv deling-guard — stopper Jarvis før han deler info om en ANDEN bruger.

Spec §4.4: når Jarvis er på vej til at dele noget om en anden bruger end sin
nuværende samtalepartner, udløses en guard der stopper ham og spørger *"privat
info, eller okay at dele?"* — uanset mode/rolle/override. En sidste menneskelig-
hensyns-tjek før kryds-bruger-deling (bygger på samme idé som communication_guard).

Ren funktion: `check_outbound(text, current_user_id, known_users)`. Heuristik =
kendte bruger-navne/ids der ≠ nuværende samtalepartner. Fail-safe: ved match →
needs_confirmation=True. Håndhæves i Fase 4 (udgående sti → approval-kort).
"""
from __future__ import annotations

import re

_PROMPT = (
    "Det her nævner en anden bruger ({names}). Er det privat information om dem, "
    "eller er det okay at dele med din nuværende samtalepartner?"
)


def check_outbound(
    text: str,
    *,
    current_user_id: str,
    known_users: list[dict] | None,
) -> dict:
    """Tjek et udgående svar for omtale af andre brugere end samtalepartneren.

    Returnerer {needs_confirmation, mentioned_users, prompt}. `known_users` er
    en liste af {"id", "name"} (fx fra users-registry). Word-boundary + case-
    insensitive match på navn ELLER id; samtalepartnerens eget navn/id ignoreres.
    """
    mentioned: list[str] = []
    if text and known_users:
        lower = text.lower()
        for u in known_users:
            uid = str(u.get("id") or "")
            name = str(u.get("name") or "")
            if uid and uid == current_user_id:
                continue  # samtalepartneren selv — ikke kryds-bruger
            for token in (name, uid):
                if not token:
                    continue
                # Word-boundary (\b virker på unicode-bogstaver i Python re)
                if re.search(rf"\b{re.escape(token.lower())}\b", lower):
                    if name and name not in mentioned:
                        mentioned.append(name)
                    break

    needs = bool(mentioned)
    return {
        "needs_confirmation": needs,
        "mentioned_users": mentioned,
        "prompt": _PROMPT.format(names=", ".join(mentioned)) if needs else "",
    }
