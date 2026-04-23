"""Ambient Sound daemon — Layer 6½: background acoustic context.

Per roadmap v6/v7 (Jarvis' forslag, bekræftet af Claude):
  "Lag 6½: 4 gange om dagen, 10 sekunders lydniveau-sample, metadata-only.
  Ingen indhold gemmes — kun nøgle-ratio (talk/silence/music/noise)."

PRIVACY: The daemon is opt-in (ambient_sound_experiment_enabled, default
False). When enabled AND category == "talk" AND
ambient_sound_transcribe_enabled is True (default True), the 10s buffer
is written to a temp WAV, transcribed via HF Whisper, and the temp file
is deleted immediately after. Non-talk samples remain metadata-only.
Every sample (with or without transcript) is mirrored into Sansernes
Arkiv so Jarvis has a recallable audio timeline.

Requires `sounddevice` (optional dep). If unavailable, daemon silently skips.
If microphone is not accessible (permission denied, no device), same.

Categories: talk, music, silence, noise, mixed
"""
from __future__ import annotations

import logging
import os
import tempfile
import wave
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
_TRANSCRIBE_AMPLITUDE_FLOOR = 0.015  # below this, never bother transcribing
_SAMPLE_RATE = 44100


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

    category, amplitude_mean, amplitude_std, wav_path = _capture_sample()
    if category is None:
        return {"generated": False, "reason": "no_audio_device"}

    transcript = ""
    try:
        if (
            wav_path
            and category == "talk"
            and amplitude_mean >= _TRANSCRIBE_AMPLITUDE_FLOOR
            and _ambient_transcribe_enabled()
        ):
            transcript = _transcribe_sample(wav_path)
    finally:
        if wav_path:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    description = _interpret_sound(
        category=category,
        amplitude_mean=amplitude_mean,
        amplitude_std=amplitude_std,
        now=now,
    )

    sample = {
        "sampled_at": now.isoformat(),
        "category": category,
        "amplitude_mean": round(amplitude_mean, 4),
        "amplitude_std": round(amplitude_std, 4),
        "description": description,
        "transcript": transcript,
    }

    history = list(state.get("history") or [])
    history.insert(0, sample)
    if len(history) > _BUFFER_MAX:
        history = history[:_BUFFER_MAX]

    new_state = {
        "last_sample_at": now.isoformat(),
        "last_category": category,
        "last_description": description,
        "last_transcript": transcript,
        "history": history,
    }
    set_runtime_state_value(_STATE_KEY, new_state)

    _store_sample(sample, now)
    _archive_sensory(sample, now)

    return {
        "generated": True,
        "category": category,
        "amplitude_mean": amplitude_mean,
        "transcribed": bool(transcript),
    }


def _capture_sample() -> tuple[str | None, float, float, str | None]:
    """Record 10 seconds of audio, classify, save to temp WAV.

    Returns (category, mean, std, wav_path) on success; (None, 0, 0, None) if
    the mic/device is unavailable. Caller is responsible for deleting the
    WAV file after transcription (or not) — see tick_ambient_sound_daemon.
    """
    try:
        import numpy as np
        import sounddevice as sd

        samples = sd.rec(
            int(_SAMPLE_DURATION_SECONDS * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocking=True,
        )
        amplitude = np.abs(samples.flatten())
        mean = float(amplitude.mean())
        std = float(amplitude.std())
        category = _classify(mean, std)
        wav_path = _save_wav(samples)
        return category, mean, std, wav_path
    except ImportError:
        logger.debug("ambient_sound: sounddevice not available")
        return None, 0.0, 0.0, None
    except Exception as exc:
        logger.debug("ambient_sound: capture failed: %s", exc)
        return None, 0.0, 0.0, None


def _save_wav(samples) -> str | None:
    """Write float32 mono samples to a temp 16-bit PCM WAV. Returns path or None."""
    try:
        import numpy as np

        fd, path = tempfile.mkstemp(prefix="jarvis-ambient-", suffix=".wav")
        os.close(fd)
        pcm = np.clip(samples.flatten() * 32767.0, -32768, 32767).astype("<i2")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())
        return path
    except Exception as exc:
        logger.debug("ambient_sound: wav save failed: %s", exc)
        return None


def _transcribe_sample(wav_path: str) -> str:
    """Transcribe a WAV via HF Whisper. Returns empty string on failure."""
    try:
        from core.tools.hf_inference_tools import transcribe_audio
        result = transcribe_audio(audio_source=wav_path, language="da")
        text = str(result.get("text") or "").strip()
        if result.get("status") == "error":
            logger.debug("ambient_sound: transcribe error: %s", text)
            return ""
        return text[:2000]
    except Exception as exc:
        logger.debug("ambient_sound: transcribe raised: %s", exc)
        return ""


def _ambient_transcribe_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.extra.get("ambient_sound_transcribe_enabled", True))
    except Exception:
        return True


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
    transcript = str(sample.get("transcript") or "").strip()
    detail = f"amplitude_mean={amplitude:.4f} category={category}"
    if transcript:
        detail += f" transcript={transcript[:400]}"
    summary = f"Ambient: {category}"
    if transcript:
        summary = f"Ambient talk: {transcript[:120]}"
    try:
        insert_private_brain_record(
            record_id=f"pb-ambient-{uuid4().hex[:12]}",
            record_type="ambient-sound",
            layer="lag_6_half",
            session_id="heartbeat",
            run_id=f"ambient-sound-{uuid4().hex[:12]}",
            focus="ambient_acoustics",
            summary=summary,
            detail=detail,
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
                "has_transcript": bool(transcript),
            },
        )
    except Exception:
        pass


def _archive_sensory(sample: dict, now: datetime) -> None:
    """Mirror every ambient sample into Sansernes Arkiv. Silent on failure."""
    category = str(sample.get("category") or "")
    description = str(sample.get("description") or "").strip()
    transcript = str(sample.get("transcript") or "").strip()
    amplitude_mean = float(sample.get("amplitude_mean") or 0)
    amplitude_std = float(sample.get("amplitude_std") or 0)
    if transcript:
        content = f"[hørt tale]: {transcript}"
        if description:
            content += f"\n\n(rumstemning: {description})"
    elif description:
        content = description
    else:
        content = f"Lydbillede: {category}"
    try:
        from core.services.sensory_archive import record_audio
        record_audio(
            content,
            metadata={
                "source": "ambient_sound_daemon",
                "category": category,
                "amplitude_mean": round(amplitude_mean, 4),
                "amplitude_std": round(amplitude_std, 4),
                "transcribed": bool(transcript),
                "sampled_at": now.isoformat(),
            },
        )
    except Exception as exc:
        logger.debug("ambient_sound: archive mirror failed: %s", exc)


def get_latest_ambient_sound_for_prompt() -> str:
    """Return a nuanced description of recent ambient sound for prompt injection."""
    if not _experiment_enabled():
        return ""
    state = _state()
    last_at = state.get("last_sample_at") or ""
    if not last_at:
        return ""
    dt = _parse_iso(str(last_at))
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    minutes_ago = int((datetime.now(UTC) - dt).total_seconds() / 60)
    if minutes_ago > 12 * 60:
        return ""
    time_label = (
        f" (for {minutes_ago} min siden)" if minutes_ago < 60
        else f" (for {minutes_ago // 60}t siden)"
    )
    transcript = str(state.get("last_transcript") or "").strip()
    description = str(state.get("last_description") or "").strip()
    if not description:
        _LABELS = {
            "talk": "der var tale i rummet",
            "music": "der var musik",
            "silence": "det var stille",
            "noise": "der var baggrundsstøj",
            "mixed": "blandet lyd — tale + musik/støj",
        }
        last_cat = str(state.get("last_category") or "").strip()
        description = _LABELS.get(last_cat, last_cat)
    if transcript:
        return f"[lyd{time_label}]: {description} — hørte: \"{transcript[:140]}\""
    return f"[lyd{time_label}]: {description}"


def build_ambient_sound_surface() -> dict:
    state = _state()
    return {
        "enabled": _experiment_enabled(),
        "last_sample_at": state.get("last_sample_at") or "",
        "last_category": state.get("last_category") or "",
        "history": list(state.get("history") or [])[:10],
        "sample_count": len(list(state.get("history") or [])),
    }


_SOUND_PROMPTS = [
    (
        "Lydbilledet er klassificeret som '{category}' "
        "(amplitude: gennemsnit={mean:.4f}, variation={std:.4f}, tidspunkt={hour}:xx). "
        "Skriv én kort sætning på dansk der beskriver stemningen i rummet. "
        "Tænk på tidspunkt og intensitet — ikke blot kategorien. "
        "Undgå: 'det er stille', 'der er musik'. Vær konkret og sanselig."
    ),
    (
        "Lydniveauet er '{category}' (mean={mean:.4f}, std={std:.4f}) klokken ~{hour}. "
        "Hvad fortæller dette lydmønster om hvad der foregår i rummet? "
        "Skriv én sætning på dansk — fokus på energi og tilstedeværelse."
    ),
    (
        "Akustisk snapshot: kategori='{category}', amplitude={mean:.4f}, tid={hour}:xx. "
        "Beskriv på dansk hvad øret ville bemærke. "
        "Kontrast med stilhed eller larm — hvad er karakteristisk ved netop dette?"
    ),
    (
        "Lydklassifikation: '{category}' (variation={std:.4f} ift. niveau={mean:.4f}). "
        "Skriv én sætning på dansk om den akustiske stemning — "
        "som om du beskriver det til én der ikke er i rummet."
    ),
]


def _interpret_sound(
    *,
    category: str,
    amplitude_mean: float,
    amplitude_std: float,
    now: datetime,
) -> str:
    """Generate a nuanced Danish description from acoustic metadata via LLM."""
    import time as _time
    prompt_template = _SOUND_PROMPTS[int(_time.time() // 3600) % len(_SOUND_PROMPTS)]
    prompt = prompt_template.format(
        category=category,
        mean=amplitude_mean,
        std=amplitude_std,
        hour=now.hour,
    )
    try:
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(prompt, max_len=80, fallback="", daemon_name="ambient_sound")
        text = str(raw or "").strip()
        if text:
            return text[:200]
    except Exception as exc:
        logger.debug("ambient_sound: LLM interpretation failed: %s", exc)
    return ""


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
