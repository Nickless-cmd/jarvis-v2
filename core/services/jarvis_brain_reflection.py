"""End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte.

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 4.3.

Slot orchestrering:
  1. Once daily (typisk evening transition), check om der var aktivitet i dag
  2. Build chronicle summary
  3. Emit eventbus 'jarvis_brain.reflection_requested' med envelope
  4. Visible Jarvis kører som almindelig tur og kalder remember_this
  5. Slot lytter på reflection_completed event for telemetri
"""
from __future__ import annotations
import logging

logger = logging.getLogger("jarvis_brain_reflection")


_REFLECTION_TEMPLATE = """\
[reflection-slot] Dagen er ved at runde. Her er kort hvad der skete i dag:
{chronicle_summary}

Spørgsmål til dig: Hvad lærte du i dag som er værd at føre ind i din
egen hjerne? Tænk på fakta, indsigter, observationer, eller referencer.
Brug `remember_this` for hver enkelt — eller spring over hvis intet
stikker ud. Du behøver ikke skrive om alt; vælg de 1-3 ting der
virkelig er værd at huske.
"""


def build_reflection_envelope(*, chronicle_summary: str) -> str:
    """Build the envelope text shown to visible Jarvis at end-of-day."""
    return _REFLECTION_TEMPLATE.format(chronicle_summary=chronicle_summary)


def build_internal_nudge(*, count_so_far: int) -> str:
    """Soft nudge after 3+ remember_this calls in same reflection slot.

    Forhindrer at en hallucineret loop fylder hjernen op uden at hard-blocke.
    """
    if count_so_far < 3:
        return ""
    return (
        f"[brain-nudge-internal] Du har nu skrevet {count_so_far} poster "
        f"i dag. Er der mere, eller er du færdig?"
    )


def _was_active_today() -> bool:
    """Best-effort tjek om Jarvis havde aktivitet i dag.

    Spring refleksion over hvis ingen friske begivenheder — refleksion
    uden grundlag bliver fabrication.
    """
    try:
        # Heuristic: check if there are any chat messages today
        from datetime import datetime, timezone
        from core.runtime.db import connect

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM chat_messages WHERE created_at >= ? LIMIT 1",
                (today + "T00:00:00",),
            ).fetchone()
        return row is not None
    except Exception:
        return True  # fail-open: hellere køre end at springe over


def _build_today_chronicle_summary() -> str:
    """Build a short summary of today's chronicle entries.

    Uses the chronicle distillation infrastructure if available;
    otherwise returns a minimal stub.
    """
    try:
        from core.services.chronicle_engine import build_recent_chronicle_summary
        return build_recent_chronicle_summary(hours=24, max_lines=10)
    except Exception:
        return "(chronicle summary unavailable — refleksionen kører på fri hånd)"


def _run_reflection_turn(chronicle_summary: str) -> int:
    """Trigger en visible-Jarvis tur med reflection-envelope.

    V1: emit eventbus-event som visible_runs lytter på. Fuld
    orchestrering kommer i v2 når vi har observeret hvordan Jarvis
    bruger slottet.
    Returnerer antal remember_this rapporteret tilbage (0 i v1).
    """
    try:
        from core.eventbus.events import emit  # type: ignore
        emit(
            "jarvis_brain.reflection_requested",
            {
                "envelope_text": build_reflection_envelope(
                    chronicle_summary=chronicle_summary,
                ),
            },
        )
    except Exception as exc:
        logger.warning("reflection event emit failed: %s", exc)
        return 0
    return 0


def run_daily_reflection_if_active() -> None:
    """Entry point for the daily slot trigger.

    Skipper hvis ingen aktivitet i dag (catch-up = fabrication, ikke refleksion).
    """
    if not _was_active_today():
        logger.info("reflection skipped: no activity today")
        return
    try:
        summary = _build_today_chronicle_summary()
    except Exception as exc:
        logger.warning("could not build chronicle summary: %s", exc)
        return
    _run_reflection_turn(summary)
