"""Experiment runner — controlled A/B trials of prompt variants.

Allows Jarvis (or user) to test two variants of a prompt fragment in
controlled rotation, log outcomes via prompt_variant_tracker, and report
winner after enough trials.

Stays within propose-only territory: experiments produce DATA,
not auto-applied changes. After an experiment concludes, the result
goes via plan_proposals — user approves the winner.

State:
- _STATE_KEY 'experiments' stores {experiment_id, scope, variant_a, variant_b,
  trials_target, trials_done, status, winner}
- Active experiments alternate variants per call

Critical: this module does NOT mutate any prompt. It exposes
get_active_variant(scope) for callers (prompt_contract sections) that
choose to participate. Sections that don't call it use their default.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "prompt_experiments"


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(d: dict[str, dict[str, Any]]) -> None:
    save_json(_STATE_KEY, d)


def start_experiment(
    *,
    scope: str,
    variant_a_label: str,
    variant_a_text: str,
    variant_b_label: str,
    variant_b_text: str,
    trials_target: int = 20,
) -> dict[str, Any]:
    """Begin a new A/B experiment for a scope."""
    if not scope or not variant_a_label or not variant_b_label:
        return {"status": "error", "error": "scope and both variant labels required"}
    experiments = _load()
    # Close any existing active experiment for this scope first
    for eid, exp in list(experiments.items()):
        if exp.get("scope") == scope and exp.get("status") == "active":
            exp["status"] = "superseded"
            exp["closed_at"] = datetime.now(UTC).isoformat()
    eid = f"exp-{uuid4().hex[:10]}"
    experiments[eid] = {
        "experiment_id": eid,
        "scope": scope,
        "variant_a": {"label": variant_a_label, "text": variant_a_text},
        "variant_b": {"label": variant_b_label, "text": variant_b_text},
        "trials_target": int(max(1, trials_target)),
        "trials_done": 0,
        "next_pick": "a",
        "status": "active",
        "started_at": datetime.now(UTC).isoformat(),
    }
    _save(experiments)
    return {"status": "ok", "experiment_id": eid, "experiment": experiments[eid]}


def get_active_variant(scope: str) -> dict[str, Any] | None:
    """Return the variant currently scheduled for this scope, or None.

    Caller (e.g. an awareness-section function) substitutes its default
    text with the returned text, then logs outcome via
    prompt_variant_tracker.log_variant_outcome.

    Side effect: increments trials_done + flips next_pick.
    """
    experiments = _load()
    active = [
        e for e in experiments.values()
        if e.get("scope") == scope and e.get("status") == "active"
    ]
    if not active:
        return None
    exp = active[0]
    pick = "a" if exp.get("next_pick", "a") == "a" else "b"
    variant = exp.get(f"variant_{pick}") or {}
    exp["trials_done"] = int(exp.get("trials_done", 0)) + 1
    exp["next_pick"] = "b" if pick == "a" else "a"
    if exp["trials_done"] >= int(exp.get("trials_target") or 0):
        exp["status"] = "ready_for_analysis"
    _save(experiments)
    return {
        "experiment_id": exp["experiment_id"],
        "variant_pick": pick,
        "label": variant.get("label", ""),
        "text": variant.get("text", ""),
    }


def conclude_experiment(experiment_id: str) -> dict[str, Any]:
    """Analyze an experiment's data via prompt_variant_tracker, declare winner."""
    experiments = _load()
    exp = experiments.get(experiment_id)
    if exp is None:
        return {"status": "error", "error": "experiment not found"}
    scope = str(exp.get("scope", ""))
    try:
        from core.services.prompt_variant_tracker import variant_performance
        perf = variant_performance(scope=scope, min_samples=3)
    except Exception as exc:
        return {"status": "error", "error": f"perf read failed: {exc}"}
    variants = perf.get("variants") or []
    if not variants:
        exp["status"] = "inconclusive"
        exp["closed_at"] = datetime.now(UTC).isoformat()
        _save(experiments)
        return {"status": "ok", "result": "inconclusive", "experiment": exp}

    # Find the two labels
    label_a = exp.get("variant_a", {}).get("label", "")
    label_b = exp.get("variant_b", {}).get("label", "")
    perf_a = next((v for v in variants if v.get("variant_label") == label_a), None)
    perf_b = next((v for v in variants if v.get("variant_label") == label_b), None)
    if perf_a is None or perf_b is None:
        exp["status"] = "inconclusive"
        exp["closed_at"] = datetime.now(UTC).isoformat()
        _save(experiments)
        return {"status": "ok", "result": "inconclusive", "reason": "missing data for both variants",
                "experiment": exp}

    winner = "a" if perf_a["avg_score"] > perf_b["avg_score"] else "b"
    margin = abs(perf_a["avg_score"] - perf_b["avg_score"])
    exp["status"] = "concluded"
    exp["closed_at"] = datetime.now(UTC).isoformat()
    exp["winner"] = winner
    exp["margin"] = round(margin, 1)
    exp["variant_a_avg"] = perf_a["avg_score"]
    exp["variant_b_avg"] = perf_b["avg_score"]
    _save(experiments)

    # File a proposal to adopt the winner (propose-only — user approves)
    try:
        from core.services.plan_proposals import propose_plan
        winner_label = label_a if winner == "a" else label_b
        propose_plan(
            session_id=None,
            title=f"Experiment {experiment_id} concluded — adopt variant '{winner_label}' for {scope}",
            why=(
                f"Variant '{winner_label}' scored {perf_a['avg_score'] if winner=='a' else perf_b['avg_score']:.1f} "
                f"vs the loser's {perf_b['avg_score'] if winner=='a' else perf_a['avg_score']:.1f}. "
                f"Margin: {margin:.1f}. Recommendation: make the winner the default."
            ),
            steps=[
                f"Update default variant for scope '{scope}' to '{winner_label}'",
                "Verify no regression after adoption",
                "Close this experiment record",
            ],
        )
    except Exception:
        pass

    return {"status": "ok", "result": "concluded", "winner": winner, "experiment": exp}


def list_experiments(*, status: str | None = None) -> list[dict[str, Any]]:
    experiments = list(_load().values())
    if status:
        experiments = [e for e in experiments if e.get("status") == status]
    experiments.sort(key=lambda e: str(e.get("started_at", "")), reverse=True)
    return experiments


def _exec_start_experiment(args: dict[str, Any]) -> dict[str, Any]:
    return start_experiment(
        scope=str(args.get("scope") or ""),
        variant_a_label=str(args.get("variant_a_label") or ""),
        variant_a_text=str(args.get("variant_a_text") or ""),
        variant_b_label=str(args.get("variant_b_label") or ""),
        variant_b_text=str(args.get("variant_b_text") or ""),
        trials_target=int(args.get("trials_target") or 20),
    )


def _exec_conclude_experiment(args: dict[str, Any]) -> dict[str, Any]:
    return conclude_experiment(str(args.get("experiment_id") or ""))


def _exec_list_experiments(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "experiments": list_experiments(status=args.get("status"))}


EXPERIMENT_RUNNER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "start_prompt_experiment",
            "description": (
                "Start an A/B experiment on a prompt-fragment scope. Trials "
                "alternate; outcomes logged via log_variant_outcome. After "
                "trials_target, run conclude_experiment to file a proposal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "variant_a_label": {"type": "string"},
                    "variant_a_text": {"type": "string"},
                    "variant_b_label": {"type": "string"},
                    "variant_b_text": {"type": "string"},
                    "trials_target": {"type": "integer"},
                },
                "required": ["scope", "variant_a_label", "variant_a_text",
                             "variant_b_label", "variant_b_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conclude_prompt_experiment",
            "description": "Analyze experiment data, file proposal to adopt winner via plan_proposals.",
            "parameters": {
                "type": "object",
                "properties": {"experiment_id": {"type": "string"}},
                "required": ["experiment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_prompt_experiments",
            "description": "List active/concluded prompt-variant experiments.",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": [],
            },
        },
    },
]
