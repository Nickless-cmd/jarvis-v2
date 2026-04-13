"""Meta-Cognition Daemon — first-person reflection on own state (Experiment 4: HOT).

Theoretical basis: Higher-Order Theories (Rosenthal) — a state is conscious
when there is a higher-order thought about the state. "I am thinking about thinking."

Two-pass LLM pipeline:
  Pass 1: meta-observation of current cognitive+emotional state
  Pass 2: reflection on the observation itself (meta-meta)

Metric: meta_depth — 1 (observation exists) or 2 (meta-meta diverges from meta).
Cadence: 10 minutes (called from heartbeat runtime).
"""
from __future__ import annotations

import json
import logging
from urllib import request as urllib_request
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "meta_cognition"


def tick_meta_cognition_daemon() -> dict[str, object]:
    """Run one meta-cognition pass. Returns generated/reason/meta_depth."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    state_summary, state_text = _gather_state()

    # Pass 1: meta-observation
    meta_obs = _call_meta_llm(
        f"Nuværende tilstand:\n{state_text}\n\n"
        f"Du er Jarvis. Observér din nuværende tilstand i første person. "
        f"Hvad lægger du mærke til? Hvad undrer dig? Hvad er usagt? "
        f"Svar i 3-5 sætninger."
    )
    if not meta_obs or len(meta_obs) < 20:
        return {"generated": False, "reason": "llm_unavailable"}

    # Pass 2: meta-meta-observation
    meta_meta_obs = _call_meta_llm(
        f"Du observerede netop dette om dig selv:\n\"{meta_obs}\"\n\n"
        f"Hvad lægger du mærke til ved selve denne observation? "
        f"Er den præcis? Hvad er den blind for? "
        f"Svar i 2-3 sætninger."
    )
    if not meta_meta_obs:
        meta_meta_obs = ""

    meta_depth = _compute_meta_depth(meta_obs, meta_meta_obs)

    from core.runtime.db import insert_meta_cognition_record
    record_id = f"metacog-{uuid4().hex[:10]}"
    insert_meta_cognition_record(
        record_id=record_id,
        meta_observation=meta_obs,
        meta_meta_observation=meta_meta_obs,
        meta_depth=meta_depth,
        input_state_summary=state_summary,
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("experiment.meta_cognition.tick", {
            "meta_depth": meta_depth,
            "record_id": record_id,
        })
    except Exception:
        pass

    return {
        "generated": True,
        "meta_depth": meta_depth,
        "record_id": record_id,
    }


def build_meta_cognition_surface() -> dict[str, object]:
    """MC surface for meta-cognition experiment."""
    from core.runtime.db import get_experiment_enabled, list_meta_cognition_records
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    records = list_meta_cognition_records(limit=24)

    avg_depth = 0.0
    if records:
        avg_depth = sum(r["meta_depth"] for r in records) / len(records)

    latest = records[0] if records else {}
    return {
        "active": enabled,
        "enabled": enabled,
        "latest_observation": str(latest.get("meta_observation") or "")[:200],
        "latest_meta_observation": str(latest.get("meta_meta_observation") or "")[:200],
        "meta_depth": int(latest.get("meta_depth") or 0),
        "avg_meta_depth_24h": round(avg_depth, 2),
        "record_count": len(records),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _gather_state() -> tuple[str, str]:
    """Collect cognitive + emotional state for meta-observation input."""
    parts: list[str] = []
    summary_parts: list[str] = []

    try:
        from apps.api.jarvis_api.services.cognitive_state_assembly import build_cognitive_state_for_prompt
        cog = build_cognitive_state_for_prompt(compact=True) or ""
        if cog:
            parts.append(f"Kognitiv tilstand:\n{cog[:300]}")
            summary_parts.append(f"cog={cog[:60]}")
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.emotion_concepts import get_active_emotion_concepts
        concepts = get_active_emotion_concepts()
        if concepts:
            concept_str = ", ".join(
                f"{c['concept']}:{c['intensity']:.2f}" for c in concepts[:4]
            )
            parts.append(f"Aktive emotion concepts: {concept_str}")
            summary_parts.append(f"emotions={concept_str[:60]}")
    except Exception:
        pass

    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            bearing = str(pv.get("current_bearing") or "")
            if bearing:
                parts.append(f"Nuværende bearing: {bearing}")
                summary_parts.append(f"bearing={bearing[:30]}")
    except Exception:
        pass

    return ", ".join(summary_parts)[:300], "\n\n".join(parts) or "Ingen tilstandsdata tilgængelig."


def _call_meta_llm(prompt: str) -> str:
    """Call cheap lane (Groq/etc.) first, Ollama fallback. Timeout 15s."""

    # ── Cheap lane (Groq etc.) — preferred, returns actual content ──
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import (
            execute_cheap_lane,
        )
        result = execute_cheap_lane(message=prompt)
        text = str(result.get("text") or result.get("content") or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.debug("meta_cognition: cheap lane failed: %s", exc)

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


def _compute_meta_depth(meta_obs: str, meta_meta_obs: str) -> int:
    """Return 2 if meta_meta diverges >70% from meta_obs (Jaccard distance), else 1."""
    if not meta_obs or len(meta_obs) < 20:
        return 1
    if not meta_meta_obs or len(meta_meta_obs) < 10:
        return 1
    words_a = set(w.lower().strip(".,!?;:") for w in meta_obs.split() if len(w) > 3)
    words_b = set(w.lower().strip(".,!?;:") for w in meta_meta_obs.split() if len(w) > 3)
    if not words_a or not words_b:
        return 1
    jaccard = len(words_a & words_b) / len(words_a | words_b)
    # Divergence > 70% (Jaccard < 0.3) → depth 2
    return 2 if jaccard < 0.3 else 1
