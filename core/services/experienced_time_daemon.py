"""Experienced time daemon — tracks subjective felt duration of the current session."""
from __future__ import annotations

from datetime import UTC, datetime

_session_start_at: datetime | None = None
_session_event_count: int = 0
_session_novelty_count: int = 0
_felt_duration_label: str = ""

_INTENSITY_MAP: dict[str, float] = {
    "høj": 1.3,
    "medium": 1.0,
    "lav": 0.8,
    "udmattet": 0.6,
}

# Fase 2 / Lag 1 — rå-signal-mode. Når flaget er TÆNDT emitter daemonen de
# rå metrics (ur-tid + aktivitets-tæthed) som frase i stedet for at kalde
# narrations-LLM'en (_generate_felt_label). Default OFF, runtime-state-tunbar,
# self-safe → False ved fejl. Jarvis' oplevelse ændrer sig ikke før owner flipper.
_RAW_SIGNAL_MODE_FLAG = "raw_signal_mode"


def raw_signal_mode_enabled() -> bool:
    """Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state.

    Self-safe → False ved enhver fejl (Jarvis' oplevelse må aldrig gå i stykker
    fordi et flag-opslag fejler).
    """
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_RAW_SIGNAL_MODE_FLAG, False)
        return False if v is None else bool(v)
    except Exception:
        return False


def _build_raw_felt(*, base_minutes: float, density_factor: float) -> str:
    """Byg felt-strengen udelukkende fra rå metrics — ingen LLM.

    ur-tid = faktiske minutter siden session-start. aktivitet = tæthed 0-1
    (density_factor ligger i 1.0-2.0 → normaliseres til 0-1). Fx ``ur-tid 47min · aktivitet 0.3``.
    """
    density_0_1 = max(0.0, min(1.0, density_factor - 1.0))
    return f"ur-tid {base_minutes:.0f}min · aktivitet {density_0_1:.1f}"


def tick_experienced_time_daemon(
    event_count: int,
    new_signal_count: int,
    energy_level: str,
) -> dict[str, object]:
    """Update experienced time state.
    event_count: number of active signals this tick.
    new_signal_count: number of genuinely new signals (novelty).
    energy_level: somatic energy (høj/medium/lav/udmattet)."""
    global _session_start_at, _session_event_count, _session_novelty_count, _felt_duration_label

    now = datetime.now(UTC)
    if _session_start_at is None:
        _session_start_at = now

    _session_event_count += max(0, event_count)
    _session_novelty_count += max(0, new_signal_count)

    base_minutes = (now - _session_start_at).total_seconds() / 60
    density_factor = min(2.0, 1.0 + _session_event_count / 100)
    novelty_factor = min(1.5, 1.0 + _session_novelty_count / 10)
    intensity_factor = _INTENSITY_MAP.get(energy_level, 1.0)
    felt_minutes = base_minutes * density_factor * novelty_factor * intensity_factor

    # Fase 2 / Lag 1 — rå tal, ikke LLM-label. Bygger felt-strengen direkte fra
    # metrics og SPRINGER narrations-LLM-kaldet over. Samme output-felt (felt_label),
    # så awareness/prompt-consumeren mærker kun at STRENGEN skifter.
    if raw_signal_mode_enabled():
        _felt_duration_label = _build_raw_felt(
            base_minutes=base_minutes,
            density_factor=density_factor,
        )
    else:
        _felt_duration_label = _generate_felt_label(
            felt_minutes=felt_minutes,
            event_count=_session_event_count,
            novelty_count=_session_novelty_count,
            energy_level=energy_level,
        )

    return {
        "felt_minutes": felt_minutes,
        "felt_label": _felt_duration_label,
        "session_event_count": _session_event_count,
    }


def _label(felt_minutes: float) -> str:
    if felt_minutes < 15:
        return "meget kort"
    if felt_minutes < 30:
        return "kort"
    if felt_minutes < 90:
        return "normal"
    if felt_minutes < 180:
        return "lang"
    return "meget lang"


def _generate_felt_label(
    *,
    felt_minutes: float,
    event_count: int,
    novelty_count: int,
    energy_level: str,
) -> str:
    from core.services.daemon_llm import daemon_public_safe_llm_call

    fallback = _label(felt_minutes)
    prompt = "\n".join(
        [
            "Task: classify subjective session duration from structured runtime metrics.",
            "Return exactly one of: meget kort | kort | normal | lang | meget lang",
            f"felt_minutes={round(felt_minutes, 1)}",
            f"event_count={int(event_count)}",
            f"novelty_count={int(novelty_count)}",
            f"energy_level={energy_level}",
        ]
    )
    raw = daemon_public_safe_llm_call(
        prompt,
        max_len=40,
        fallback=fallback,
        daemon_name="experienced_time",
    )
    normalized = " ".join(str(raw or "").strip().lower().split())
    if normalized in {"meget kort", "kort", "normal", "lang", "meget lang"}:
        return normalized
    return fallback


def reset_experienced_time_daemon() -> None:
    """Reset session state (for new session or testing)."""
    global _session_start_at, _session_event_count, _session_novelty_count, _felt_duration_label
    _session_start_at = None
    _session_event_count = 0
    _session_novelty_count = 0
    _felt_duration_label = ""


def build_experienced_time_surface() -> dict:
    if _session_start_at is None:
        base_minutes = 0.0
    else:
        base_minutes = (datetime.now(UTC) - _session_start_at).total_seconds() / 60
    return {
        "felt_label": _felt_duration_label or "meget kort",
        "session_event_count": _session_event_count,
        "session_novelty_count": _session_novelty_count,
        "base_minutes": round(base_minutes, 1),
        "active": _session_start_at is not None,
    }


