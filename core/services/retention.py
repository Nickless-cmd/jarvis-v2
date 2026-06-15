"""Retention-sweep — bremser ubegrænset vækst på høj-volumen tabeller.

Baggrund (liveness-audit 15. jun): lærings-tabeller voksede ~3k rækker/dag uden
prune (`compact_stale` var forældreløs; `generalized_policies` havde ingen prune).

RØDT PUNKT — dette må ALDRIG slette Jarvis' hukommelse, identitet eller load-bearing
event-substrat. Kun:
  (a) LÆRING — gammelt + beviseligt værdiløst (lav-konfidens / aldrig-matchet).
  (b) TELEMETRI — ren operationel log uden kognitive læsere.
BEVIDST UDELADT (decay via salience/arkivering, IKKE sletning — separat design):
  events (læses af counterfactual/dream_bias/longing/finitude m.fl.), private_brain_*,
  cognitive_* memories, sensory_memories, emotional_memory_anchors, costs (infra_weather).

Selv-throttlende: kører reelt max 1×/24h via runtime_state-tidsstempel, uanset
kald-frekvens. Defensiv: en fejl på én tabel stopper ikke de øvrige; kaster aldrig.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_LAST_RUN_KEY = "retention_sweep_last_run"
_MIN_INTERVAL_HOURS = 24

# Ren age-baseret telemetri-prune (tabel, max_alder_dage). Verificeret: ingen
# kognitive læsere. created_at-kolonne antaget.
_TELEMETRY_POLICIES: list[tuple[str, int]] = [
    ("cheap_provider_invocations", 60),
    ("daemon_output_log", 30),
]


def _should_run(last_run_iso: str | None, now: datetime) -> bool:
    if not last_run_iso:
        return True
    try:
        last = datetime.fromisoformat(str(last_run_iso))
    except Exception:
        return True
    return now - last >= timedelta(hours=_MIN_INTERVAL_HOURS)


def _prune_telemetry(table: str, max_age_days: int, now: datetime) -> int:
    from core.runtime.db import connect
    cutoff = (now - timedelta(days=max_age_days)).isoformat()
    conn = connect()
    try:
        cur = conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def _prune_unmatched_policies(max_age_days: int, now: datetime) -> int:
    """Slet generaliserede principper der ALDRIG har matchet og er >max_age gamle —
    beviseligt værdiløse. Hver policy der nogensinde har matchet bevares."""
    from core.runtime.db import connect
    cutoff = (now - timedelta(days=max_age_days)).isoformat()
    conn = connect()
    try:
        cur = conn.execute(
            "DELETE FROM generalized_policies WHERE match_count = 0 AND created_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def run_retention_sweep(*, force: bool = False, now: datetime | None = None) -> dict[str, object]:
    """Kør retention. Selv-throttlende (max 1×/24h) medmindre force=True."""
    now = now or datetime.now(UTC)
    from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    if not force and not _should_run(get_runtime_state_value(_LAST_RUN_KEY, None), now):
        return {"ran": False, "reason": "cadence"}

    removed: dict[str, int] = {}

    # (a) Læring — genbrug den konservative compact_stale (30d + conf<0.1).
    try:
        from core.services.reasoning_store import compact_stale
        removed["reasoning_conclusions"] = compact_stale()
    except Exception:
        logger.warning("retention: compact_stale fejlede", exc_info=True)

    try:
        removed["generalized_policies"] = _prune_unmatched_policies(30, now)
    except Exception:
        logger.warning("retention: policy-prune fejlede", exc_info=True)

    # (b) Telemetri — ren age-prune.
    for table, age in _TELEMETRY_POLICIES:
        try:
            removed[table] = _prune_telemetry(table, age, now)
        except Exception:
            logger.warning("retention: prune af %s fejlede", table, exc_info=True)

    try:
        set_runtime_state_value(_LAST_RUN_KEY, now.isoformat())
    except Exception:
        pass

    total = sum(removed.values())
    logger.info("retention-sweep: fjernede %d rækker %s", total, removed)
    return {"ran": True, "removed": removed, "total": total}
