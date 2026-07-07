"""Core-infra cadence producers (split from internal_cadence.py).

Behavior-preserving extraction (Boy Scout rule): the producer registration
bodies live here, called in unchanged order by
``internal_cadence._ensure_producers_registered``.

This group: brain continuity, cognitive-state warmer, gate-verdict flush,
API-connection retention, excess-sense, keymaker.
"""
from __future__ import annotations

from typing import Callable

# ProducerSpec is re-exported by internal_cadence; import from source to avoid
# a circular dependency at module import time.
from core.services.internal_cadence import ProducerSpec


def register_core_producers(register_producer: Callable[[ProducerSpec], None]) -> None:
    """Register the core-infra producers (unchanged order/timing)."""

    # Brain continuity motor
    def _run_brain_continuity(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.session_distillation import (
            run_private_brain_continuity,
        )
        return run_private_brain_continuity(trigger=trigger)

    register_producer(ProducerSpec(
        name="brain_continuity",
        cooldown_minutes=5,
        visible_grace_minutes=0,  # brain continuity has no visible grace
        run_fn=_run_brain_continuity,
        priority=1,  # runs first — others may depend on its output
    ))

    # Cognitive-state warmer (#2, 2026-06-30): pre-byg cognitive_state-cachen i
    # baggrunden hvert ~3 min, så den ENE dominante blokerende LLM-omkostning
    # (recall_for_message) betales HER i stedet for synkront under prompt assembly.
    # force=True → bygger frisk uden cache-gap (gammel cache serveres til ny er sat).
    # Visible-turen rammer så altid en varm cache (0 blokerende LLM). Den tilstands-
    # bevidste invalidering sikrer at den fanger ægte indre-liv-skift uafhængigt.
    def _run_cognitive_state_warm(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        warmed = 0
        try:
            from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
            for _compact in (False, True):
                try:
                    if build_cognitive_state_for_prompt(compact=_compact, force=True) is not None:
                        warmed += 1
                except Exception:
                    pass
        except Exception:
            pass
        return {"warmed": warmed}

    register_producer(ProducerSpec(
        name="cognitive_state_warm",
        cooldown_minutes=3,
        visible_grace_minutes=0,  # kører uanset visible — varm cache ER pointen (lokal lane, kolliderer ikke med deepseek-visible)
        run_fn=_run_cognitive_state_warm,
        priority=2,
    ))

    # Gate-verdict-ledger flush (6. jul): central().decide akkumulerer verdicts in-memory pr.
    # kald; her batch-flushes de til den persistente gate_verdict_counts-tabel ~hvert minut, så
    # verdict-fordelingen (ground-truth til shadow→enforce-flip) OVERLEVER genstart. Ren lokal
    # DB-skriv — ingen LLM, kører uanset visible. Selv-sikker (flush sluger egne fejl).
    def _run_gate_verdict_flush(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services import gate_verdict_ledger
        return {"flushed": gate_verdict_ledger.flush()}

    register_producer(ProducerSpec(
        name="gate_verdict_flush",
        cooldown_minutes=1,
        visible_grace_minutes=0,
        run_fn=_run_gate_verdict_flush,
        priority=2,
    ))

    # API-forbindelses-nerve GDPR-retention (6. jul): backstop der anonymiserer fuld IP → /24
    # efter 48t + sletter gammel log + pruner presence. Proces-agnostisk DB-arbejde (virker uanset
    # at bufferen ejes af api-processen — retention rammer den delte DB). ~hvert 30. min.
    def _run_api_conn_retention(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.api_connection_nerve import flush, retention_sweep
        flush()
        return {"retention": retention_sweep()}

    register_producer(ProducerSpec(
        name="api_conn_retention",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=_run_api_conn_retention,
        priority=3,
    ))

    # Excess-sans / gartner-muskel (6. jul): Centralen MÆRKER sin egen vægt (bloat) → observerer
    # pres til nerve system/excess så tyngden bliver FØLT over tid. Kun den billige fil-scan i
    # cadence (dead-function-scan er on-demand via /central/excess?propose=1). ~hvert 60. min.
    def _run_excess_sense(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_excess import record_excess_pressure
        s = record_excess_pressure()
        return {"pressure": s.get("pressure", 0)}

    register_producer(ProducerSpec(
        name="excess_sense",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=_run_excess_sense,
        priority=4,
    ))

    # The Keymaker (6. jul, tema #4): optjent/udløbende autonomi. Hver cyklus tjekker (1) om en
    # dimension har OPTJENT en nøgle (track-record over tærskel → PENDING, venter på owner-ja) og
    # (2) om godkendte nøgler er UDLØBET → reverter deres flag (tilladelse mistes hvis ikke fornyet,
    # ingen permanent privilege-crawl). Genererer ALDRIG adgang selv — kun pending + auto-expire.
    def _run_keymaker(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_keymaker import evaluate_keys, expire_due
        ev = evaluate_keys()
        ex = expire_due()
        return {"issued": len(ev.get("issued", [])), "expired": ex.get("expired", 0)}

    register_producer(ProducerSpec(
        name="keymaker",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=_run_keymaker,
        priority=4,
    ))
