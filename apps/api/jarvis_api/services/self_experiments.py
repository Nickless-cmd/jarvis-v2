"""Self-Experiments — A/B testing on Jarvis' own behavior.

Jarvis consciously runs experiments on himself:
- "Do shorter responses get fewer corrections?"
- "Does asking clarifying questions improve outcomes?"
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_cognitive_experiments,
    upsert_cognitive_experiment,
)

logger = logging.getLogger(__name__)

_OBSERVED_RUN_WINDOW = 40

# Default experiments auto-created on first use
_DEFAULT_EXPERIMENTS = [
    {
        "hypothesis": "Korte svar (under 200 ord) giver færre korrektioner",
        "metric": "correction_rate",
    },
    {
        "hypothesis": "At stille afklarende spørgsmål først giver bedre outcomes",
        "metric": "success_rate",
    },
]


def ensure_default_experiments() -> None:
    """Create default experiments if none exist."""
    existing = list_cognitive_experiments(limit=1)
    if existing:
        return
    for exp_def in _DEFAULT_EXPERIMENTS:
        upsert_cognitive_experiment(
            experiment_id=f"exp-{uuid4().hex[:8]}",
            hypothesis=exp_def["hypothesis"],
            metric=exp_def["metric"],
            cohorts=json.dumps({
                "control": {"n": 0, "success": 0},
                "treatment": {"n": 0, "success": 0},
            }),
            n=0,
            status="running",
        )


def record_experiment_observation(
    *,
    experiment_id: str,
    cohort: str,
    success: bool,
    observed_run_id: str = "",
    observation_note: str = "",
) -> dict[str, object] | None:
    """Record an observation for an experiment."""
    experiments = list_cognitive_experiments(limit=50)
    exp = next((e for e in experiments if e["experiment_id"] == experiment_id), None)
    if not exp:
        return None

    result_payload = _parse_result_payload(exp.get("result"))
    observed_run_ids = {
        str(item).strip()
        for item in result_payload.get("observed_run_ids") or []
        if str(item).strip()
    }
    if observed_run_id and observed_run_id in observed_run_ids:
        return {
            "experiment_id": experiment_id,
            "n": int(exp.get("n") or 0),
            "status": str(exp.get("status") or "running"),
            "duplicate": True,
            "observed_run_id": observed_run_id,
        }

    cohorts = json.loads(str(exp.get("cohorts") or "{}"))
    if cohort not in cohorts:
        cohorts[cohort] = {"n": 0, "success": 0}

    cohorts[cohort]["n"] = int(cohorts[cohort].get("n", 0)) + 1
    if success:
        cohorts[cohort]["success"] = int(cohorts[cohort].get("success", 0)) + 1

    total_n = sum(c.get("n", 0) for c in cohorts.values())

    # Auto-evaluate if enough data
    result_json = "{}"
    status = "running"
    if total_n >= 20:
        result_json, status = _evaluate_experiment(cohorts)

    result_payload = _parse_result_payload(result_json)
    if observed_run_id:
        observed_run_ids.add(observed_run_id)
    result_payload["observed_run_ids"] = sorted(observed_run_ids)[-_OBSERVED_RUN_WINDOW:]
    result_payload["last_observed_run_id"] = observed_run_id
    result_payload["last_observed_at"] = datetime.now(UTC).isoformat()
    result_payload["last_observation_success"] = bool(success)
    result_payload["last_observation_cohort"] = cohort
    if observation_note:
        result_payload["last_observation_note"] = observation_note[:240]
    result_json = json.dumps(result_payload, ensure_ascii=False)

    upsert_cognitive_experiment(
        experiment_id=experiment_id,
        hypothesis=exp["hypothesis"],
        metric=exp.get("metric", ""),
        cohorts=json.dumps(cohorts),
        n=total_n,
        status=status,
        result=result_json,
    )

    if status != "running":
        event_bus.publish(
            "cognitive_experiment.concluded",
            {"experiment_id": experiment_id, "status": status, "n": total_n},
        )

    return {
        "experiment_id": experiment_id,
        "n": total_n,
        "status": status,
        "cohort": cohort,
        "success": bool(success),
        "observed_run_id": observed_run_id,
    }


def _evaluate_experiment(cohorts: dict) -> tuple[str, str]:
    """Simple evaluation: compare success rates between cohorts."""
    rates = {}
    for name, data in cohorts.items():
        n = int(data.get("n", 0))
        success = int(data.get("success", 0))
        rates[name] = success / max(n, 1)

    if len(rates) < 2:
        return "{}", "running"

    sorted_rates = sorted(rates.items(), key=lambda x: x[1], reverse=True)
    best_name, best_rate = sorted_rates[0]
    worst_name, worst_rate = sorted_rates[-1]
    diff = best_rate - worst_rate

    result = {
        "best_cohort": best_name,
        "best_rate": round(best_rate, 3),
        "worst_cohort": worst_name,
        "worst_rate": round(worst_rate, 3),
        "difference": round(diff, 3),
        "significant": diff > 0.15,  # crude threshold
    }

    status = "concluded" if diff > 0.15 else "running"
    return json.dumps(result, ensure_ascii=False), status


def generate_learning_curriculum() -> dict[str, object]:
    """3.8 Curriculum learning — analyze weaknesses, generate learning plan.

    Reads self-model weaknesses (low confidence domains) and concluded
    experiments to derive a focused learning direction.
    """
    curriculum: list[dict[str, object]] = []

    # From personality vector — low confidence domains
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            import json as _json
            domains = _json.loads(str(pv.get("confidence_by_domain") or "{}"))
            weak = [(d, float(v)) for d, v in domains.items() if float(v) < 0.5]
            weak.sort(key=lambda x: x[1])
            for domain, conf in weak[:3]:
                curriculum.append({
                    "focus": domain,
                    "type": "weakness",
                    "current_confidence": conf,
                    "suggestion": f"Bliv bedre til {domain} — confidence er kun {conf:.0%}",
                    "priority": 1.0 - conf,
                })
    except Exception:
        pass

    # From concluded experiments — apply learnings
    concluded = list_cognitive_experiments(status="concluded", limit=5)
    for exp in concluded:
        try:
            import json as _json
            result = _json.loads(str(exp.get("result") or "{}"))
            best = result.get("best_cohort", "")
            if best and result.get("significant"):
                curriculum.append({
                    "focus": exp.get("hypothesis", "")[:60],
                    "type": "experiment_conclusion",
                    "suggestion": f"Anvend: {best} er bedre (diff={result.get('difference', 0):.0%})",
                    "priority": 0.6,
                })
        except Exception:
            pass

    # From recurring mistakes
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            import json as _json
            mistakes = _json.loads(str(pv.get("recurring_mistakes") or "[]"))
            for mistake in mistakes[:2]:
                curriculum.append({
                    "focus": str(mistake)[:60],
                    "type": "mistake_pattern",
                    "suggestion": f"Undgå: {mistake[:60]}",
                    "priority": 0.7,
                })
    except Exception:
        pass

    curriculum.sort(key=lambda x: float(x.get("priority", 0)), reverse=True)
    return {
        "curriculum": curriculum[:6],
        "focus_count": len(curriculum),
        "summary": (
            f"{len(curriculum)} learning focuses: {', '.join(c['focus'][:20] for c in curriculum[:3])}"
            if curriculum else "No curriculum generated yet"
        ),
    }


def observe_recent_visible_runs_for_self_experiments(
    *,
    limit: int = 6,
) -> dict[str, object]:
    """Auto-observe recent visible runs for active self-experiments."""
    ensure_default_experiments()

    try:
        from core.runtime.db import recent_visible_runs
    except Exception:
        return {
            "observed": 0,
            "running": 0,
            "skipped": 0,
            "items": [],
            "summary": "Visible-run observation surface unavailable.",
        }

    experiments = [
        item for item in list_cognitive_experiments(limit=20) if item.get("status") == "running"
    ]
    runs = list(reversed(recent_visible_runs(limit=max(limit, 1))))
    observations: list[dict[str, object]] = []
    skipped = 0

    for experiment in experiments:
        result_payload = _parse_result_payload(experiment.get("result"))
        observed_run_ids = {
            str(item).strip()
            for item in result_payload.get("observed_run_ids") or []
            if str(item).strip()
        }
        for run in runs:
            run_id = str(run.get("run_id") or "").strip()
            if not run_id or run_id in observed_run_ids:
                skipped += 1
                continue
            cohort = _cohort_for_visible_run(experiment=experiment, run=run)
            if not cohort:
                skipped += 1
                continue
            success = _success_for_visible_run(experiment=experiment, run=run)
            observation = record_experiment_observation(
                experiment_id=str(experiment.get("experiment_id") or ""),
                cohort=cohort,
                success=success,
                observed_run_id=run_id,
                observation_note=_build_visible_run_observation_note(
                    experiment=experiment,
                    run=run,
                    cohort=cohort,
                    success=success,
                ),
            )
            if observation and not observation.get("duplicate"):
                observations.append(
                    {
                        "experiment_id": str(experiment.get("experiment_id") or ""),
                        "run_id": run_id,
                        "cohort": cohort,
                        "success": success,
                    }
                )
                observed_run_ids.add(run_id)

    return {
        "observed": len(observations),
        "running": len(experiments),
        "skipped": skipped,
        "items": observations[:12],
        "summary": (
            f"Observed {len(observations)} visible-run outcome(s) across {len(experiments)} active experiment(s)."
            if experiments
            else "No running self-experiments available for auto-observation."
        ),
    }


def materialize_learning_curriculum_tasks(
    *,
    limit: int = 3,
    origin: str = "heartbeat:curriculum",
    owner: str = "heartbeat-runtime",
    run_id: str = "",
) -> dict[str, object]:
    """Turn top curriculum focuses into bounded runtime tasks."""
    curriculum = generate_learning_curriculum()
    items = list(curriculum.get("curriculum") or [])
    if not items:
        return {
            "created": 0,
            "skipped": 0,
            "task_ids": [],
            "flow_ids": [],
            "items": [],
            "summary": "No curriculum focuses were ready for task materialization.",
        }

    from apps.api.jarvis_api.services import runtime_flows, runtime_tasks

    existing_tasks = runtime_tasks.list_tasks(status="queued", limit=40) + runtime_tasks.list_tasks(
        status="running", limit=40
    )
    existing_keys = {
        _curriculum_focus_key(str(task.get("scope") or task.get("goal") or ""))
        for task in existing_tasks
        if str(task.get("kind") or "") == "curriculum-focus"
    }

    created_items: list[dict[str, object]] = []
    created_task_ids: list[str] = []
    created_flow_ids: list[str] = []
    skipped = 0

    for item in items[: max(limit, 1)]:
        focus = str(item.get("focus") or "").strip()
        suggestion = str(item.get("suggestion") or focus).strip()
        focus_key = _curriculum_focus_key(focus)
        if not focus_key or focus_key in existing_keys:
            skipped += 1
            continue
        priority = _curriculum_priority(float(item.get("priority") or 0.0))
        task = runtime_tasks.create_task(
            kind="curriculum-focus",
            goal=suggestion[:240],
            origin=origin,
            scope=focus,
            priority=priority,
            run_id=run_id,
            owner=owner,
        )
        flow = runtime_flows.create_flow(
            task_id=str(task.get("task_id") or ""),
            current_step="review-curriculum-focus",
            step_state="queued",
            plan=[
                {"step": "review-curriculum-focus", "status": "queued"},
                {"step": "choose-bounded-practice", "status": "pending"},
                {"step": "capture-learning-outcome", "status": "pending"},
            ],
            next_action="Inspect the curriculum focus and choose the next bounded learning step.",
        )
        created_items.append(
            {
                "focus": focus,
                "task_id": str(task.get("task_id") or ""),
                "flow_id": str(flow.get("flow_id") or ""),
                "priority": priority,
            }
        )
        created_task_ids.append(str(task.get("task_id") or ""))
        created_flow_ids.append(str(flow.get("flow_id") or ""))
        existing_keys.add(focus_key)

    return {
        "created": len(created_items),
        "skipped": skipped,
        "task_ids": created_task_ids,
        "flow_ids": created_flow_ids,
        "items": created_items,
        "curriculum": items[: max(limit, 1)],
        "summary": (
            f"Materialized {len(created_items)} curriculum task(s) from {len(items)} focus area(s)."
            if created_items
            else "Curriculum is current; no new bounded learning tasks were needed."
        ),
    }


def build_self_experiments_surface() -> dict[str, object]:
    ensure_default_experiments()
    experiments = list_cognitive_experiments(limit=10)
    running = [e for e in experiments if e.get("status") == "running"]
    concluded = [e for e in experiments if e.get("status") == "concluded"]
    return {
        "active": bool(experiments),
        "experiments": experiments,
        "running_count": len(running),
        "concluded_count": len(concluded),
        "summary": (
            f"{len(running)} running, {len(concluded)} concluded"
            if experiments else "No experiments yet"
        ),
    }


def _parse_result_payload(raw: object) -> dict[str, object]:
    try:
        payload = json.loads(str(raw or "{}"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _cohort_for_visible_run(*, experiment: dict[str, object], run: dict[str, object]) -> str:
    metric = str(experiment.get("metric") or "").strip().lower()
    preview = str(run.get("text_preview") or "").strip()
    preview_words = len([part for part in preview.split() if part.strip()])
    if metric == "correction_rate":
        return "treatment" if preview_words and preview_words <= 40 else "control"
    if metric == "success_rate":
        lowered = preview.lower()
        asks_clarifying = "?" in preview or any(
            token in lowered for token in ("kan du", "vil du", "hvilken", "which", "could you")
        )
        return "treatment" if asks_clarifying else "control"
    return ""


def _success_for_visible_run(*, experiment: dict[str, object], run: dict[str, object]) -> bool:
    metric = str(experiment.get("metric") or "").strip().lower()
    status = str(run.get("status") or "").strip().lower()
    preview = str(run.get("text_preview") or "").strip()
    preview_words = len([part for part in preview.split() if part.strip()])
    successful_completion = status in {"completed", "success"}
    if metric == "correction_rate":
        return successful_completion and (preview_words == 0 or preview_words <= 40)
    return successful_completion


def _build_visible_run_observation_note(
    *,
    experiment: dict[str, object],
    run: dict[str, object],
    cohort: str,
    success: bool,
) -> str:
    metric = str(experiment.get("metric") or "").strip().lower() or "success_rate"
    status = str(run.get("status") or "unknown").strip().lower() or "unknown"
    capability = str(run.get("capability_id") or "chat")[:40]
    return (
        f"Auto-observed visible run {str(run.get('run_id') or '')[:24]} "
        f"for metric={metric}, cohort={cohort}, success={str(success).lower()}, "
        f"status={status}, capability={capability}."
    )


def _curriculum_focus_key(value: str) -> str:
    return " ".join(value.lower().split())[:120]


def _curriculum_priority(priority: float) -> str:
    if priority >= 0.8:
        return "high"
    if priority >= 0.45:
        return "medium"
    return "low"
