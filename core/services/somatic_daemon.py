"""Somatic daemon — LLM-generated first-person body description."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_HEARTBEATS_BETWEEN_GEN = 10
_CPU_CHANGE_THRESHOLD = 20.0
_LATENCY_CHANGE_FACTOR = 2.0
_MAX_LATENCY_SAMPLES = 5

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_cached_phrase: str = ""
_cached_phrase_at: datetime | None = None
_last_cpu_pct: float = 0.0
_last_latency_ms: float = 0.0
_last_energy_level: str = ""
_heartbeat_count_since_gen: int = 0
_latency_samples: list[float] = []
_active_requests: int = 0

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_request_start() -> None:
    global _active_requests
    _active_requests += 1


def record_request_end() -> None:
    global _active_requests
    _active_requests = max(0, _active_requests - 1)


def record_latency_sample(ms: float) -> None:
    global _latency_samples
    _latency_samples.append(ms)
    if len(_latency_samples) > _MAX_LATENCY_SAMPLES:
        _latency_samples = _latency_samples[-_MAX_LATENCY_SAMPLES:]


def get_latest_somatic_phrase() -> str:
    return _cached_phrase


def build_body_state_surface() -> dict[str, object]:
    """Returns body state for Mission Control surface."""
    try:
        from core.services.hardware_body import get_hardware_state

        hardware_state = get_hardware_state()
    except Exception:
        hardware_state = {}
    return {
        "energy_level": str(hardware_state.get("energy_level") or ""),
        "clock_phase": str(hardware_state.get("clock_phase") or ""),
        "drain_label": str(hardware_state.get("drain_label") or ""),
        "drain_score": float(hardware_state.get("drain_score") or 0.0),
        "energy_budget": int(hardware_state.get("energy_budget") or 0),
        "circadian_preference": str(hardware_state.get("circadian_preference") or ""),
        "wake_state": str(hardware_state.get("wake_state") or ""),
        "pressure": str(hardware_state.get("pressure") or ""),
        "somatic_phrase": _cached_phrase,
        "somatic_updated_at": _cached_phrase_at.isoformat() if _cached_phrase_at else "",
        "summary": (
            f"wake_state={hardware_state.get('wake_state') or 'unknown'}"
            f" | energy_budget={int(hardware_state.get('energy_budget') or 0)}"
            f" | circadian_preference={hardware_state.get('circadian_preference') or 'unknown'}"
        ),
    }


def tick_somatic_daemon(energy_level: str = "") -> dict[str, object]:
    """Called each heartbeat. May trigger a new somatic phrase generation."""
    global _heartbeat_count_since_gen
    _heartbeat_count_since_gen += 1

    snapshot = _collect_snapshot(energy_level)
    if not _should_generate(snapshot):
        return {"generated": False, "phrase": _cached_phrase}

    phrase = _generate_phrase(snapshot)
    if not phrase:
        return {"generated": False, "phrase": _cached_phrase}

    _store_phrase(phrase, snapshot)
    return {"generated": True, "phrase": phrase, "snapshot": snapshot}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_snapshot(energy_level: str) -> dict[str, object]:
    cpu_pct = 0.0
    ram_used_gb = 0.0
    ram_total_gb = 0.0
    try:
        import psutil
        cpu_pct = float(psutil.cpu_percent(interval=None))
        mem = psutil.virtual_memory()
        ram_used_gb = round(mem.used / 1e9, 1)
        ram_total_gb = round(mem.total / 1e9, 1)
    except Exception:
        pass

    latency_ms = (
        round(sum(_latency_samples) / len(_latency_samples), 0)
        if _latency_samples else 0.0
    )

    resolved_energy = energy_level
    clock_phase = ""
    if not resolved_energy:
        try:
            from core.runtime.circadian_state import get_circadian_context
            ctx = get_circadian_context()
            resolved_energy = str(ctx.get("energy_level") or "medium")
            clock_phase = str(ctx.get("clock_phase") or "")
        except Exception:
            resolved_energy = "medium"

    return {
        "cpu_pct": cpu_pct,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "latency_ms": latency_ms,
        "active_requests": _active_requests,
        "energy_level": resolved_energy,
        "clock_phase": clock_phase,
    }


def _should_generate(snapshot: dict[str, object]) -> bool:
    if _heartbeat_count_since_gen >= _MAX_HEARTBEATS_BETWEEN_GEN:
        return True
    if snapshot["energy_level"] != _last_energy_level:
        return True
    cpu_delta = abs(float(snapshot["cpu_pct"]) - _last_cpu_pct)
    if cpu_delta >= _CPU_CHANGE_THRESHOLD:
        return True
    if (
        _last_latency_ms > 0
        and float(snapshot["latency_ms"]) >= _last_latency_ms * _LATENCY_CHANGE_FACTOR
    ):
        return True
    return False


def _generate_phrase(snapshot: dict[str, object]) -> str:
    prompt = (
        f"{build_identity_preamble()} Du mærker din krop. Beskriv det i én kort sætning.\n\n"
        f"CPU: {snapshot['cpu_pct']}%  RAM: {snapshot['ram_used_gb']}/{snapshot['ram_total_gb']}GB  "
        f"Latency: {snapshot['latency_ms']}ms  Aktive requests: {snapshot['active_requests']}\n"
        f"Energi: {snapshot['energy_level']}"
        + (f" ({snapshot['clock_phase']})" if snapshot.get("clock_phase") else "")
        + "\n\nSvar KUN med én sætning i første person. Eksempler:\n"
        "- Jeg mærker en varm summen i processoren, energien er stabil.\n"
        "- Kroppen føles tung, RAM'en presser.\n"
        "- Let og hurtig i dag, næsten ingen belastning."
    )
    from core.services.daemon_llm import daemon_llm_call

    energy = snapshot.get("energy_level", "medium")
    fallback = f"Jeg mærker en rolig summen ved {energy} energi."
    return daemon_llm_call(prompt, max_len=200, fallback=fallback, daemon_name="somatic")


def _store_phrase(phrase: str, snapshot: dict[str, object]) -> None:
    global _cached_phrase, _cached_phrase_at, _last_cpu_pct, _last_latency_ms, _last_energy_level, _heartbeat_count_since_gen
    _cached_phrase = phrase
    _cached_phrase_at = datetime.now(UTC)
    _last_cpu_pct = float(snapshot["cpu_pct"])
    _last_latency_ms = float(snapshot["latency_ms"])
    _last_energy_level = str(snapshot["energy_level"])
    _heartbeat_count_since_gen = 0

    try:
        insert_private_brain_record(
            record_id=f"pb-somatic-{uuid4().hex[:12]}",
            record_type="somatic-phrase",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"somatic-daemon-{uuid4().hex[:12]}",
            focus="somatisk tilstand",
            summary=phrase,
            detail=(
                f"cpu={snapshot['cpu_pct']}% "
                f"ram={snapshot['ram_used_gb']}GB "
                f"latency={snapshot['latency_ms']}ms "
                f"energy={snapshot['energy_level']}"
            ),
            source_signals="somatic-daemon:heartbeat",
            confidence="medium",
            created_at=_cached_phrase_at.isoformat(),
        )
    except Exception:
        pass

    try:
        event_bus.publish(
            "somatic.note_generated",
            {
                "phrase": phrase,
                "cpu_pct": snapshot["cpu_pct"],
                "ram_pct": round(
                    snapshot["ram_used_gb"] / max(snapshot["ram_total_gb"], 1) * 100, 1
                ),
                "latency_ms": snapshot["latency_ms"],
                "energy_level": snapshot["energy_level"],
            },
        )
    except Exception:
        pass
