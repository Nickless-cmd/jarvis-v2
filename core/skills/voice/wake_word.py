"""Wake word detection using Whisper (faster-whisper) via parec audio stream."""

import subprocess
import threading
import numpy as np
from faster_whisper import WhisperModel

# PipeWire source for the USB camera microphone (picks up voice reliably)
MIC_SOURCE = "alsa_input.usb-Generic_USB_Camera2_200901010001-03.iec958-stereo"
PAREC_BIN = "/home/linuxbrew/.linuxbrew/bin/parec"
SAMPLE_RATE = 16000
CLIP_SECONDS = 2  # window size for each Whisper transcription

# Words Whisper might hear instead of "jarvis" (typos/homophones from tiny model)
TRIGGER_WORDS = ["jarvis", "jarvi", "jarv", "davis", "travis"]

_model: WhisperModel | None = None
_model_lock = threading.Lock()


def _get_model() -> WhisperModel:
    global _model
    with _model_lock:
        if _model is None:
            _model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return _model


def _is_wake_word(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in TRIGGER_WORDS)


def listen(callback=None, interrupt_event=None):
    """
    Continuously listen for 'Hey Jarvis' using Whisper transcription.
    Calls callback(word) when wake word is detected.
    Stops when interrupt_event is set.
    """
    if interrupt_event is None:
        interrupt_event = threading.Event()

    model = _get_model()
    frame_bytes = SAMPLE_RATE * CLIP_SECONDS * 2  # s16le = 2 bytes/sample

    import os
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}

    print(f"👂 Listening for 'Hey Jarvis'...")

    def _make_proc():
        return subprocess.Popen(
            [
                PAREC_BIN,
                f"--device={MIC_SOURCE}",
                f"--rate={SAMPLE_RATE}",
                "--channels=1",
                "--format=s16le",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )

    proc = _make_proc()
    try:
        while not interrupt_event.is_set():
            raw = proc.stdout.read(frame_bytes)
            if not raw:
                break
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            segs, _ = model.transcribe(
                audio,
                language="en",
                beam_size=1,
                initial_prompt="Hey Jarvis",
            )
            text = " ".join(s.text.strip() for s in segs).strip()
            if text:
                print(f"  heard: {text!r}")
            if _is_wake_word(text):
                print(f"🔊 Wake word detected!")
                # Kill parec so buffered audio is discarded before callback returns
                proc.terminate()
                proc.wait()
                if callback:
                    callback("hey_jarvis")
                if not interrupt_event.is_set():
                    # Fresh parec — no stale "Hey Jarvis" in buffer
                    proc = _make_proc()
    finally:
        proc.terminate()
        proc.wait()
        print("🛑 Stopped listening")
