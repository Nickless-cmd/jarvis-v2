"""Speech-to-text using faster-whisper."""

import numpy as np
from faster_whisper import WhisperModel

MODEL_SIZE = "tiny"
SAMPLE_RATE = 16000

# PipeWire source for Logitech PRO USB sound card
MIC_SOURCE = "alsa_input.usb-Logitech_PRO_000000000000-00.mono-fallback"
PAREC_BIN = "/home/linuxbrew/.linuxbrew/bin/parec"


def get_model(model_size: str = MODEL_SIZE, device: str = "cpu", compute_type: str = "int8") -> WhisperModel:
    """Load or return cached Whisper model."""
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def record_audio(duration: float = 5.0, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Record audio from USB mic via parec and return as float32 at 16 kHz."""
    import subprocess, os
    print(f"🎙️  Recording for {duration}s...")
    n_bytes = int(duration * SAMPLE_RATE) * 2  # s16le
    env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    proc = subprocess.Popen(
        [PAREC_BIN, f"--device={MIC_SOURCE}", f"--rate={SAMPLE_RATE}",
         "--channels=1", "--format=s16le"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    raw = proc.stdout.read(n_bytes)
    proc.terminate()
    proc.wait()
    print("✅ Recording done")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(audio: np.ndarray, model: WhisperModel | None = None, language: str = "en") -> str:
    """Transcribe numpy audio array to text."""
    if model is None:
        model = get_model()

    segments, _ = model.transcribe(audio, language=language, beam_size=1)
    text = " ".join(s.text.strip() for s in segments)
    return text.strip()


def listen_and_transcribe(duration: float = 5.0, language: str = "da") -> str:
    """Record from mic and return transcribed text."""
    audio = record_audio(duration)
    return transcribe(audio, language=language)