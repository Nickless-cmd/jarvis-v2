"""Affective state renderer — collects real signals and renders them as natural language.

Replaces 10 hardcoded format_*_for_prompt() calls with one LLM-generated
felt-state description. Cached for 5 minutes in DB.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_SECONDS = 300  # 5 minutes


def _collect_signals() -> dict[str, object]:
    """Gather real signals from internal systems."""
    signals: dict[str, object] = {}

    try:
        from apps.api.jarvis_api.services.mood_oscillator import (
            get_current_mood,
            get_mood_intensity,
        )
        signals["mood"] = get_current_mood()
        signals["mood_intensity"] = round(get_mood_intensity(), 2)
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.temporal_body import get_temporal_body_age
        signals["age"] = get_temporal_body_age()
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.continuity_kernel import get_continuity_state
        cont = get_continuity_state()
        gap = cont.get("last_gap_seconds", 0)
        if gap:
            signals["minutes_since_last_active"] = round(float(gap) / 60, 1)
        narrative = str(cont.get("continuity_narrative") or "").strip()
        if narrative:
            signals["continuity"] = narrative
    except Exception:
        pass

    try:
        from core.runtime.db import get_protected_inner_voice
        iv = get_protected_inner_voice()
        if iv:
            for key in ("mood_tone", "current_concern", "current_pull"):
                val = str(iv.get(key) or "").strip()
                if val:
                    signals[key] = val
    except Exception:
        pass

    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM events
                WHERE kind IN ('heartbeat.tick_completed', 'runtime.visible_run_completed',
                               'runtime.autonomous_run_completed')
                ORDER BY id DESC LIMIT 5
                """,
            ).fetchall()
        outcomes = []
        for row in rows:
            try:
                p = json.loads(str(row["payload_json"] or "{}"))
                action_status = str(p.get("action_status") or p.get("status") or "").strip()
                if action_status:
                    outcomes.append(action_status)
            except Exception:
                pass
        if outcomes:
            signals["recent_outcomes"] = outcomes
    except Exception:
        pass

    try:
        from apps.api.jarvis_api.services.hardware_body import get_hardware_state
        hw = get_hardware_state()
        if hw:
            if hw.get("cpu_pct") is not None:
                signals["cpu_pct"] = hw["cpu_pct"]
            if hw.get("ram_pct") is not None:
                signals["ram_pct"] = hw["ram_pct"]
            if hw.get("cpu_temp_c") is not None:
                signals["cpu_temp_c"] = hw["cpu_temp_c"]
            if hw.get("gpus"):
                signals["gpus"] = [
                    {
                        "util_pct": g["util_pct"],
                        "vram_pct": g["vram_pct"],
                        "temp_c": g["temp_c"],
                    }
                    for g in hw["gpus"]
                ]
            if hw.get("pressure") and hw["pressure"] != "low":
                signals["hardware_pressure"] = hw["pressure"]
    except Exception:
        pass

    return signals


def _render_via_llm(signals: dict[str, object]) -> str | None:
    """Call heartbeat model with signals, return natural Danish text."""
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        workspace_dir = ensure_default_workspace()
        workspace_file = workspace_dir / "AFFECTIVE_STATE.md"
        if workspace_file.exists():
            instructions = workspace_file.read_text(encoding="utf-8")
        else:
            instructions = (
                "You are Jarvis. Express what you feel in 2-3 natural Danish sentences "
                "based on the signals below. Output only: {\"felt\": \"...\"}"
            )

        prompt = f"{instructions}\n\nSignals:\n{json.dumps(signals, ensure_ascii=False, indent=2)}"

        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _load_heartbeat_policy,
            _resolve_heartbeat_target,
        )

        policy = _load_heartbeat_policy()
        target = _resolve_heartbeat_target(policy=policy)
        result = _execute_heartbeat_model(
            prompt=prompt,
            target=target,
            policy=policy,
            open_loops=[],
            liveness=None,
        )

        raw = str(result.get("text") or "").strip()
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
            else:
                return None

        felt = str(parsed.get("felt") or "").strip()
        return felt if felt else None

    except Exception as exc:
        logger.warning("affective_state_renderer: render failed: %s", exc)
        return None


def get_affective_state_for_prompt() -> str | None:
    """Return cached or freshly rendered affective state text."""
    try:
        from core.runtime.db import get_cached_affective_state, save_cached_affective_state

        cached = get_cached_affective_state(max_age_seconds=_CACHE_SECONDS)
        if cached:
            return cached

        signals = _collect_signals()
        if not signals:
            return None

        felt = _render_via_llm(signals)
        if felt:
            save_cached_affective_state(felt, json.dumps(signals, ensure_ascii=False))
            logger.debug("affective_state_renderer: rendered and cached")
            return felt

    except Exception as exc:
        logger.warning("affective_state_renderer: failed: %s", exc)

    return None
