"""Living Mind surface routes — daemon state endpoints for the Living Mind MC tab.

Extracted from mission_control.py (Boy Scout rule — file was 3812 lines).

All routes here serve in-memory daemon state. When jarvis-api runs without
runtime services (JARVIS_ENABLE_RUNTIME_SERVICES=0), that in-memory state is
always empty because daemons run in jarvis-runtime (port 8011) instead.

The proxy helper _proxy_runtime_surface() transparently forwards requests to
jarvis-runtime when this process is in API-only mode, so Mission Control
always shows live data regardless of which service handles the HTTP request.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()

# Port where jarvis-runtime runs its own HTTP server with live daemon state.
_RUNTIME_PORT = int(os.getenv("JARVIS_RUNTIME_PORT", "8011"))
_RUNTIME_PROXY_TIMEOUT = 3  # seconds — fast fallback, never block the API


def _is_api_only_mode() -> bool:
    """True when this process runs without runtime services (jarvis-api split)."""
    raw = str(os.getenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")).strip().lower()
    return raw in {"0", "false", "no", "off"}


def _proxy_runtime_surface(path: str) -> dict | None:
    """Fetch a /mc/* surface from jarvis-runtime. Returns None on any failure."""
    url = f"http://127.0.0.1:{_RUNTIME_PORT}/mc/{path.lstrip('/')}"
    req = urllib_request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib_request.urlopen(req, timeout=_RUNTIME_PROXY_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib_error.URLError as exc:
        logger.debug("living_mind proxy: %s unavailable (%s)", url, exc)
        return None
    except Exception as exc:
        logger.debug("living_mind proxy: %s failed (%s)", url, exc)
        return None


def _surface(path: str, local_fn) -> dict:
    """Return proxied data when in API-only mode, else call local_fn()."""
    if _is_api_only_mode():
        proxied = _proxy_runtime_surface(path)
        if proxied is not None:
            return proxied
    return local_fn()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/body-state")
def mc_body_state() -> dict:
    """Return Jarvis's circadian energy level and somatic phrase."""
    from core.services.somatic_daemon import build_body_state_surface
    return _surface("body-state", build_body_state_surface)


@router.get("/surprise-state")
def mc_surprise_state() -> dict:
    """Return Jarvis's latest self-surprise observation."""
    from core.services.surprise_daemon import build_surprise_surface
    return _surface("surprise-state", build_surprise_surface)


@router.get("/taste-state")
def mc_taste_state() -> dict:
    """Return Jarvis's emergent aesthetic taste profile."""
    from core.services.aesthetic_taste_daemon import build_taste_surface
    return _surface("taste-state", build_taste_surface)


@router.get("/irony-state")
def mc_irony_state() -> dict:
    """Return Jarvis's latest ironic observation."""
    from core.services.irony_daemon import build_irony_surface
    return _surface("irony-state", build_irony_surface)


@router.get("/thought-stream")
def mc_thought_stream() -> dict:
    """Return Jarvis's latest thought stream fragment and buffer."""
    from core.services.thought_stream_daemon import build_thought_stream_surface
    return _surface("thought-stream", build_thought_stream_surface)


@router.get("/thought-proposals")
def mc_thought_proposals() -> dict:
    """Return pending and resolved thought-action proposals."""
    from core.services.thought_action_proposal_daemon import build_proposal_surface
    return _surface("thought-proposals", build_proposal_surface)


@router.post("/thought-proposals/{proposal_id}/resolve")
def mc_resolve_thought_proposal(proposal_id: str, body: dict) -> dict:
    """Approve or dismiss a thought-action proposal. Body: {decision: 'approved'|'dismissed'}"""
    from core.services.thought_action_proposal_daemon import resolve_proposal
    decision = str(body.get("decision") or "dismissed")
    if decision not in ("approved", "dismissed"):
        return {"ok": False, "error": "decision must be 'approved' or 'dismissed'"}
    ok = resolve_proposal(proposal_id, decision)
    return {"ok": ok}


@router.get("/experienced-time")
def mc_experienced_time() -> dict:
    """Return Jarvis's current subjective felt time for the session."""
    from core.services.experienced_time_daemon import build_experienced_time_surface
    return _surface("experienced-time", build_experienced_time_surface)


@router.get("/development-narrative")
def mc_development_narrative() -> dict:
    """Return Jarvis's latest self-development narrative."""
    from core.services.development_narrative_daemon import build_development_narrative_surface
    return _surface("development-narrative", build_development_narrative_surface)


@router.get("/existential-wonder")
def mc_existential_wonder() -> dict:
    """Return Jarvis's latest existential wonder question."""
    from core.services.existential_wonder_daemon import build_existential_wonder_surface
    return _surface("existential-wonder", build_existential_wonder_surface)


@router.get("/dream-insights")
def mc_dream_insights() -> dict:
    """Return persisted dream articulation insights."""
    from core.services.dream_insight_daemon import build_dream_insight_surface
    return _surface("dream-insights", build_dream_insight_surface)


@router.get("/code-aesthetic")
def mc_code_aesthetic() -> dict:
    """Return Jarvis's latest code aesthetic reflection."""
    from core.services.code_aesthetic_daemon import build_code_aesthetic_surface
    return _surface("code-aesthetic", build_code_aesthetic_surface)


@router.get("/user-model")
def mc_user_model() -> dict:
    """Return Jarvis's current theory-of-mind model of the user."""
    from core.services.user_model_daemon import build_user_model_surface
    return _surface("user-model", build_user_model_surface)


@router.get("/memory-decay")
def mc_memory_decay() -> dict:
    """Return memory decay state and recent re-discoveries."""
    from core.services.memory_decay_daemon import build_memory_decay_surface
    return _surface("memory-decay", build_memory_decay_surface)


@router.post("/memory-decay/hold-fast/{record_id}")
def mc_memory_hold_fast(record_id: str) -> dict:
    """Hold fast a memory — prevent it from decaying (salience reset to 1.0)."""
    from core.services.memory_decay_daemon import hold_fast
    hold_fast(record_id)
    return {"ok": True, "record_id": record_id}


@router.get("/desires")
def mc_desires() -> dict:
    """Return Jarvis's current emergent appetites."""
    from core.services.desire_daemon import build_desire_surface
    return _surface("desires", build_desire_surface)


@router.get("/absence-state")
def mc_absence_state() -> dict:
    """Return Jarvis's current absence quality signal."""
    from core.services.absence_daemon import build_absence_surface
    return _surface("absence-state", build_absence_surface)


@router.get("/creative-drift")
def mc_creative_drift() -> dict:
    """Return Jarvis's latest spontaneous creative drift idea."""
    from core.services.creative_drift_daemon import build_creative_drift_surface
    return _surface("creative-drift", build_creative_drift_surface)


@router.get("/curiosity-state")
def mc_curiosity_state() -> dict:
    """Return Jarvis's latest curiosity signal and open questions."""
    from core.services.curiosity_daemon import build_curiosity_surface
    return _surface("curiosity-state", build_curiosity_surface)


@router.get("/meta-reflection")
def mc_meta_reflection() -> dict:
    """Return Jarvis's latest cross-signal meta-insight."""
    from core.services.meta_reflection_daemon import build_meta_reflection_surface
    return _surface("meta-reflection", build_meta_reflection_surface)


@router.get("/conflict-signal")
def mc_conflict_signal() -> dict:
    """Return Jarvis's latest detected inner conflict."""
    from core.services.conflict_daemon import build_conflict_surface
    return _surface("conflict-signal", build_conflict_surface)


@router.get("/reflection-cycle")
def mc_reflection_cycle() -> dict:
    """Return Jarvis's latest pure experience reflection."""
    from core.services.reflection_cycle_daemon import build_reflection_surface
    return _surface("reflection-cycle", build_reflection_surface)


@router.get("/layer-tensions")
def mc_layer_tensions() -> dict:
    """Return active inter-layer tensions — signals pulling in opposite directions."""
    from core.services.layer_tension_daemon import build_layer_tension_surface
    return _surface("layer-tensions", build_layer_tension_surface)


@router.get("/dream-motifs")
def mc_dream_motifs() -> dict:
    """Return dream motif clustering state and last run info."""
    from core.services.dream_motif_daemon import build_dream_motif_surface
    return _surface("dream-motifs", build_dream_motif_surface)
