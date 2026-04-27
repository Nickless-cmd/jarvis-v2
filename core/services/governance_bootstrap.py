"""Governance bootstrap — idempotent setup of default windows, jobs handlers, automations.

Called at runtime startup to ensure the Governance MC tab has meaningful
content. Safe to call multiple times — each helper checks for existing
entries before creating new ones.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def ensure_default_windows() -> list[str]:
    """Ensure default scheduled job windows exist. Returns list of window_ids
    that were newly created (empty if all already existed)."""
    from core.services.scheduled_job_windows import list_windows, register_window

    existing = {w.get("name"): w for w in list_windows()}
    created: list[str] = []

    defaults = [
        {
            "name": "night-batch",
            "start_hour": 2,
            "end_hour": 6,
            "max_requests": 200,
            "prefer_free_first": True,
            "description": "Natlig batch-vindue til consolidation, dream distillation, memory decay",
        },
        {
            "name": "morning-catchup",
            "start_hour": 6,
            "end_hour": 9,
            "max_requests": 100,
            "prefer_free_first": False,
            "description": "Morgen-catchup: chronicle entries, initiative review",
        },
        {
            "name": "quiet-afternoon",
            "start_hour": 13,
            "end_hour": 15,
            "max_requests": 80,
            "prefer_free_first": True,
            "description": "Stille middag: cheap lane-learning, repetition reviews",
        },
    ]

    for spec in defaults:
        if spec["name"] in existing:
            continue
        try:
            wid = register_window(
                name=spec["name"],
                start_hour=spec["start_hour"],
                end_hour=spec["end_hour"],
                max_requests=spec["max_requests"],
                prefer_free_first=spec["prefer_free_first"],
                active=True,
            )
            created.append(wid)
            logger.info(
                "governance_bootstrap: registered window %s (%dh-%dh)",
                spec["name"], spec["start_hour"], spec["end_hour"],
            )
        except Exception as exc:
            logger.warning("governance_bootstrap: window %s failed: %s", spec["name"], exc)

    return created


def ensure_default_job_handlers() -> list[str]:
    """Register default job-type handlers. Returns list of job_type names registered.

    Handlers here are thin wrappers — they import the heavy service lazily so
    startup is fast and handler registration is cheap.
    """
    from core.services.jobs_engine import register_handler

    registered: list[str] = []

    def _chronicle_refresh_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Rebuild the latest chronicle summary entry."""
        try:
            from core.services.chronicle_engine import build_chronicle_summary
            result = build_chronicle_summary() or {}
            return {"status": "ok", "kind": "chronicle_refresh", "result": result}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _memory_decay_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Run one pass of memory decay (intended for night windows)."""
        try:
            from core.services.memory_decay_daemon import tick_memory_decay_daemon
            return {"status": "ok", "kind": "memory_decay", "result": tick_memory_decay_daemon()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _dream_distillation_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Distill pending dreams into consolidated form."""
        try:
            from core.services.dream_distillation_daemon import tick_dream_distillation_daemon
            return {"status": "ok", "kind": "dream_distillation", "result": tick_dream_distillation_daemon()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _weekly_manifest_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Rewrite WEEKLY_MANIFEST.md with this week's self-reflection."""
        try:
            from core.services.weekly_manifest import build_weekly_manifest
            return {"status": "ok", "kind": "weekly_manifest_refresh", "result": build_weekly_manifest()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _goal_synthesis_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Propose new candidate goals from recent dreams/chronicle/questions."""
        try:
            from core.services.goal_signal_synthesizer import synthesize_candidate_goals
            return {"status": "ok", "kind": "goal_synthesis", "result": synthesize_candidate_goals()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _personality_snapshot_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Take a periodic mood snapshot for personality_drift baseline."""
        try:
            from core.services.personality_drift import take_snapshot
            return {"status": "ok", "kind": "personality_snapshot", "result": take_snapshot()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _provider_health_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Ping all cheap-lane providers proactively."""
        try:
            from core.services.provider_health_check import health_check_all_providers
            return {"status": "ok", "kind": "provider_health_check", "result": health_check_all_providers()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _auto_improvement_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Daily auto-improvement proposals via plan_proposals."""
        try:
            from core.services.auto_improvement_proposer import generate_improvement_proposals
            return {"status": "ok", "kind": "auto_improvement", "result": generate_improvement_proposals()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _agent_observation_decay_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Daily: mark agent observations older than 14 days as stale."""
        try:
            from core.services.agent_observation_compressor import mark_stale_observations
            return {"status": "ok", "kind": "obs_decay", "result": mark_stale_observations()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _wakeup_dispatch_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Every 60s: dispatch fired self-wakeups (webchat push + heartbeat trigger)."""
        try:
            from core.services.wakeup_dispatcher import dispatch_due_wakeups
            return {"status": "ok", "kind": "wakeup_dispatch", "result": dispatch_due_wakeups()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _crisis_scan_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Daily: scan for identity-forming crisis markers."""
        try:
            from core.services.crisis_marker_detector import scan_for_crisis_markers
            return {"status": "ok", "kind": "crisis_scan", "result": scan_for_crisis_markers()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _identity_drift_proposer_handler(payload: dict[str, Any]) -> dict[str, Any]:
        """Weekly: if drift sustained, propose IDENTITY.md update."""
        try:
            from core.services.identity_drift_proposer import propose_identity_update_if_drifted
            return {"status": "ok", "kind": "identity_drift_proposal", "result": propose_identity_update_if_drifted()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _monthly_arc_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.long_arc_synthesizer import synthesize_arc
            return {"status": "ok", "kind": "monthly_arc", "result": synthesize_arc(period="monthly")}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _quarterly_arc_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.long_arc_synthesizer import synthesize_arc
            return {"status": "ok", "kind": "quarterly_arc", "result": synthesize_arc(period="quarterly")}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _annual_arc_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.long_arc_synthesizer import synthesize_arc
            return {"status": "ok", "kind": "annual_arc", "result": synthesize_arc(period="annual")}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _skill_distillation_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.agent_skill_distiller import distill_all_known_roles
            return {"status": "ok", "kind": "skill_distillation",
                    "result": distill_all_known_roles(days=7)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _arc_rule_extraction_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.arc_rule_extractor import extract_rules_for_unprocessed_arcs
            return {"status": "ok", "kind": "arc_rule_extraction",
                    "result": extract_rules_for_unprocessed_arcs()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    handlers = {
        "chronicle_refresh": _chronicle_refresh_handler,
        "memory_decay_sweep": _memory_decay_handler,
        "dream_distillation_sweep": _dream_distillation_handler,
        "weekly_manifest_refresh": _weekly_manifest_handler,
        "goal_synthesis": _goal_synthesis_handler,
        "personality_snapshot": _personality_snapshot_handler,
        "provider_health_check": _provider_health_handler,
        "auto_improvement_proposals": _auto_improvement_handler,
        "agent_observation_decay": _agent_observation_decay_handler,
        "wakeup_dispatch": _wakeup_dispatch_handler,
        "crisis_scan": _crisis_scan_handler,
        "identity_drift_proposal": _identity_drift_proposer_handler,
        "monthly_arc": _monthly_arc_handler,
        "quarterly_arc": _quarterly_arc_handler,
        "annual_arc": _annual_arc_handler,
        "skill_distillation": _skill_distillation_handler,
        "arc_rule_extraction": _arc_rule_extraction_handler,
    }

    for job_type, handler in handlers.items():
        try:
            register_handler(job_type, handler)
            registered.append(job_type)
        except Exception as exc:
            logger.warning("governance_bootstrap: handler %s failed: %s", job_type, exc)

    if registered:
        logger.info("governance_bootstrap: registered %d job handlers: %s",
                    len(registered), ", ".join(registered))
    return registered


def ensure_default_automations() -> list[str]:
    """Seed a couple of baseline automations so the DSL surface has examples.

    These let the UI demonstrate the DSL shape and give real entries that the
    tick loop evaluates. Triggers and actions use the valid literals from
    automation_dsl.py (TriggerType = schedule|webhook|event,
    ActionType = llm_prompt|call_tool|post_message).
    """
    from core.services.automation_dsl import (
        ActionSpec,
        AutomationDSL,
        TriggerSpec,
        list_automations,
        register_automation,
    )

    existing_names = {a.get("name") for a in list_automations()}
    created: list[str] = []

    defaults = [
        {
            "name": "daily-chronicle-cue",
            "description": "Minder Jarvis om at reflektere over dagen ved dagsafslutning",
            "trigger": TriggerSpec(type="schedule", config={"cron": "0 21 * * *"}),
            "action": ActionSpec(
                type="llm_prompt",
                prompt_template="Kort daglig refleksion: hvad stod frem for dig i dag?",
                title="Daily chronicle cue",
            ),
            "channel": "internal",
        },
        {
            "name": "tool-error-pattern-watch",
            "description": "Skriv en intern note hvis samme tool fejler gentagne gange",
            "trigger": TriggerSpec(type="event", config={"event_kind": "tool.completed", "filter": "status=error"}),
            "action": ActionSpec(
                type="post_message",
                prompt_template="Gentaget tool-fejl observeret; overvej at tjekke pattern.",
                title="Tool error pattern",
            ),
            "channel": "ntfy",
        },
    ]

    for spec in defaults:
        if spec["name"] in existing_names:
            continue
        try:
            dsl = AutomationDSL(
                name=spec["name"],
                description=spec["description"],
                trigger=spec["trigger"],
                action=spec["action"],
                channel=spec["channel"],
            )
            auto_id = register_automation(dsl)
            created.append(auto_id)
            logger.info("governance_bootstrap: registered automation %s", spec["name"])
        except Exception as exc:
            logger.warning("governance_bootstrap: automation %s failed: %s", spec["name"], exc)

    return created


def ensure_warmup_job() -> str | None:
    """Enqueue a single low-priority warmup job on first boot so the
    jobs_engine surface has at least one entry showing the system works.
    Idempotent: checks if any jobs exist first.
    """
    from core.services.jobs_engine import enqueue_job, list_jobs

    existing = list_jobs(limit=1)
    if existing:
        return None  # Already have job history

    try:
        job_id = enqueue_job(
            job_type="chronicle_refresh",
            payload={"reason": "warmup on first boot"},
            priority=9,  # low priority
            max_requests=1,
        )
        logger.info("governance_bootstrap: enqueued warmup job %s", job_id)
        return job_id
    except Exception as exc:
        logger.warning("governance_bootstrap: warmup job failed: %s", exc)
        return None


def bootstrap_all() -> dict[str, Any]:
    """Run all idempotent bootstrap helpers. Safe at any startup."""
    result: dict[str, Any] = {}
    try:
        result["windows_created"] = ensure_default_windows()
    except Exception as exc:
        result["windows_error"] = str(exc)
    try:
        result["handlers_registered"] = ensure_default_job_handlers()
    except Exception as exc:
        result["handlers_error"] = str(exc)
    try:
        result["automations_created"] = ensure_default_automations()
    except Exception as exc:
        result["automations_error"] = str(exc)
    try:
        result["warmup_job"] = ensure_warmup_job()
    except Exception as exc:
        result["warmup_error"] = str(exc)
    return result
