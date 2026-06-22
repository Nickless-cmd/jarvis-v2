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

import logging
import re

logger = logging.getLogger(__name__)

_PROMPT = (
    "Det her nævner en anden bruger ({names}). Er det privat information om dem, "
    "eller er det okay at dele med din nuværende samtalepartner?"
)


def check_outbound(
    text: str,
    *,
    current_user_id: str,
    known_users: list[dict] | None,
    session_id: str = "",
) -> dict:
    """Tjek et udgående svar for omtale af andre brugere end samtalepartneren.

    Returnerer {needs_confirmation, mentioned_users, prompt}. `known_users` er
    en liste af {"id", "name"} (fx fra users-registry). Word-boundary + case-
    insensitive match på navn ELLER id; samtalepartnerens eget navn/id ignoreres.

    Teams (spec 2026-06-20): i en delt team-session brugeren er medlem af ER
    cross-user-omtaler tilladt (det er hele pointen) → tidlig retur uden flag.
    """
    if session_id:
        try:
            import core.services.teams as teams
            from core.runtime.db import connect
            with connect() as conn:
                row = conn.execute(
                    "SELECT team_id FROM chat_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
            team_id = row[0] if row and row[0] else None
            if team_id and teams.is_member(team_id, current_user_id):
                return {"needs_confirmation": False, "mentioned_users": [], "prompt": ""}
        except Exception:
            pass  # fail-open til normal guard-logik

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


def check_against_registry(text: str, *, current_user_id: str) -> dict:
    """Som check_outbound, men henter kendte brugere fra users-registry.

    Convenience til udgående wiring (visible_runs): loader alle registrerede
    brugere som {id, name} og tjekker det udgående svar mod dem. Fail-safe: ved
    fejl i registry-load returneres needs_confirmation=False (blokér ikke chat).
    """
    try:
        from core.identity.users import load_users
        known = [{"id": u.discord_id, "name": u.name} for u in load_users()]
    except Exception as exc:
        # FAIL-CLOSED (2026-06-22, Bjørn): hvis bruger-registret IKKE kan loades, kan vi
        # ikke verificere cross-user-sikkerhed → flag til bekræftelse (læk ALDRIG i
        # stilhed). Tidligere fail-OPEN (known=[] → ingen flag) var en potentiel læk.
        logger.warning(
            "cross_user_share registry-load fejlede — fail-CLOSED flag (læk ikke i stilhed): %s",
            exc,
        )
        return {
            "needs_confirmation": True,
            "mentioned_users": [],
            "prompt": ("Kunne ikke verificere cross-user-sikkerhed (bruger-registret kunne "
                       "ikke loades) — bekræft før deling."),
        }
    return check_outbound(text, current_user_id=current_user_id, known_users=known)
