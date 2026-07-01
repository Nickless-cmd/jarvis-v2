"""core/services/eventbus_central_bridge.py

KEYSTONE — poll-broen fra eventbus → Centralen (spec §23.3 #1, M0-fundamentet).

I dag er ~980 ``event_bus.publish()``-kald dead-letter for Centralen: INGEN nerve
poller nogen family. Denne bro konverterer hvidlistede families til ``central().observe``
så Centralen for FØRSTE gang ser den operationelle event-strøm.

BINDENDE DESIGN (spec §24):
  * §24.1 — POLL, ikke push. Vi poller ``event_bus.recent_since_id(last_seen_id)`` og
    router. Idempotent via ``last_seen_id`` i shared_cache. Broen subscriber IKKE
    (undgår dobbelt-indtag).
  * §24.5 — router ALDRIG ``central.*`` (rekursions-guard).
  * §24.6 — kill-switch = ``central_switches.is_enabled("nerve", "eventbus_bridge")``.
  * §24.3 — observe-fejl sluges IKKE stille: de tælles og observes som
    ``system/bridge_observe_failures`` (ellers lærer systemet på tomt signal).

M0-INVARIANTER (§24.3 — HARDKODEDE, ikke config, config kan drifte):
  * OBSERVE-ONLY. Ingen læring, ingen threshold-justering, ingen heling, ingen mutation
    findes i denne fil. Broen aflæser og melder — punktum.
  * ALLOWLIST, ikke denylist (``FAMILY_ROUTES``): kun eksplicit hvidlistede OPERATIONELLE
    families routes. Alt andet er default-skip → intet kan lække ved et uheld.
  * §24.4 — PRIVATLAGS-ISOLATION: inner-life/private families (inner_voice, dreams,
    private_brain, cognitive_state, self_critique, ...) er BEVIDST UDELADT af allowlisten
    i M0. De kræver PRIVATE_NO_EGRESS-isolation (egen senere fase) og forbliver dark til da.
  * Kun EVENT-METADATA (id/kind/family) forwardes til observe — ALDRIG event-payload.
    Payloads på operationelle families (channel.*/tool.*) kan indeholde brugerindhold;
    det holdes ude af trace, så en senere trace→eventbus-publicering ikke kan lække det.
"""
from __future__ import annotations

from typing import Any

from core.eventbus.bus import event_bus
from core.services import central_timeseries, shared_cache
from core.services.central_core import central

# ── Allowlist: family → (cluster, nerve). KUN operationelle, ikke-private families. ──
# Bevidst konservativ i M0. Nye families tilføjes eksplicit her, aldrig via denylist.
FAMILY_ROUTES: dict[str, tuple[str, str]] = {
    "runtime": ("loop", "lifecycle"),
    "tool": ("tools", "event"),
    "approvals": ("tools", "approval"),
    "cost": ("cost", "ledger"),
    "cache": ("cost", "prefix_cache"),
    "council": ("agents", "council"),
    "channel": ("channel", "delivery"),
    "anomaly": ("system", "anomaly"),
    "stream": ("stream", "event"),
    "heartbeat": ("system", "heartbeat"),
}

# Dokumenteret liste over families der BEVIDST holdes dark i M0 (privatlags-isolation,
# §24.4). Ikke brugt til routing (allowlisten afgør alt) — men gør intentionen eksplicit
# og testbar: ingen af disse må nogensinde optræde i FAMILY_ROUTES uden PRIVATE_NO_EGRESS.
PRIVATE_FAMILIES_EXCLUDED_M0: frozenset[str] = frozenset({
    "inner_voice", "dreams", "dream_consolidation", "witness", "creative_impulse",
    "prompt_evolution", "self_critique", "meta_learning", "private_brain", "impulse",
    "pressure", "emergent_signal", "cognitive_counterfactual", "cognitive_state",
    "thought_stream", "memory", "consolidation", "selective_consolidation",
})

_BRIDGE_NERVE = "eventbus_bridge"
_LAST_SEEN_KEY = "central:eventbus_bridge:last_seen_id"
_LAST_SEEN_TTL = 86400.0  # 24t; udløber broen >24t nede → re-seed fra nuværende max (springer
                          # backlog over — sikrere end at replaye hele historikken).
_BATCH_LIMIT = 200
_MAX_BATCHES_PER_TICK = 20  # loft: max 4000 events/tick, så ét tick aldrig hænger loopet.


def _get_last_seen() -> int | None:
    try:
        val = shared_cache.get(_LAST_SEEN_KEY)
        if isinstance(val, dict) and "id" in val:
            return int(val["id"])
        if val is not None:
            return int(val)
    except Exception:
        pass
    return None


def _set_last_seen(event_id: int) -> None:
    try:
        shared_cache.set(_LAST_SEEN_KEY, {"id": int(event_id)}, ttl_seconds=_LAST_SEEN_TTL)
    except Exception:
        pass


def _current_max_id() -> int:
    try:
        rows = event_bus.recent(limit=1)
        if rows:
            return int(rows[0].get("id") or 0)
    except Exception:
        pass
    return 0


def _observe_one(cluster: str, nerve: str, ev: dict[str, Any]) -> bool:
    """Meld ét event til Centralen (metadata-only) + registrér i per-nerve tidsserie.

    Returnerer False ved fejl (så kalderen kan tælle — vi sluger IKKE stille, §24.3)."""
    try:
        central().observe({
            "cluster": cluster,
            "nerve": nerve,
            "kind": "observe",
            "event_id": ev.get("id"),
            "event_kind": ev.get("kind"),
            "family": ev.get("family"),
        })
        central_timeseries.record(cluster, nerve, value=1.0, meta={"kind": ev.get("kind")})
        return True
    except Exception:
        return False


def _observe_failure_summary(count: int) -> None:
    """Meld observe-fejl som en synlig nerve — ALDRIG stille sluge (§24.3)."""
    try:
        central().observe({
            "cluster": "system",
            "nerve": "bridge_observe_failures",
            "kind": "error",
            "count": int(count),
        })
        central_timeseries.record("system", "bridge_observe_failures", value=float(count))
    except Exception:
        pass


def run_bridge_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Ét poll-tick: læs nye events siden last_seen_id, router hvidlistede → observe.

    Kaldes af cadence-laget. Observe-only, kaster aldrig, idempotent via last_seen_id.
    """
    # Kill-switch (§24.6). is_enabled fail-open'er til ON ved cache-fejl (sikkert: broen
    # er observe-only, så "kør" er den sikre default; kun eksplicit disable stopper den).
    try:
        from core.services.central_switches import is_enabled
        if not is_enabled("nerve", _BRIDGE_NERVE):
            return {"status": "skipped", "reason": "killswitch"}
    except Exception:
        pass

    last_seen = _get_last_seen()
    if last_seen is None:
        # Kold start: seed fra nuværende max-id, behandl INTET (spring eksisterende
        # backlog over — vi vil ikke re-observe hele historikken ved første opstart).
        seed = _current_max_id()
        _set_last_seen(seed)
        return {"status": "ok", "seeded": seed, "observed": 0, "note": "cold-start-seed"}

    observed = 0
    skipped = 0
    failures = 0
    batches = 0
    max_id = last_seen

    while batches < _MAX_BATCHES_PER_TICK:
        try:
            rows = event_bus.recent_since_id(max_id, limit=_BATCH_LIMIT)
        except Exception:
            break
        if not rows:
            break
        batches += 1
        for ev in rows:
            try:
                eid = int(ev.get("id") or 0)
            except Exception:
                eid = 0
            if eid > max_id:
                max_id = eid
            family = str(ev.get("family") or "")
            if family == "central":  # rekursions-guard (§24.5)
                skipped += 1
                continue
            route = FAMILY_ROUTES.get(family)
            if route is None:  # allowlist: alt ikke-hvidlistet (inkl. private) skippes
                skipped += 1
                continue
            cluster, nerve = route
            if _observe_one(cluster, nerve, ev):
                observed += 1
            else:
                failures += 1
        if len(rows) < _BATCH_LIMIT:
            break

    _set_last_seen(max_id)
    if failures:
        _observe_failure_summary(failures)

    return {
        "status": "ok",
        "observed": observed,
        "skipped": skipped,
        "failures": failures,
        "batches": batches,
        "last_seen_id": max_id,
    }


def register_bridge_producer() -> None:
    """Registrér broen som cadence-producer (poll ~hvert 30s). Observe-only → ingen
    visible-grace nødvendig (ingen LLM, kolliderer ikke med den synlige lane)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="eventbus_central_bridge",
        cooldown_minutes=0.5,
        visible_grace_minutes=0,
        run_fn=run_bridge_tick,
        priority=2,
    ))
