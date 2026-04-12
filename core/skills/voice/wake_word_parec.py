"""Wake word detection using parec (PipeWire/PulseAudio) for audio capture."""

import subprocess
import numpy as np
from openwakeword.model import Model

SAMPLE_RATE = 16000
FRAME_MS = 80
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 1280
FRAME_BYTES = FRAME_SAMPLES * 2  # s16le = 2 bytes per sample

# PipeWire source for the onboard analog mic
MIC_SOURCE = "alsa_input.pci-0000_00_1f.3.analog-stereo"

DEFAULT_WAKE_WORDS = ["hey_jarvis_v0.1"]


def listen(callback=None, interrupt_event=None, wake_words=None):
    """
    Stream mic audio via parec and run openwakeword on each 80ms frame.
    Calls callback(word) when wake word detected with score > 0.5.
    Stops when interrupt_event is set.
    """
    if wake_words is None:
        wake_words = DEFAULT_WAKE_WORDS

    model = Model(wakeword_models=wake_words)

    proc = subprocess.Popen(
        [
            "parec",
            f"--device={MIC_SOURCE}",
            f"--rate={SAMPLE_RATE}",
            "--channels=1",
            "--format=s16le",
            "--latency-msec=80",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    print(f"👂 Listening for: {wake_words}")
    buf = b""
    try:
        while True:
            if interrupt_event and interrupt_event.is_set():
                break
            chunk = proc.stdout.read(FRAME_BYTES)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= FRAME_BYTES:
                frame_bytes = buf[:FRAME_BYTES]
                buf = buf[FRAME_BYTES:]
                frame = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                preds = model.predict(frame)
                for word in wake_words:
                    score = preds.get(word, 0)
                    if score > 0.5:
                        print(f"🔊 Wake word detected: {word} (score={score:.3f})")
                        if callback:
                            callback(word)
    finally:
        proc.terminate()
        proc.wait()
        print("🛑 Stopped listening")
