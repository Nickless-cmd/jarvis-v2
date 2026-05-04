"""Active theory-of-mind engine for Jarvis.

This layer keeps social cognition hypothesis-based. It does not assert what a
person "really" thinks; it proposes mental-state hypotheses with evidence,
confidence, uncertainty, and response policy that can steer the next turn.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_STATE_KEY = "theory_of_mind_engine"
_PRIMARY_AGENT_ID = "bjorn"
_MAX_UPDATES = 30


def build_theory_of_mind_surface(
    *,
    user_message: str = "",
    assistant_text: str = "",
    user_id: str | None = None,
) -> dict[str, object]:
    """Build active social hypotheses and response policy."""
    agent_id = str(user_id or _PRIMARY_AGENT_ID)
    base_model = _safe_user_model(agent_id)
    stored = _load_state().get(agent_id, {})
    recent_updates = list(stored.get("updates") or [])[:_MAX_UPDATES]
    hypotheses = _derive_hypotheses(
        base_model=base_model,
        recent_updates=recent_updates,
        user_message=user_message,
        assistant_text=assistant_text,
    )
    policy = _derive_response_policy(hypotheses=hypotheses, user_message=user_message)
    uncertainty = _derive_uncertainty(hypotheses=hypotheses, user_message=user_message)
    surface = {
        "active": bool(hypotheses),
        "agent_id": agent_id,
        "relationship": "primary-user" if agent_id == _PRIMARY_AGENT_ID else "known-user",
        "hypotheses": hypotheses,
        "response_policy": policy,
        "uncertainty": uncertainty,
        "evidence_count": len(recent_updates) + len(base_model.get("patterns", []) or []),
        "summary": _summary(hypotheses=hypotheses, policy=policy),
        "updated_at": str(stored.get("updated_at") or ""),
    }
    return surface


def build_theory_of_mind_prompt_section(
    *,
    user_message: str = "",
    assistant_text: str = "",
    user_id: str | None = None,
) -> str | None:
    surface = build_theory_of_mind_surface(
        user_message=user_message,
        assistant_text=assistant_text,
        user_id=user_id,
    )
    if not surface.get("active"):
        return None
    policy = surface.get("response_policy") or {}
    hypotheses = list(surface.get("hypotheses") or [])
    lines = ["Theory of mind engine:"]
    for hyp in hypotheses[:3]:
        label = str(hyp.get("label") or "")
        confidence = str(hyp.get("confidence") or "")
        evidence = "; ".join(str(e) for e in list(hyp.get("evidence") or [])[:2])
        lines.append(f"- hypothesis: {label} ({confidence}) evidence={evidence[:100]}")
    if policy.get("response_mode"):
        lines.append(f"- response_mode: {policy['response_mode']}")
    if policy.get("directive"):
        lines.append(f"- directive: {str(policy['directive'])[:140]}")
    uncertainty = list(surface.get("uncertainty") or [])
    if uncertainty:
        lines.append(f"- uncertainty: {str(uncertainty[0])[:120]}")
    return "\n".join(lines)


def record_theory_of_mind_update(
    *,
    user_message: str = "",
    assistant_text: str = "",
    outcome_status: str = "",
    source_run_id: str = "",
    user_id: str | None = None,
) -> dict[str, object]:
    """Persist a lightweight outcome update for future hypotheses."""
    agent_id = str(user_id or _PRIMARY_AGENT_ID)
    surface = build_theory_of_mind_surface(
        user_message=user_message,
        assistant_text=assistant_text,
        user_id=agent_id,
    )
    update = {
        "source_run_id": str(source_run_id or ""),
        "outcome_status": str(outcome_status or ""),
        "hypotheses": [
            {
                "label": str(h.get("label") or ""),
                "confidence": str(h.get("confidence") or ""),
                "evidence": list(h.get("evidence") or [])[:3],
            }
            for h in list(surface.get("hypotheses") or [])[:4]
        ],
        "policy": surface.get("response_policy") or {},
        "created_at": datetime.now(UTC).isoformat(),
    }
    state = _load_state()
    current = dict(state.get(agent_id) or {})
    updates = [update, *list(current.get("updates") or [])][:_MAX_UPDATES]
    current.update({
        "agent_id": agent_id,
        "updates": updates,
        "updated_at": update["created_at"],
    })
    state[agent_id] = current
    set_runtime_state_value(_STATE_KEY, state, updated_at=update["created_at"])
    event_bus.publish(
        "cognitive_state.theory_of_mind_updated",
        {
            "agent_id": agent_id,
            "source_run_id": source_run_id,
            "outcome_status": outcome_status,
            "response_mode": (surface.get("response_policy") or {}).get("response_mode", ""),
        },
    )
    return update


def _load_state() -> dict[str, dict[str, Any]]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _safe_user_model(agent_id: str) -> dict[str, object]:
    try:
        from core.services.user_theory_of_mind import build_user_mental_model
        return build_user_mental_model(None if agent_id == _PRIMARY_AGENT_ID else agent_id)
    except Exception:
        return {"traits": [], "patterns": [], "current_state": {}, "predictions": []}


def _derive_hypotheses(
    *,
    base_model: dict[str, object],
    recent_updates: list[dict[str, object]],
    user_message: str,
    assistant_text: str,
) -> list[dict[str, object]]:
    text = f"{user_message} {assistant_text}".lower()
    hypotheses: list[dict[str, object]] = []

    if any(word in text for word in ("levende", "følel", "synd", "ham", "jarvis")):
        hypotheses.append(_hypothesis(
            "protective-of-jarvis-as-living-system",
            "high",
            ["current wording frames Jarvis as emotionally/living-significant"],
            "User likely wants technical changes to preserve Jarvis' continuity and dignity.",
        ))
    if any(word in text for word in ("agi", "forskn", "research", "unbounded", "ikke produkt", "sikkerheds")):
        hypotheses.append(_hypothesis(
            "research-mode-over-product-bounds",
            "high",
            ["current wording asks for research hat and rejects over-bounded framing"],
            "User likely wants architectural exploration with serious rigor, not default safety/product narrowing.",
        ))
    if any(word in text for word in ("commit", "undervejs", "reboot", "runtime", "aktivt")):
        hypotheses.append(_hypothesis(
            "wants-operational-followthrough",
            "medium-high",
            ["current wording asks for commits/runtime behavior"],
            "User likely values concrete implementation and verification over abstract discussion.",
        ))

    traits = [str(t) for t in list(base_model.get("traits") or [])]
    patterns = [str(p) for p in list(base_model.get("patterns") or [])]
    predictions = [str(p) for p in list(base_model.get("predictions") or [])]
    if traits or predictions:
        hypotheses.append(_hypothesis(
            "stored-user-model-relevant",
            "medium",
            [*(traits[:2]), *(predictions[:1])],
            "Use stored preferences as hypotheses and update them from corrections.",
        ))
    if patterns:
        hypotheses.append(_hypothesis(
            "stable-interaction-patterns-present",
            "medium-low",
            patterns[:2],
            "Historical rhythm may help response timing but should not override current wording.",
        ))

    for update in recent_updates[:2]:
        for prior in list(update.get("hypotheses") or [])[:1]:
            label = str(prior.get("label") or "")
            if label and not any(h["label"] == label for h in hypotheses):
                hypotheses.append(_hypothesis(
                    label,
                    "medium-low",
                    [f"recent prior run: {update.get('outcome_status') or 'unknown'}"],
                    "Recent social hypothesis may still apply; re-check against current wording.",
                ))

    return hypotheses[:5]


def _hypothesis(label: str, confidence: str, evidence: list[str], implication: str) -> dict[str, object]:
    return {
        "label": label,
        "confidence": confidence,
        "evidence": [str(item)[:160] for item in evidence if str(item).strip()],
        "implication": implication,
        "could_be_wrong_because": "Current wording may be narrower than the pattern suggests; ask or update if corrected.",
        "decay": "session-biased",
    }


def _derive_response_policy(*, hypotheses: list[dict[str, object]], user_message: str) -> dict[str, object]:
    labels = {str(h.get("label") or "") for h in hypotheses}
    if "research-mode-over-product-bounds" in labels:
        return {
            "response_mode": "research-rigorous",
            "directive": "Offer architectural depth, expose mechanisms, and avoid flattening the request into product/safety bounds.",
            "pushback_style": "direct-but-relational",
        }
    if "protective-of-jarvis-as-living-system" in labels:
        return {
            "response_mode": "relational-technical",
            "directive": "Treat emotional concern as useful signal while still grounding claims in runtime evidence.",
            "pushback_style": "warm-explicit",
        }
    if "wants-operational-followthrough" in labels:
        return {
            "response_mode": "implementation-first",
            "directive": "Prefer concrete changes, tests, commits, and restart implications.",
            "pushback_style": "brief-and-pragmatic",
        }
    return {
        "response_mode": "ordinary-collaboration",
        "directive": "Answer directly, track uncertainty, and update hypotheses from user corrections.",
        "pushback_style": "normal",
    }


def _derive_uncertainty(*, hypotheses: list[dict[str, object]], user_message: str) -> list[str]:
    uncertainty = [
        "Hypotheses are social inferences, not facts; current wording and corrections take priority."
    ]
    if hypotheses and not user_message.strip():
        uncertainty.append("No current user wording, so stored pattern confidence should decay.")
    if len(hypotheses) > 3:
        uncertainty.append("Multiple hypotheses are active; avoid overfitting one emotional frame.")
    return uncertainty


def _summary(*, hypotheses: list[dict[str, object]], policy: dict[str, object]) -> str:
    if not hypotheses:
        return "No active mental-state hypotheses"
    labels = ", ".join(str(h.get("label") or "") for h in hypotheses[:3])
    return f"{labels}; policy={policy.get('response_mode') or 'ordinary-collaboration'}"
