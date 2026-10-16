"""Mic listen tool — Jarvis hears the room when he actively chooses to.

Distinct from ambient_sound_daemon (which is privacy-preserving metadata
only, no content). This tool is an **active, intentional** listen: Jarvis
calls it, audio is captured, transcribed, and returned as text.

Two transcription backends:
- 'hf' (default) — HF Whisper-v3, good Danish/multilingual quality, needs
  network + huggingface_token
- 'local' — faster-whisper tiny via core.skills.voice.stt, offline + private
  but poor quality on Danish

Audio captured via sounddevice/ALSA. The device is chosen by NAME, not by
index, and the capture runs at the device's NATIVE sample rate before being
resampled to 16 kHz for transcription.

History (measured 16/10-2026): the tool used to shell out to `parec` against
a PipeWire source name (`alsa_input.usb-NOS_X500_...`). Both halves of that
were dead: the NOS X500 is no longer attached, and there is no PulseAudio/
PipeWire daemon inside the container (`pactl` → Connection refused), so
`parec` could never connect. The fallback then called `sd.rec()` with no
device, which resolved to ALSA `default` — also silent. Net effect: the tool
reported success while capturing digital silence.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_DEFAULT_DURATION = 8.0
_MAX_DURATION = 60.0

#: Substring matched against ALSA device names, in priority order. The first
#: device whose name contains one of these wins. Names are used instead of
#: indices because ALSA indices shift when devices are plugged/unplugged —
#: an index that works today can silently point at a different card tomorrow.
#: Override with JARVIS_MIC_DEVICE (a name substring or an exact index).
_MIC_DEVICE_PREFERENCES = (
    "PRO: USB Audio",       # Logitech PRO — the only device measured with signal
    "BUA-200M: USB Audio",  # Plantronics headset (measured silent 16/10-2026)
    "USB Camera2: Audio",
)
_MIC_DEVICE_ENV = "JARVIS_MIC_DEVICE"

_RECORDINGS_REL = "memory/generated/mic"

# Trigger phrases Jarvis recognizes in transcripts. Matched case-insensitively
# as substrings. Each trigger maps to a structured action the helper below
# routes to.
_TRIGGER_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # action_key, phrases
    ("remember", ("jarvis husk dette", "husk dette jarvis", "husk det her",
                  "jarvis remember this", "remember this jarvis")),
    ("note", ("jarvis note", "skriv en note", "take a note")),
    ("journal", ("jarvis journal", "start journal", "journal entry")),
)


def _normalize_for_match(text: str) -> str:
    """Lowercase + replace punctuation with spaces + collapse whitespace.

    So 'Jarvis, remember this:' matches the pattern 'jarvis remember this'.
    """
    import re
    low = str(text or "").lower()
    low = re.sub(r"[,:;!?.\-—_]+", " ", low)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def detect_trigger(text: str) -> str | None:
    """Return the action_key of a trigger matched in text, or None."""
    if not text:
        return None
    normalized = _normalize_for_match(text)
    for action_key, phrases in _TRIGGER_PATTERNS:
        for phrase in phrases:
            if phrase in normalized:
                return action_key
    return None


def _strip_trigger(text: str, action_key: str) -> str:
    """Remove the matched trigger phrase from the transcript so the remainder
    is the actual content Bjørn wanted recorded.

    Uses a regex that tolerates punctuation between words (so 'Jarvis, husk
    dette:' strips the same way as 'Jarvis husk dette').
    """
    import re
    for ak, phrases in _TRIGGER_PATTERNS:
        if ak != action_key:
            continue
        for phrase in phrases:
            # Build a regex allowing any non-alphanumeric characters between
            # words (so commas/colons/dashes don't break the match).
            words = phrase.split()
            pattern = r"[^a-zæøå0-9]*".join(re.escape(w) for w in words)
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                before = text[:match.start()].rstrip(" .,:;-—")
                after = text[match.end():].lstrip(" .,:;-—")
                return (before + " " + after).strip()
    return text.strip()


def _route_trigger(action_key: str, transcript: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Route a detected trigger to the appropriate downstream system.

    Returns a small dict describing what was done, or None on failure.
    Gracefully soft-fails if dependencies aren't available.
    """
    content = _strip_trigger(transcript, action_key)
    if not content:
        return {"routed": action_key, "action": "skipped", "reason": "no-content-after-trigger"}

    if action_key == "remember":
        try:
            from core.services.memory_density import write_density_note
            # Derive short title from first 60 chars
            title = content[:60].rstrip(".,!?:;") or "Voice capture"
            note = write_density_note(
                title=title,
                what_happened=content,
                what_it_meant="(unfilled — voice capture, enrich later)",
                how_it_felt="(unfilled)",
                what_it_changed="(unfilled)",
                trigger_type="manual",
                metadata={
                    "source": "mic_listen_trigger",
                    "trigger_action": action_key,
                    **metadata,
                },
            )
            return {
                "routed": action_key,
                "action": "memory_density.written",
                "note_id": note.get("note_id"),
                "title": note.get("title"),
            }
        except Exception as exc:
            logger.debug("mic_listen trigger 'remember' routing failed: %s", exc)
            return {"routed": action_key, "action": "error", "error": str(exc)}

    if action_key == "note":
        # Lightweight: append to workspace NOTES.md (create if missing)
        try:
            from datetime import UTC, datetime as _dt
            from pathlib import Path as _Path
            from core.runtime.workspace_paths import shared_dir as _shared_dir
            notes_path = _shared_dir() / "NOTES.md"
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = _dt.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
            entry = f"\n- **{timestamp}** (voice): {content}\n"
            if notes_path.exists():
                notes_path.write_text(notes_path.read_text() + entry)
            else:
                notes_path.write_text("# NOTES\n\n*Voice and text captures.*\n" + entry)
            return {"routed": action_key, "action": "notes.appended", "path": str(notes_path)}
        except Exception as exc:
            return {"routed": action_key, "action": "error", "error": str(exc)}

    if action_key == "journal":
        # Don't recurse into voice_journal (already-captured audio); just flag
        # to caller that user intended a journal entry — they should call
        # voice_journal separately for a longer dedicated recording.
        return {
            "routed": action_key,
            "action": "intent-detected",
            "note": "User asked to start a journal — caller should invoke voice_journal for longer recording",
        }

    return {"routed": action_key, "action": "unhandled"}


def _recording_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _RECORDINGS_REL


# ─── Device selection ─────────────────────────────────────────────────

def _pick_input_device(sd: Any) -> tuple[int | None, str, int]:
    """Choose an input device by NAME. Returns (index, name, native_rate).

    ``index`` is None when nothing usable was found. The rate is the device's
    own default — capturing at a rate the hardware does not support is what
    produced ``Invalid sample rate`` on the camera device (measured
    16/10-2026: card 3 rejects 16 kHz).
    """
    override = os.environ.get(_MIC_DEVICE_ENV, "").strip()
    try:
        devices = list(sd.query_devices())
    except Exception as exc:
        logger.debug("mic_listen: could not query devices: %s", exc)
        return None, "", _SAMPLE_RATE

    def _usable(d: dict[str, Any]) -> bool:
        return int(d.get("max_input_channels") or 0) > 0

    # Explicit override wins: an exact index, or a name substring.
    if override:
        if override.isdigit():
            idx = int(override)
            if 0 <= idx < len(devices) and _usable(devices[idx]):
                d = devices[idx]
                return idx, str(d.get("name") or ""), int(d.get("default_samplerate") or _SAMPLE_RATE)
        else:
            for idx, d in enumerate(devices):
                if _usable(d) and override.lower() in str(d.get("name") or "").lower():
                    return idx, str(d.get("name") or ""), int(d.get("default_samplerate") or _SAMPLE_RATE)
        logger.warning("mic_listen: %s=%r matched no usable device — falling back", _MIC_DEVICE_ENV, override)

    for pref in _MIC_DEVICE_PREFERENCES:
        for idx, d in enumerate(devices):
            if _usable(d) and pref.lower() in str(d.get("name") or "").lower():
                return idx, str(d.get("name") or ""), int(d.get("default_samplerate") or _SAMPLE_RATE)

    # Last resort: the system default input, if it has input channels.
    try:
        default_in = sd.default.device[0]
        if isinstance(default_in, int) and 0 <= default_in < len(devices) and _usable(devices[default_in]):
            d = devices[default_in]
            return default_in, str(d.get("name") or ""), int(d.get("default_samplerate") or _SAMPLE_RATE)
    except Exception:  # sd.default kan mangle/vaere en streng — vi falder til None nedenfor
        pass
    return None, "", _SAMPLE_RATE


def _resample_to_16k(samples: Any, native_rate: int) -> Any:
    """Resample int16 mono samples from ``native_rate`` to 16 kHz.

    Uses scipy when available; otherwise falls back to linear interpolation
    via numpy. Never raises — on failure the caller gets the input unchanged
    (better a wrong-rate transcript than a crash in a perception path).
    """
    import numpy as np
    if native_rate == _SAMPLE_RATE:
        return samples
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(int(native_rate), _SAMPLE_RATE)
        up, down = _SAMPLE_RATE // g, int(native_rate) // g
        return resample_poly(samples.astype(np.float32), up, down).astype(np.int16)
    except Exception as exc:
        logger.debug("mic_listen: scipy resample failed (%s) — linear fallback", exc)
        try:
            n_out = int(len(samples) * _SAMPLE_RATE / native_rate)
            if n_out <= 0:
                return samples
            x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
            return np.interp(x_new, x_old, samples.astype(np.float32)).astype(np.int16)
        except Exception:  # ogsaa lineaer interpolation fejlede — hellere raa lyd end et kast i en perceptions-vej
            return samples


# ─── Capture ──────────────────────────────────────────────────────────

def _capture_sounddevice(duration: float) -> tuple[bytes | None, str]:
    """Capture via sounddevice/ALSA at the device's native rate.

    Returns (raw s16le mono 16 kHz bytes, description). The description names
    the device actually used, so a silent capture can be traced to a device
    rather than to "the mic".
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as exc:
        logger.debug("mic_listen: sounddevice/numpy unavailable: %s", exc)
        return None, "sounddevice-unavailable"

    idx, name, native_rate = _pick_input_device(sd)
    if idx is None:
        return None, "no-input-device"

    try:
        samples = sd.rec(
            int(duration * native_rate),
            samplerate=native_rate,
            channels=1,
            dtype="int16",
            device=idx,
            blocking=True,
        )
    except Exception as exc:
        logger.debug("mic_listen: capture failed on device %s (%s): %s", idx, name, exc)
        return None, f"capture-failed:{name}"

    mono = samples.reshape(-1)
    resampled = _resample_to_16k(mono, native_rate)
    return resampled.tobytes(), f"sounddevice:{name}@{native_rate}"


def _capture_audio(duration: float) -> tuple[bytes | None, str]:
    """Capture audio. sounddevice/ALSA is the only path.

    `parec` was removed 16/10-2026: it needs a PulseAudio/PipeWire daemon and
    there is none in the container, so it could only ever fail — while its
    presence made the failure look like a device problem.
    """
    return _capture_sounddevice(duration)


def _write_wav(raw_pcm: bytes, path: Path) -> None:
    """Wrap raw s16le mono 16kHz bytes as a WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(raw_pcm)


# ─── Transcription backends ───────────────────────────────────────────

def _transcribe_hf(wav_path: Path, language: str | None) -> dict[str, Any]:
    try:
        from core.tools.hf_inference_tools import transcribe_audio
        return transcribe_audio(
            audio_source=str(wav_path),
            model="openai/whisper-large-v3",
            language=language,
        )
    except Exception as exc:
        return {"status": "error", "text": f"hf transcribe failed: {exc}"}


def _transcribe_local(raw_pcm: bytes, language: str | None) -> dict[str, Any]:
    try:
        import numpy as np
        from core.skills.voice.stt import transcribe, get_model
        audio = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
        model = get_model()  # faster-whisper tiny
        text = transcribe(audio, model=model, language=language or "en")
        return {"status": "ok", "text": text, "model": "faster-whisper-tiny-local"}
    except Exception as exc:
        return {"status": "error", "text": f"local transcribe failed: {exc}"}


# ─── Tool entry point ────────────────────────────────────────────────

def listen_and_transcribe(
    *,
    duration: float = _DEFAULT_DURATION,
    backend: str = "hf",
    language: str | None = None,
    save_recording: bool = False,
) -> dict[str, Any]:
    """Active mic listen. Captures audio, transcribes, returns text.

    Args:
        duration: seconds to record (capped at _MAX_DURATION)
        backend: 'hf' (cloud, better quality) or 'local' (offline)
        language: ISO hint like 'da', 'en'. None = auto-detect (HF only)
        save_recording: persist WAV to workspace/memory/generated/mic/
    """
    duration = max(0.5, min(_MAX_DURATION, float(duration)))

    raw_pcm, capture_path = _capture_audio(duration)
    if raw_pcm is None:
        return {
            "status": "error",
            "text": (
                f"Could not capture audio — no usable input device ({capture_path}). "
                "Set JARVIS_MIC_DEVICE to a device name substring or index to override."
            ),
            "capture_device": capture_path,
        }

    tmp_dir = Path(tempfile.mkdtemp(prefix="jarvis-mic-"))
    wav_path = tmp_dir / f"capture-{uuid4().hex[:8]}.wav"
    try:
        _write_wav(raw_pcm, wav_path)
    except Exception as exc:
        return {"status": "error", "text": f"could not write WAV: {exc}"}

    # Pick backend
    backend_used = backend
    if backend == "hf":
        result = _transcribe_hf(wav_path, language=language)
        # Automatic fallback to local if HF fails and local is importable
        if result.get("status") != "ok":
            hf_err = result.get("text", "")
            local = _transcribe_local(raw_pcm, language=language)
            if local.get("status") == "ok":
                result = local
                result["fallback_note"] = f"HF failed ({hf_err[:80]}); used local"
                backend_used = "local"
    else:
        result = _transcribe_local(raw_pcm, language=language)
        backend_used = "local"

    # Persist recording if requested
    saved_path: str | None = None
    if save_recording and result.get("status") == "ok":
        try:
            target_dir = _recording_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            saved = target_dir / f"mic-{ts}-{uuid4().hex[:6]}.wav"
            shutil.copy2(wav_path, saved)
            saved_path = str(saved)
        except Exception as exc:
            logger.debug("mic_listen: save failed: %s", exc)

    # Cleanup temp
    try:
        wav_path.unlink()
        tmp_dir.rmdir()
    except Exception:
        pass

    if result.get("status") != "ok":
        return result

    # Emit event for action_router / memory_density / etc.
    transcript = str(result.get("text") or "")
    trigger_action = detect_trigger(transcript)
    trigger_result: dict[str, Any] | None = None
    if trigger_action:
        trigger_result = _route_trigger(trigger_action, transcript, {
            "duration_s": duration,
            "backend": backend_used,
            "wav_path": saved_path,
        })

    # Egress-fri Central-observation (§24.4): Jarvis SANSER lyd fra rummet. Kun
    # skalarer (chars/duration/backend/trigger-flag) — ALDRIG transskriptionen.
    # Self-safe: en observe-fejl må aldrig påvirke tool-logikken.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "mic_listen",
            value=float(len(transcript)),
            meta={
                "chars": len(transcript),
                "duration_s": float(duration),
                "backend": str(backend_used),
                "capture": str(capture_path),
                "trigger": bool(trigger_action),
                "heard": bool(transcript),
            },
            reason="mic perception",
        )
    except Exception:
        pass

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "mic.transcribed",
            {
                "text": transcript[:500],
                "chars": len(transcript),
                "backend": backend_used,
                "duration_s": duration,
                "capture": capture_path,
                "saved_path": saved_path,
                "trigger": trigger_action,
                "trigger_result": trigger_result,
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "text": transcript,
        "backend": backend_used,
        "capture_device": capture_path,
        "duration_s": duration,
        "saved_path": saved_path,
        "bytes_recorded": len(raw_pcm),
        "trigger": trigger_action,
        "trigger_result": trigger_result,
    }


def _exec_mic_listen(args: dict[str, Any]) -> dict[str, Any]:
    try:
        duration = float(args.get("duration") or _DEFAULT_DURATION)
    except Exception:
        duration = _DEFAULT_DURATION
    backend = str(args.get("backend") or "hf").lower().strip()
    if backend not in ("hf", "local"):
        backend = "hf"
    language = args.get("language")
    save_recording = bool(args.get("save_recording", False))

    result = listen_and_transcribe(
        duration=duration,
        backend=backend,
        language=str(language) if language else None,
        save_recording=save_recording,
    )
    if result.get("status") == "ok":
        text = result.get("text", "") or "(stilhed)"
        preview = text if len(text) <= 200 else text[:200] + "..."
        return {
            "status": "ok",
            "text": f"Heard [{result.get('backend')}, {result.get('duration_s')}s]: {preview}",
            **result,
        }
    return result


MIC_LISTEN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "mic_listen",
            "description": (
                "Record N seconds of NEW audio from the system mic and "
                "transcribe it. ONLY call when Bjørn EXPLICITLY asks you to "
                "listen now (e.g. 'lyt', 'optag voice memo', 'tag det her "
                "ned mens jeg taler'). DO NOT call this just because the "
                "current message arrived via voice — the wake-word pipeline "
                "already transcribed what Bjørn said and that's the message "
                "you're reading right now. Calling mic_listen on a regular "
                "message produces several seconds of dead delay and captures "
                "silence. If unsure: don't call it. Background acoustic "
                "monitoring is ambient_sound_daemon's job (metadata only). "
                "Default backend: HF Whisper-v3 (cloud), falls back to local."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "number",
                        "description": "Seconds to record (0.5-60). Default 8.",
                    },
                    "backend": {
                        "type": "string",
                        "description": (
                            "hf (default, cloud Whisper-v3, better quality) | "
                            "local (offline faster-whisper-tiny, private)"
                        ),
                    },
                    "language": {
                        "type": "string",
                        "description": "ISO code like 'da', 'en'. Omit for auto-detect.",
                    },
                    "save_recording": {
                        "type": "boolean",
                        "description": "Persist WAV to workspace/memory/generated/mic/. Default false.",
                    },
                },
                "required": [],
            },
        },
    },
]
