"""Mic listen tool — Jarvis hears the room when he actively chooses to.

Distinct from ambient_sound_daemon (which is privacy-preserving metadata
only, no content). This tool is an **active, intentional** listen: Jarvis
calls it, audio is captured, transcribed, and returned as text.

Two transcription backends:
- 'hf' (default) — HF Whisper-v3, better Danish/multilingual quality, needs
  network + huggingface_token
- 'local' — faster-whisper tiny via core.skills.voice.stt, offline + private
  but lower quality on Danish

Audio captured from Logitech PRO USB via parec (same source as voice loop)
or sounddevice fallback.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
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
_MIC_SOURCE = "alsa_input.usb-Logitech_PRO_000000000000-00.mono-fallback"
_PAREC_BIN_CANDIDATES = (
    "/home/linuxbrew/.linuxbrew/bin/parec",
    "/usr/bin/parec",
    shutil.which("parec") or "",
)
_RECORDINGS_REL = "workspaces/default/memory/generated/mic"

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
            base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
            notes_path = _Path(base) / "workspaces/default/NOTES.md"
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


def _parec_binary() -> str | None:
    for path in _PAREC_BIN_CANDIDATES:
        if path and os.path.exists(path):
            return path
    return None


def _recording_dir() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _RECORDINGS_REL


# ─── Capture ──────────────────────────────────────────────────────────

def _capture_parec(duration: float) -> bytes | None:
    """Capture from Logitech via parec. Returns raw s16le mono 16kHz bytes."""
    parec = _parec_binary()
    if not parec:
        return None
    n_bytes = int(duration * _SAMPLE_RATE) * 2  # s16le
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    try:
        proc = subprocess.Popen(
            [parec, f"--device={_MIC_SOURCE}", f"--rate={_SAMPLE_RATE}",
             "--channels=1", "--format=s16le"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
        )
        raw = proc.stdout.read(n_bytes) if proc.stdout else b""
        proc.terminate()
        proc.wait(timeout=3)
        return raw if len(raw) >= 3200 else None  # at least 100ms
    except Exception as exc:
        logger.debug("mic_listen: parec capture failed: %s", exc)
        return None


def _capture_sounddevice(duration: float) -> bytes | None:
    """Fallback capture via sounddevice (default input device)."""
    try:
        import numpy as np
        import sounddevice as sd
        samples = sd.rec(
            int(duration * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocking=True,
        )
        return samples.tobytes()
    except Exception as exc:
        logger.debug("mic_listen: sounddevice capture failed: %s", exc)
        return None


def _capture_audio(duration: float) -> tuple[bytes | None, str]:
    """Try parec first (Logitech), then sounddevice fallback."""
    raw = _capture_parec(duration)
    if raw:
        return raw, "parec"
    raw = _capture_sounddevice(duration)
    if raw:
        return raw, "sounddevice"
    return None, "none"


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
            "text": "Could not capture audio — no mic available (parec + sounddevice both failed)",
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

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "mic.transcribed",
            "payload": {
                "text": transcript[:500],
                "chars": len(transcript),
                "backend": backend_used,
                "duration_s": duration,
                "capture": capture_path,
                "saved_path": saved_path,
                "trigger": trigger_action,
                "trigger_result": trigger_result,
            },
        })
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
                "Actively listen through the mic (Logitech PRO USB) for N seconds, "
                "then transcribe the recording. Use when Bjørn says something out loud, "
                "asks Jarvis to note a voice memo, or when active listening is needed. "
                "NOT for background monitoring — that's what ambient_sound_daemon handles "
                "(metadata only, no content). "
                "Default: HF Whisper-v3 (cloud, best quality); falls back to local "
                "faster-whisper if HF fails. Emits mic.transcribed event."
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
