"""Maintenance / health cadence producers (split from internal_cadence.py).

Behavior-preserving extraction (Boy Scout rule): registered in unchanged
order by ``internal_cadence._ensure_producers_registered``.

This group: cache-warmer + reassessment sweeps + health/usage observers
(prompt_assembly_cache_warmer, life_projects_reassessment,
relation_map_refresh, counterfactual_predictions_sweep, shared_cache_cleanup,
central_self_health, central_learning, stream_stall_sweep, config_drift_check,
instrument_scan, provider_health_check, db_health_scan, tool_usage_stats,
endpoint_usage_stats).
"""
from __future__ import annotations

import logging
from typing import Callable

from core.services.internal_cadence import ProducerSpec

logger = logging.getLogger(__name__)


def register_maintenance_producers(register_producer: Callable[[ProducerSpec], None]) -> None:
    """Register the maintenance / health producers (unchanged order/timing)."""

    def _run_prompt_assembly_cache_warmer(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Refresh prompt-assembly section caches in background.

        Strategy: every 2 minutes, invalidate + rebuild both rule_conclusions
        and cognitive_frame caches. This way visible-chat turns always see
        ≤2 min stale data, AND never pay the cold-rebuild cost themselves —
        the heartbeat thread absorbs it.

        Without this: 180s TTL means a turn lands exactly when the cache
        expired pays the full 10s rebuild. With this: cache is always warm
        when visible chat needs it.

        Added 2026-05-12 after instrumentation identified rule_conclusions
        + cognitive_frame as the dominant assembly cost.
        """
        # Logger.info so we can SEE when this fires in journal.
        # Without this, the warmer is invisible because the producer
        # doesn't publish events to the DB. Cheap line, big diagnostic value.
        logger.info("prompt_assembly_cache_warmer: tick fired (trigger=%s)", trigger)

        out: dict[str, object] = {
            "rule_conclusions": "skipped", "cognitive_frame": "skipped",
            "cognitive_state": "skipped",
        }
        try:
            from core.services.prompt_sections.rule_conclusions import (
                invalidate_section_cache, rule_conclusions_section,
            )
            invalidate_section_cache()
            _ = rule_conclusions_section()  # rebuild + cache
            out["rule_conclusions"] = "warmed"
        except Exception as exc:
            out["rule_conclusions"] = f"error: {exc}"
        try:
            from core.services.prompt_contract import (
                invalidate_cognitive_frame_cache, _cognitive_frame_section,
            )
            invalidate_cognitive_frame_cache()
            _ = _cognitive_frame_section()
            out["cognitive_frame"] = "warmed"
        except Exception as exc:
            out["cognitive_frame"] = f"error: {exc}"
        # cognitive_state (~5,5s, SQLite-cachet, TTL 120s) blev IKKE varmet før
        # — den var den dominerende kolde-cache-omkostning i den visible assembly
        # (Bjørn 2026-06-17). Varm den med compact=False (= visible owner-chat-nøglen)
        # så ingen tur betaler kold pris. Friskhed = warmer-kadence (~2 min), uændret.
        try:
            from core.services.cognitive_state_assembly import (
                invalidate_cognitive_state_cache, build_cognitive_state_for_prompt,
            )
            invalidate_cognitive_state_cache()
            _ = build_cognitive_state_for_prompt(compact=False)  # rebuild + cache
            out["cognitive_state"] = "warmed"
        except Exception as exc:
            out["cognitive_state"] = f"error: {exc}"
        logger.info(
            "prompt_assembly_cache_warmer: done rule_conclusions=%s cognitive_frame=%s cognitive_state=%s",
            out["rule_conclusions"], out["cognitive_frame"], out["cognitive_state"],
        )
        return {"status": "ok", **out}

    register_producer(ProducerSpec(
        name="prompt_assembly_cache_warmer",
        cooldown_minutes=2,            # refresh every 2 min (< 3 min TTL)
        visible_grace_minutes=0,       # always run — it's background pre-warm
        run_fn=_run_prompt_assembly_cache_warmer,
        priority=31,
        depends_on=[],
    ))

    def _run_life_projects_reassessment(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        # PENSIONERET 2026-07-15 — cluster_projects (familie #9) overtager
        # life_projects_reassessment som non-LLM medlem (1440min/24t self-throttle).
        # Gate den gamle produceren på is_enabled så den no-op'er når daemonen er
        # pensioneret (undgår dobbelt-eksekvering + reassessment_due-spam med familien).
        try:
            from core.services import daemon_manager as _dm
            if not _dm.is_enabled("life_projects_reassessment"):
                return {"status": "retired", "reason": "cluster_projects overtager"}
        except Exception:
            pass
        from core.services.life_projects import tick_life_projects_reassessment
        return tick_life_projects_reassessment(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="life_projects_reassessment",
        cooldown_minutes=1440,
        visible_grace_minutes=30,
        run_fn=_run_life_projects_reassessment,
        priority=28,
    ))

    def _run_relation_map_refresh(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        # PENSIONERET 2026-07-15 — cluster_relation (familie #8) overtager relation_map
        # som non-LLM medlem. Gate den gamle produceren på is_enabled så den no-op'er
        # når daemonen er pensioneret (undgår dobbelt-eksekvering med familien).
        try:
            from core.services import daemon_manager as _dm
            if not _dm.is_enabled("relation_map_refresh"):
                return {"status": "retired", "reason": "cluster_relation overtager"}
        except Exception:
            pass
        from core.services.relation_map import tick_relation_map_refresh
        return tick_relation_map_refresh(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="relation_map_refresh",
        cooldown_minutes=720,
        visible_grace_minutes=0,
        run_fn=_run_relation_map_refresh,
        priority=30,
    ))

    def _run_counterfactual_predictions_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Counterfactuals Phase 1.5 (2026-05-14) — close the prediction
        resolution loop. Resolves counterfactual-bound predictions whose
        7-day horizon (+1d grace) has passed, marking as 'uncertain' with
        an audit note. Future Phase 2 will replace this with frequency-
        based supported/contradicted assignment."""
        from core.services.counterfactual_predictions import (
            sweep_expired_counterfactual_predictions,
        )
        return sweep_expired_counterfactual_predictions()

    register_producer(ProducerSpec(
        name="counterfactual_predictions_sweep",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_counterfactual_predictions_sweep,
        priority=35,
    ))

    def _run_shared_cache_cleanup(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Sweep expired rows from shared_cache (2026-05-14).

        shared_cache lazy-expires individual entries on read, but rows
        written and never read again would linger. Hourly cleanup keeps
        the table tight."""
        from core.services.shared_cache import cleanup_expired, stats
        deleted = cleanup_expired()
        return {"status": "ok", "deleted": deleted, **stats()}

    register_producer(ProducerSpec(
        name="shared_cache_cleanup",
        cooldown_minutes=60,  # hourly
        visible_grace_minutes=0,
        run_fn=_run_shared_cache_cleanup,
        priority=36,
    ))

    def _run_central_self_health(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """§1 (2026-06-22): Centralen prober SIG SELV hver time → observe + eskalér hvis
        decide/observe fejler, breakers er åbne, eller for mange uløste severe incidents."""
        from core.services.central_health import observe_and_escalate
        rep = observe_and_escalate()
        return {"status": "ok", "decide_ok": rep.get("decide_ok"),
                "observe_ok": rep.get("observe_ok"), "degraded": rep.get("degraded"),
                "open_breakers": len(rep.get("open_breakers") or [])}

    register_producer(ProducerSpec(
        name="central_self_health",
        cooldown_minutes=60,  # hver time — self-helbred skal fanges hurtigt
        visible_grace_minutes=0,
        run_fn=_run_central_self_health,
        priority=36,
    ))

    def _run_central_learning(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """#4 (2026-06-22): adaptiv læring pr. cluster fra incident-historikken → observe +
        flag degraderende clusters (trender mod nedbrud) + vurdér Jarvis' autonomi-modenhed.
        Deterministisk, read-only — akkumulerer over tid (fx overnight)."""
        from core.services.central_learning import observe_learning
        s = observe_learning()
        return {"status": "ok", "degrading": len(s.get("degrading") or []),
                "autonomy": (s.get("autonomy") or {}).get("verdict")}

    register_producer(ProducerSpec(
        name="central_learning",
        cooldown_minutes=60,  # hver time — lær kontinuerligt
        visible_grace_minutes=0,
        run_fn=_run_central_learning,
        priority=36,
    ))

    def _run_stream_stall_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Stream-cluster (audit 2026-06-23): stream_stall sweepede FØR kun opportunistisk
        ved næste note_start → en zombie-stream i en HELT stille periode (ingen nye streams)
        blev aldrig flagget. Denne producer kalder sweep() på kadence så zombier fanges også
        i stilhed. Read-only (flagger, dropper aldrig)."""
        from core.services import stream_sentinel
        live = stream_sentinel.sweep()
        return {"status": "ok", "live_streams": int(live)}

    register_producer(ProducerSpec(
        name="stream_stall_sweep",
        cooldown_minutes=5,  # hvert 5. min — zombie skal fanges selv uden ny aktivitet
        visible_grace_minutes=0,
        run_fn=_run_stream_stall_sweep,
        priority=37,
    ))

    def _run_config_drift(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """§7 (2026-06-22): config↔runtime-drift-check (port). Fanger 8010/8011-typen — settings
        siger én port, API'en svarer på en anden → observe + incident. Read-only probe."""
        from core.services.config_drift import observe_config_drift
        rep = observe_config_drift()
        return {"status": "ok", "declared_port": rep.get("declared_port"),
                "actual_port": rep.get("actual_port"), "drift": rep.get("drift")}

    register_producer(ProducerSpec(
        name="config_drift_check",
        cooldown_minutes=1440,  # daily — drift opstår kun ved deploy/config-skift
        visible_grace_minutes=0,
        run_fn=_run_config_drift,
        priority=36,
    ))

    def _run_instrument_scan(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Selv-instrumenterings-motor (2026-06-23): AST-scan af kodebasen for silent-failure-
        mønstre → score → observe → reviewbare proposals (score≥3). Incremental (kun ændrede
        filer). ALDRIG auto-merged, instrumenterer aldrig sig selv."""
        from core.services.central_instrument import run_instrument_scan
        rep = run_instrument_scan(trigger=trigger, changed_only=True)
        return {"status": "ok", "scanned": rep.get("scanned"), "changed": rep.get("changed"),
                "findings": rep.get("findings"), "new_proposals": rep.get("new_proposals")}

    register_producer(ProducerSpec(
        name="instrument_scan",
        cooldown_minutes=360,  # hver 6. time (Jarvis-spec); incremental → billigt
        visible_grace_minutes=0,
        run_fn=_run_instrument_scan,
        priority=38,
    ))

    def _run_provider_health(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """provider_health (2026-06-23, Jarvis-spec): proaktiv provider-ping → flag nede/
        degraderet/tør + model-drift. Bygger på config_drift-mekanik (observe+flag+auto-resolve).
        ALDRIG destruktiv — retter ikke config selv."""
        from core.services.provider_health_check import observe_and_flag
        rep = observe_and_flag()
        return {"status": "ok", "checked": rep.get("checked"), "down": rep.get("unreachable"),
                "degraded": rep.get("degraded"), "model_drift": rep.get("model_drift")}

    register_producer(ProducerSpec(
        name="provider_health_check",
        cooldown_minutes=5,  # hvert 5. min (Jarvis-spec) — proaktiv, fanger drift før kritisk
        visible_grace_minutes=0,
        run_fn=_run_provider_health,
        priority=37,
    ))

    def _run_db_health_scan(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """DB-cluster (2026-06-22): daglig table-census + vækst-flag via db_sentinel.observe.
        ALDRIG destruktiv — kun observe + flag (tom tabel = kandidat til review, ikke drop)."""
        from core.services.db_sentinel import observe
        report = observe()
        return {"status": "ok", "tables": report.get("tables"),
                "total_rows": report.get("total_rows"),
                "flagged_growth": len(report.get("flagged_growth") or []),
                "empty_candidates": len(report.get("empty") or [])}

    register_producer(ProducerSpec(
        name="db_health_scan",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_db_health_scan,
        priority=36,
    ))

    def _run_tool_usage_stats(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Tools-cluster Phase 2 (2026-06-22): daglig forbrugs-statistik via tool_usage_store
        → central.observe (mest/ofte/nogle-gange/sjældent/aldrig) + flag antal døde tools.
        Grundlag for at ordne kataloget (mest-brugt først, døde sidst). Observe-only."""
        from core.services.tool_usage_store import observe_stats
        try:
            from core.tools.simple_tools import _TOOL_HANDLERS
            registered = list(_TOOL_HANDLERS.keys())
        except Exception:
            registered = []
        summary = observe_stats(registered)
        return {"status": "ok", "tracked": summary.get("tracked"),
                "never": summary.get("never"), "registered": len(registered)}

    register_producer(ProducerSpec(
        name="tool_usage_stats",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_tool_usage_stats,
        priority=36,
    ))

    def _run_endpoint_usage_stats(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Tools-cluster (2026-06-22): daglig API-endpoint forbrugs-statistik → central.observe
        (mest/aldrig) + flag antal døde endpoints (registreret men aldrig kaldt). Observe-only."""
        from core.services.endpoint_usage_store import observe_stats
        summary = observe_stats()
        return {"status": "ok", "tracked": summary.get("tracked"),
                "registered": summary.get("registered"), "dead": summary.get("dead")}

    register_producer(ProducerSpec(
        name="endpoint_usage_stats",
        cooldown_minutes=1440,  # daily
        visible_grace_minutes=0,
        run_fn=_run_endpoint_usage_stats,
        priority=36,
    ))
