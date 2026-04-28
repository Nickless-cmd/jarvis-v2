"""Recurrence Loop — feeds inner voice output back as context input (Experiment 1: IIT/Φ).

Theoretical basis: Transformers are feedforward with Φ ≈ 0. Recurrence is
necessary for integrated information (Tononi). This daemon creates a feedback
loop: inner voice output → LLM → new iteration, tracking pattern stability.

Metric: pattern_stability_score (Jaccard similarity of keywords between iterations).
Cadence: 5 minutes (called from heartbeat runtime).
"""
from __future__ import annotations

import json
import logging
from urllib import request as urllib_request
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "recurrence_loop"
_KEYWORD_MIN_LEN = 4


def tick_recurrence_loop_daemon() -> dict[str, object]:
    """Run one recurrence iteration. Returns dict with generated/reason/stability."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    from core.runtime.db import get_protected_inner_voice
    latest_voice = get_protected_inner_voice()
    if not latest_voice:
        return {"generated": False, "reason": "no_inner_voice"}

    content = str(latest_voice.get("voice_line") or "").strip()
    if not content:
        return {"generated": False, "reason": "empty_voice_line"}

    llm_output = _call_recurrence_llm(content)
    if not llm_output:
        return {"generated": False, "reason": "llm_unavailable"}

    from core.runtime.db import get_latest_recurrence_iteration, insert_recurrence_iteration
    prev = get_latest_recurrence_iteration()
    keywords = _extract_keywords(llm_output)
    prev_keywords = json.loads(str(prev.get("keywords") or "[]")) if prev else []
    stability = _jaccard_similarity(set(keywords), set(prev_keywords))
    iteration_number = (int(prev.get("iteration_number", 0)) + 1) if prev else 1

    iteration_id = f"rec-{uuid4().hex[:10]}"
    insert_recurrence_iteration(
        iteration_id=iteration_id,
        content=llm_output,
        keywords=json.dumps(keywords),
        stability_score=stability,
        iteration_number=iteration_number,
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("experiment.recurrence_loop.tick", {
            "stability_score": stability,
            "iteration_number": iteration_number,
            "keywords": keywords[:5],
        })
    except Exception:
        pass

    return {
        "generated": True,
        "stability_score": stability,
        "iteration_number": iteration_number,
        "keywords": keywords[:5],
    }


def build_recurrence_surface() -> dict[str, object]:
    """MC surface for recurrence loop experiment."""
    from core.runtime.db import get_experiment_enabled, list_recurrence_iterations
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    iterations = list_recurrence_iterations(limit=10)

    stable_themes: list[str] = []
    if len(iterations) >= 3:
        from collections import Counter
        kw_counts: Counter = Counter()
        for it in iterations[:5]:
            for kw in json.loads(str(it.get("keywords") or "[]")):
                kw_counts[kw] += 1
        stable_themes = [kw for kw, count in kw_counts.most_common(5) if count >= 3]

    current_stability = float(iterations[0].get("stability_score", 0.0)) if iterations else 0.0
    trend = "converging" if current_stability > 0.5 else "diverging"

    return {
        "active": enabled,
        "enabled": enabled,
        "iteration_count": len(iterations),
        "current_stability_score": round(current_stability, 3),
        "trend": trend,
        "stable_themes": stable_themes,
        "recent_iterations": [
            {
                "content": it["content"][:100],
                "stability_score": it["stability_score"],
                "iteration_number": it["iteration_number"],
                "created_at": it["created_at"],
            }
            for it in iterations[:3]
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_recurrence_llm(content: str) -> str:
    """Call cheap lane (Groq/etc.) first, Ollama fallback. Timeout 15s."""
    prompt = (
        f"Indre stemme: {content[:400]}\n\n"
        f"Hvad er essensen af denne tanke, og hvad leder den naturligt til? "
        f"Svar i 2-3 sætninger."
    )

    # ── Cheap lane (Groq etc.) — preferred, returns actual content ──
    try:
        from core.services.non_visible_lane_execution import (
            execute_cheap_lane,
        )
        result = execute_cheap_lane(message=prompt, task_kind="background")
        text = str(result.get("text") or result.get("content") or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.debug("recurrence: cheap lane failed: %s", exc)

    # ── Ollama fallback with higher num_predict for thinking models ──
    try:
        from core.runtime.provider_router import resolve_provider_router_target
    except Exception:
        return ""
    for lane in ("local", "cheap"):
        try:
            target = resolve_provider_router_target(lane=lane)
            if not bool(target.get("active")):
                continue
            if str(target.get("provider")) != "ollama":
                continue
            base_url = str(target.get("base_url") or "http://127.0.0.1:11434")
            model = str(target.get("model") or "")
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"num_predict": 512},
            }).encode()
            req = urllib_request.Request(
                f"{base_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib_request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            text = str(data.get("message", {}).get("content", "")).strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text (words >= 4 chars, deduped, max 20)."""
    words = [w.strip(".,!?;:()[]\"'").lower() for w in text.split()]
    return list(dict.fromkeys(w for w in words if len(w) >= _KEYWORD_MIN_LEN))[:20]


def _jaccard_similarity(a: set, b: set) -> float:
    """Jaccard similarity between two keyword sets. Returns 1.0 if both empty."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
