"""Wake word detection using webrtcvad + ElevenLabs STT.

Pipeline:
  parec → webrtcvad (speech/silence) → collect speech chunk
  → ElevenLabs STT → check for "hey jarvis"

Only sends audio to the cloud when webrtcvad detects actual speech,
which eliminates Whisper hallucinations on silence.
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


def _get_elevenlabs_key() -> str | None:
    try:
        import json
        from pathlib import Path
        cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        return json.loads(cfg.read_text()).get("elevenlabs_api_key")
    except Exception:
        return None


def _transcribe(frames: list[bytes]) -> str:
    """Send collected audio frames to ElevenLabs STT."""
    key = _get_elevenlabs_key()
    if not key:
        return ""
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
            language_code="da",  # pin to Danish — prevents multi-language hallucinations
        )
        text = (result.text or "").strip()
        # Ignore pure sound-effect descriptions like "(background noise)"
        import re
        if re.fullmatch(r"[\s()\[\].,!?–-]*|\(.*\)", text):
            return ""
        return text
    except Exception as e:
        print(f"  [stt] ElevenLabs error: {e}")
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
