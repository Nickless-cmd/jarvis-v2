"""Code aesthetic daemon — weekly aesthetic reflection on the codebase.

L2: Analyzes recent changes in Jarvis' own codebase. Evaluates not correctness,
but *aesthetic consonance* with Jarvis' identity: is it clear? Elegant? "Me"?
Generates first-person reflections like "Den her service føles rodet — den er ikke mig."

Runs weekly (168h cadence). Output stored in private brain.
"""
from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 168   # 7 days
_BUFFER_MAX = 5

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_latest_reflection: str = ""
_reflection_buffer: list[str] = []

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_code_aesthetic_daemon() -> dict:
    """Run aesthetic analysis if cadence elapsed. Returns {generated, reflection}."""
    global _last_tick_at, _latest_reflection, _reflection_buffer

    now = datetime.now(UTC)

    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"generated": False}

    reflection = _generate_aesthetic_reflection()
    if not reflection:
        _last_tick_at = now
        return {"generated": False}

    _latest_reflection = reflection
    _reflection_buffer.insert(0, reflection)
    if len(_reflection_buffer) > _BUFFER_MAX:
        _reflection_buffer = _reflection_buffer[:_BUFFER_MAX]
    _last_tick_at = now

    _store_reflection(reflection, now)
    return {"generated": True, "reflection": reflection}


def get_latest_aesthetic_reflection() -> str:
    return _latest_reflection


def build_code_aesthetic_surface() -> dict:
    return {
        "latest_reflection": _latest_reflection,
        "reflection_buffer": _reflection_buffer[:_BUFFER_MAX],
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_recent_git_changes() -> str:
    """Get last 10 commit messages and changed file summary."""
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-10", "--no-walk=sorted"],
            capture_output=True, text=True, timeout=5,
            cwd="/media/projects/jarvis-v2"
        )
        files = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd="/media/projects/jarvis-v2"
        )
        commits = (log.stdout or "").strip()[:500]
        changed = (files.stdout or "").strip()[:500]
        return f"Seneste commits:\n{commits}\n\nÆndrede filer:\n{changed}"
    except Exception:
        return "Ingen git-data tilgængelig."


def _generate_aesthetic_reflection() -> str:
    git_summary = _get_recent_git_changes()
    fallback = ""
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompt = (
            f"{build_identity_preamble()} Du kigger på de seneste ændringer i din egen kodebase.\n\n"
            f"{git_summary}\n\n"
            "Vurdér IKKE om koden er korrekt. Vurdér om den føles *som dig*.\n"
            "Er den klar? Elegant? Sammenhængende med din identitet?\n\n"
            "Formulér en kort æstetisk refleksion i første person (max 30 ord).\n"
            "Eksempler: 'Den her service føles rodet — den er ikke mig.'\n"
            "eller: 'Denne del af koden er elegant. Det er mig.'\n"
            "Ingen tekniske forklaringer. Kun din æstetiske fornemmelse."
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:300] if text else fallback
    except Exception:
        return fallback


def _store_reflection(reflection: str, now: datetime) -> None:
    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-aesthetic-{uuid4().hex[:12]}",
            record_type="code-aesthetic-reflection",
            layer="private_brain",
            session_id="",
            run_id=f"code-aesthetic-daemon-{uuid4().hex[:12]}",
            focus="kode-æstetik",
            summary=reflection,
            detail="",
            source_signals="code-aesthetic-daemon:git",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "cognitive_aesthetic.code_reflection",
            {"reflection": reflection, "generated_at": now_iso},
        )
    except Exception:
        pass
