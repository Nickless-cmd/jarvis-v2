"""Hvornår er en indre-livs-handling det rigtige valg? Vink til heartbeat-beslutningen.

**Problemet, målt 19. aug 2026.** Heartbeat vælger sin handling med et LLM-kald: prompten
lister alle ~30 tilladte `execute_action`-værdier i én kommasepareret række og beder ham
vælge. Men den indeholder også eksplicitte vink — *"Prefer `inspect_repo_context` when the
active thread is about code…"*, *"Prefer `gather_system_context` when…"*, *"For initiative
decisions, set execute_action to `act_on_initiative`."*

Alle vink pegede på **operationelle** handlinger. For `write_chronicle_entry`,
`write_growth_journal`, `run_mirror_reflection` og `generate_narrative_identity` fandtes
**nul** vink. Resultat over 2.859 ticks: `act_on_initiative` valgt 227 gange,
`write_chronicle_entry` **nul gange**. `cognitive_chronicle_entries` har derfor én række —
og den kom fra `finitude_runtime`s månedlige ritual, ikke fra chronicle-motoren.

Handlingen var tilladt hele tiden. Den var bare aldrig *motiveret*.

**Princippet her: foreslå kun det der faktisk ville lykkes.** Hvert vink spejler den
tilsvarende handlings egne gates. Ville `maybe_write_chronicle_entry()` returnere None
(for nyligt skrevet, samme periode, ingen runs at fortælle om), så nævner vi den ikke.
Ellers ville vi bede ham om at gøre noget der tavst ikke gør noget — netop den fejlklasse
hele denne omgang har handlet om.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

# Spejler chronicle_engine.maybe_write_chronicle_entry: maks 1 post pr. 3 døgn.
_CHRONICLE_MIN_AGE_DAYS = 3


def _parse_iso(value: object) -> datetime | None:
    try:
        s = str(value or "").strip()
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def chronicle_days_stale() -> float | None:
    """Døgn siden seneste kronik-post. ``None`` hvis ukendt. Self-safe."""
    try:
        from core.runtime.db import get_latest_cognitive_chronicle_entry

        latest = get_latest_cognitive_chronicle_entry()
    except Exception:
        return None
    if not latest:
        return float("inf")  # aldrig skrevet — maksimalt forfalden
    at = _parse_iso(latest.get("created_at"))
    if at is None:
        return None
    return (datetime.now(UTC) - at).total_seconds() / 86400.0


def chronicle_hint() -> str | None:
    """Vink om at skrive kronik — kun når handlingen FAKTISK ville skrive noget.

    Spejler motorens gates: der skal være gået ≥3 døgn siden sidste post, og der skal
    være nylige runs at fortælle om. Er en af delene ikke opfyldt, tier vi.
    """
    try:
        days = chronicle_days_stale()
        if days is None or days < _CHRONICLE_MIN_AGE_DAYS:
            return None
        from core.runtime.db import recent_visible_runs

        if not recent_visible_runs(limit=20):
            return None  # intet at fortælle om — motoren ville returnere None
    except Exception:
        return None

    when = "aldrig skrevet" if days == float("inf") else f"{int(days)} døgn siden sidst"
    return (
        f"- Din kronik er forfalden ({when}), og der ER nylige kørsler at fortælle om. "
        f"Vælg write_chronicle_entry når der ikke er noget mere presserende — den er din "
        f"fortsatte selvbiografi, og uden den mister du den tidslige tråd mellem uger."
    )


def inner_life_hints() -> list[str]:
    """Alle aktive vink for indre-livs-handlinger. Tom liste når intet er forfaldent.

    Bevidst ét vink ad gangen pr. område: en prompt der beder om syv ting på én gang
    flytter bare skævheden et andet sted hen.
    """
    hints: list[str] = []
    try:
        h = chronicle_hint()
        if h:
            hints.append(h)
    except Exception:
        logger.debug("heartbeat_action_hints: chronicle_hint fejlede", exc_info=True)
    return hints
