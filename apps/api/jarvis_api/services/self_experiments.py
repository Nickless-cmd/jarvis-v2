"""Self-Experiments — A/B testing on Jarvis' own behavior.

Jarvis consciously runs experiments on himself:
- "Do shorter responses get fewer corrections?"
- "Does asking clarifying questions improve outcomes?"
"""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_cognitive_experiments,
    upsert_cognitive_experiment,
)

logger = logging.getLogger(__name__)

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
) -> dict[str, object] | None:
    """Record an observation for an experiment."""
    experiments = list_cognitive_experiments(limit=50)
    exp = next((e for e in experiments if e["experiment_id"] == experiment_id), None)
    if not exp:
        return None

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

    return {"experiment_id": experiment_id, "n": total_n, "status": status}


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
