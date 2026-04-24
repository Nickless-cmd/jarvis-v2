"""Wake word detection using webrtcvad + local Whisper (cloud fallback).

Pipeline:
  parec → webrtcvad (speech/silence) → collect speech chunk
  → faster-whisper (local) → check for "hey jarvis"
  → ElevenLabs STT only as fallback if local fails

Only sends audio to the cloud when webrtcvad detects actual speech,
which eliminates hallucinations on silence. Local whisper keeps us
independent of API credits; cloud fallback covers model-load errors.
"""

import io
import os
import subprocess
import threading
import wave
import numpy as np
import webrtcvad

PAREC_BIN = "/home/linuxbrew/.linuxbrew/bin/parec"
MIC_SOURCE = "alsa_input.usb-Logitech_PRO_000000000000-00.mono-fallback"
SAMPLE_RATE = 16000
FRAME_MS = 30          # webrtcvad supports 10, 20, 30 ms
FRAME_BYTES = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # s16le

# Speech collection settings
MIN_SPEECH_FRAMES = 10  # ignore very short blips (~300ms)
MAX_SPEECH_FRAMES = 100 # ~3 seconds max before sending
SILENCE_FRAMES = 20     # frames of silence before we consider speech done

TRIGGER_WORDS = ["jarvis", "jarvi", "javis", "davis", "jarbs", "jarv", "arvis"]
TRIGGER_PREFIX = ["hey", "hej", "hi", "yo", "ok", "okay"]

# Local whisper model — loaded lazily and cached. 'tiny' is plenty for
# wake-word detection, our TRIGGER_WORDS list already tolerates slop.
_LOCAL_WHISPER_SIZE = os.environ.get("JARVIS_WAKE_WHISPER_SIZE", "tiny")
_local_whisper = None
_local_whisper_failed = False


def _get_elevenlabs_key() -> str | None:
    try:
        import json
        from pathlib import Path
        cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        return json.loads(cfg.read_text()).get("elevenlabs_api_key")
    except Exception:
        return None


def _get_local_whisper():
    """Load faster-whisper once and cache. Returns None if import fails."""
    global _local_whisper, _local_whisper_failed
    if _local_whisper_failed:
        return None
    if _local_whisper is not None:
        return _local_whisper
    try:
        from faster_whisper import WhisperModel
        _local_whisper = WhisperModel(
            _LOCAL_WHISPER_SIZE, device="cpu", compute_type="int8"
        )
        print(f"  [stt] local whisper loaded ({_LOCAL_WHISPER_SIZE}, cpu/int8)")
        return _local_whisper
    except Exception as exc:
        print(f"  [stt] local whisper load failed: {exc}")
        _local_whisper_failed = True
        return None


def _transcribe_local(frames: list[bytes]) -> str | None:
    """Transcribe with local faster-whisper. Returns None on error."""
    model = _get_local_whisper()
    if model is None:
        return None
    try:
        audio = (
            np.frombuffer(b"".join(frames), dtype=np.int16)
            .astype(np.float32)
            / 32768.0
        )
        segments, _ = model.transcribe(audio, language="da", beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()
    except Exception as exc:
        print(f"  [stt] local whisper transcribe failed: {exc}")
        return None


def _transcribe_elevenlabs(frames: list[bytes]) -> str | None:
    """Fallback: send audio to ElevenLabs STT. Returns None on error."""
    key = _get_elevenlabs_key()
    if not key:
        return None
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    buf.seek(0)
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=key)
        result = client.speech_to_text.convert(
            file=("audio.wav", buf, "audio/wav"),
            model_id="scribe_v1",
            language_code="da",
        )
        return (result.text or "").strip()
    except Exception as e:
        print(f"  [stt] ElevenLabs fallback error: {e}")
        return None


def _clean_transcript(text: str) -> str:
    """Strip sound-effect artefacts like '(background noise)'."""
    import re
    if re.fullmatch(r"[\s()\[\].,!?–-]*|\(.*\)", text):
        return ""
    return text


def _transcribe(frames: list[bytes]) -> str:
    """Local whisper first, ElevenLabs fallback."""
    local = _transcribe_local(frames)
    if local is not None:
        return _clean_transcript(local)
    cloud = _transcribe_elevenlabs(frames)
    if cloud is not None:
        return _clean_transcript(cloud)
    return ""


def _is_wake_word(text: str) -> bool:
    t = text.lower()
    has_jarvis = any(w in t for w in TRIGGER_WORDS)
    has_prefix = any(w in t for w in TRIGGER_PREFIX)
    return has_jarvis and has_prefix


def listen(callback=None, interrupt_event=None):
    """
    Continuously listen for 'Hey Jarvis'.
    Uses VAD to gate speech, ElevenLabs STT to transcribe.
    Calls callback('hey_jarvis') on detection.
    """
    if interrupt_event is None:
        interrupt_event = threading.Event()

    vad = webrtcvad.Vad(3)  # aggressiveness 0-3 (3 = most aggressive, filters background noise best)
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}

    def _make_proc():
        return subprocess.Popen(
            [PAREC_BIN, f"--device={MIC_SOURCE}",
             f"--rate={SAMPLE_RATE}", "--channels=1", "--format=s16le"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )

    print("👂 Listening for 'Hey Jarvis'...")
    proc = _make_proc()

    speech_frames: list[bytes] = []
    silence_count = 0
    in_speech = False

    try:
        while not interrupt_event.is_set():
            frame = proc.stdout.read(FRAME_BYTES)
            if not frame or len(frame) < FRAME_BYTES:
                break

            is_speech = vad.is_speech(frame, SAMPLE_RATE)

            if is_speech:
                silence_count = 0
                if not in_speech:
                    in_speech = True
                speech_frames.append(frame)

                if len(speech_frames) >= MAX_SPEECH_FRAMES:
                    # Too long — flush and check
                    text = _transcribe(speech_frames)
                    if text:
                        print(f"  heard: {text!r}")
                    if _is_wake_word(text):
                        _trigger(proc, callback, interrupt_event, _make_proc)
                    speech_frames = []
                    in_speech = False

            elif in_speech:
                speech_frames.append(frame)
                silence_count += 1

                if silence_count >= SILENCE_FRAMES:
                    # End of speech chunk
                    if len(speech_frames) >= MIN_SPEECH_FRAMES:
                        text = _transcribe(speech_frames)
                        if text:
                            print(f"  heard: {text!r}")
                        if _is_wake_word(text):
                            _trigger(proc, callback, interrupt_event, _make_proc)
                            proc = _make_proc()
                    speech_frames = []
                    silence_count = 0
                    in_speech = False
    finally:
        proc.terminate()
        proc.wait()
        print("🛑 Stopped listening")


def _trigger(proc, callback, interrupt_event, make_proc):
    """Handle wake word detection: kill parec, run callback, restart."""
    print("🔊 Wake word detected!")
    proc.terminate()
    proc.wait()
    if callback:
        callback("hey_jarvis")
    if not interrupt_event.is_set():
        import time
        time.sleep(2.0)  # brief cooldown after TTS finishes
