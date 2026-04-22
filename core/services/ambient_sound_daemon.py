"""Ambient Sound daemon — Layer 6½: background acoustic context.

Per roadmap v6/v7 (Jarvis' forslag, bekræftet af Claude):
  "Lag 6½: 4 gange om dagen, 10 sekunders lydniveau-sample, metadata-only.
  Ingen indhold gemmes — kun nøgle-ratio (talk/silence/music/noise)."

PRIVACY: No audio content is stored. The daemon captures only numeric
amplitude statistics and classifies them into categories. The raw audio
buffer is discarded immediately after classification.

Requires `sounddevice` (optional dep). If unavailable, daemon silently skips.
If microphone is not accessible (permission denied, no device), same.

Categories: talk, music, silence, noise, mixed
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, insert_private_brain_record, set_runtime_state_value

logger = logging.getLogger(__name__)

_STATE_KEY = "ambient_sound_daemon.state"
_SAMPLE_DURATION_SECONDS = 10
_SAMPLES_PER_DAY = 4
_COOLDOWN_HOURS = 24 / _SAMPLES_PER_DAY  # 6 hours between samples
_BUFFER_MAX = 50


def tick_ambient_sound_daemon() -> dict[str, object]:
    """Sample ambient audio level and classify. Runs 4x/day."""
    if not _experiment_enabled():
        return {"generated": False, "reason": "disabled"}

    state = _state()
    now = datetime.now(UTC)
    last_sample = _parse_iso(str(state.get("last_sample_at") or ""))
    if last_sample is not None:
        if (now - last_sample) < timedelta(hours=_COOLDOWN_HOURS):
            return {"generated": False, "reason": "cooldown"}

    category, amplitude_mean, amplitude_std = _capture_sample()
    if category is None:
        return {"generated": False, "reason": "no_audio_device"}

    sample = {
        "sampled_at": now.isoformat(),
        "category": category,
        "amplitude_mean": round(amplitude_mean, 4),
        "amplitude_std": round(amplitude_std, 4),
    }

    # Update state
    history = list(state.get("history") or [])
    history.insert(0, sample)
    if len(history) > _BUFFER_MAX:
        history = history[:_BUFFER_MAX]

    new_state = {
        "last_sample_at": now.isoformat(),
        "last_category": category,
        "history": history,
    }
    set_runtime_state_value(_STATE_KEY, new_state)

    _store_sample(sample, now)

    return {
        "generated": True,
        "category": category,
        "amplitude_mean": amplitude_mean,
    }


def _capture_sample() -> tuple[str | None, float, float]:
    """Record 10 seconds of audio, classify. Returns (category, mean, std) or (None, 0, 0)."""
    try:
        import numpy as np
        import sounddevice as sd

        samples = sd.rec(
            int(_SAMPLE_DURATION_SECONDS * 44100),
            samplerate=44100,
            channels=1,
            dtype="float32",
            blocking=True,
        )
        # Raw buffer discarded after stats
        amplitude = np.abs(samples.flatten())
        mean = float(amplitude.mean())
        std = float(amplitude.std())
        category = _classify(mean, std)
        return category, mean, std
    except ImportError:
        logger.debug("ambient_sound: sounddevice not available")
        return None, 0.0, 0.0
    except Exception as exc:
        logger.debug("ambient_sound: capture failed: %s", exc)
        return None, 0.0, 0.0


def _classify(mean: float, std: float) -> str:
    """Classify amplitude stats into acoustic category. No content analysis."""
    if mean < 0.005:
        return "silence"
    if mean < 0.02:
        return "silence" if std < 0.01 else "noise"
    # Moderate amplitude
    if std / (mean + 1e-9) < 0.5:
        # Low variation relative to mean → sustained sound (music or hum)
        return "music"
    # High variation → speech or noise
    if mean > 0.05:
        return "talk"
    return "mixed"


def _store_sample(sample: dict, now: datetime) -> None:
    now_iso = now.isoformat()
    category = str(sample.get("category") or "")
    amplitude = float(sample.get("amplitude_mean") or 0)
    try:
        insert_private_brain_record(
            record_id=f"pb-ambient-{uuid4().hex[:12]}",
            record_type="ambient-sound",
            layer="lag_6_half",
            session_id="heartbeat",
            run_id=f"ambient-sound-{uuid4().hex[:12]}",
            focus="ambient_acoustics",
            summary=f"Ambient: {category}",
            detail=f"amplitude_mean={amplitude:.4f} category={category}",
            source_signals="ambient_sound_daemon",
            confidence="high",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "ambient_sound.sampled",
            {
                "category": category,
                "amplitude_mean": amplitude,
                "sampled_at": now_iso,
            },
        )
    except Exception:
        pass


def get_latest_ambient_sound_for_prompt() -> str:
    """Return a quiet one-liner about recent ambient sound for prompt injection.

    Examples:
    - "[lyd (for 2t siden)]: det var stille"
    - "[lyd (for 45 min siden)]: der var tale i rummet"
    Returns empty string if nothing recent or feature disabled.
    """
    if not _experiment_enabled():
        return ""
    state = _state()
    last_cat = str(state.get("last_category") or "").strip()
    last_at = state.get("last_sample_at") or ""
    if not last_cat or not last_at:
        return ""
    dt = _parse_iso(str(last_at))
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    minutes_ago = int((datetime.now(UTC) - dt).total_seconds() / 60)
    # Only show if within last 12 hours — otherwise too stale to mean anything
    if minutes_ago > 12 * 60:
        return ""
    time_label = ""
    if minutes_ago < 60:
        time_label = f" (for {minutes_ago} min siden)"
    else:
        time_label = f" (for {minutes_ago // 60}t siden)"
    # Human-friendly Danish labels
    _LABELS = {
        "talk": "der var tale i rummet",
        "music": "der var musik",
        "silence": "det var stille",
        "noise": "der var baggrundsstøj",
        "mixed": "blandet lyd — tale + musik/støj",
    }
    label = _LABELS.get(last_cat, last_cat)
    return f"[lyd{time_label}]: {label}"


def build_ambient_sound_surface() -> dict:
    state = _state()
    return {
        "enabled": _experiment_enabled(),
        "last_sample_at": state.get("last_sample_at") or "",
        "last_category": state.get("last_category") or "",
        "history": list(state.get("history") or [])[:10],
        "sample_count": len(list(state.get("history") or [])),
    }


def _experiment_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.extra.get("ambient_sound_experiment_enabled", False))
    except Exception:
        return False


def _state() -> dict:
    val = get_runtime_state_value(_STATE_KEY, default={})
    return dict(val) if isinstance(val, dict) else {}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None
