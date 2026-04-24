"""Speech-to-text using faster-whisper with VAD-gated recording."""

import os
import subprocess
from pathlib import Path

import numpy as np
import webrtcvad
from faster_whisper import WhisperModel

MODEL_SIZE = "tiny"
SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_BYTES = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # s16le

# PipeWire source for Logitech PRO USB sound card
MIC_SOURCE = "alsa_input.usb-Logitech_PRO_000000000000-00.mono-fallback"
PAREC_BIN = "/home/linuxbrew/.linuxbrew/bin/parec"

_DEBUG_LOG = Path("/tmp/jarvis-voice-debug.log")

_model_cache: WhisperModel | None = None


def _debug(msg: str) -> None:
    """Append a timestamped message to the voice debug log."""
    try:
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with _DEBUG_LOG.open("a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _drain_nonblocking(fd: int) -> int:
    """Drain all available bytes from a file descriptor. Returns bytes dropped."""
    import fcntl
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    total = 0
    try:
        while True:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            total += len(chunk)
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    return total


def get_model(model_size: str = MODEL_SIZE, device: str = "cpu", compute_type: str = "int8") -> WhisperModel:
    """Load or return cached Whisper model."""
    global _model_cache
    if _model_cache is None:
        _model_cache = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model_cache


def record_audio(duration: float = 5.0, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Record audio from USB mic via parec and return as float32 at 16 kHz."""
    _debug(f"record_audio fixed duration={duration}s")
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
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def record_audio_vad(
    max_duration: float = 10.0,
    silence_ms: int = 1500,
    startup_ms: int = 4000,
    min_speech_ms: int = 400,
) -> np.ndarray:
    """Record until user stops speaking or max_duration.

    Prefers reusing the wake-word listener's parec stream (avoids a ~20dB
    capture-gain drop on USB audio devices after TTS playback).  Falls back
    to a fresh parec if no shared stream is available.
    """
    vad = webrtcvad.Vad(1)  # low aggressiveness so we don't cut mid-sentence

    shared_stdout = None
    try:
        from core.skills.voice import wake_word as _ww
        shared_stdout = _ww.get_shared_stdout()
    except Exception:
        shared_stdout = None

    proc: subprocess.Popen | None = None
    if shared_stdout is not None:
        stdout = shared_stdout
        drained = _drain_nonblocking(stdout.fileno())
        _debug(
            f"record_audio_vad: reusing wake-word parec stream "
            f"(drained {drained} stale bytes)"
        )
    else:
        env = {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
        proc = subprocess.Popen(
            [PAREC_BIN, f"--device={MIC_SOURCE}", f"--rate={SAMPLE_RATE}",
             "--channels=1", "--format=s16le", "--latency-msec=30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        stdout = proc.stdout
        _debug("record_audio_vad: opened fresh parec (no shared stream)")

        # Warm up: discard ~1s — fresh parec after TTS comes up attenuated.
        warmup_frames = int(1000 / FRAME_MS)
        for _ in range(warmup_frames):
            chunk = stdout.read(FRAME_BYTES)
            if not chunk:
                break

    from collections import deque
    pre_roll: deque[bytes] = deque(maxlen=int(300 / FRAME_MS))  # 300ms pre-roll
    frames: list[bytes] = []
    total_frames = 0
    speech_frames_total = 0
    silence_frames = 0
    speech_started = False
    startup_frames = int(startup_ms / FRAME_MS)
    silence_limit = int(silence_ms / FRAME_MS)
    min_speech_frames = int(min_speech_ms / FRAME_MS)
    max_frames = int(max_duration * 1000 / FRAME_MS)

    try:
        while total_frames < max_frames:
            frame = stdout.read(FRAME_BYTES)
            if not frame or len(frame) < FRAME_BYTES:
                break
            total_frames += 1
            try:
                is_speech = vad.is_speech(frame, SAMPLE_RATE)
            except Exception:
                is_speech = False

            if not speech_started:
                pre_roll.append(frame)
                if is_speech:
                    speech_started = True
                    frames.extend(pre_roll)
                    speech_frames_total += 1
                elif total_frames >= startup_frames:
                    _debug(f"record_audio_vad: no speech within {startup_ms}ms, aborting")
                    break
            else:
                frames.append(frame)
                if is_speech:
                    speech_frames_total += 1
                    silence_frames = 0
                else:
                    silence_frames += 1
                    # only stop on silence if we've captured enough speech
                    if (
                        silence_frames >= silence_limit
                        and speech_frames_total >= min_speech_frames
                    ):
                        break
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait()

    if not frames:
        _debug("record_audio_vad: returned empty audio")
        return np.zeros(0, dtype=np.float32)

    raw = b"".join(frames)
    audio_i16 = np.frombuffer(raw, dtype=np.int16)
    peak = int(np.max(np.abs(audio_i16))) if audio_i16.size else 0
    rms = float(np.sqrt(np.mean(audio_i16.astype(np.float32) ** 2))) if audio_i16.size else 0.0
    _debug(
        f"record_audio_vad: captured {len(frames)*FRAME_MS}ms "
        f"({total_frames*FRAME_MS}ms total, speech_started={speech_started}, "
        f"peak={peak}/32768, rms={rms:.0f})"
    )

    if os.environ.get("JARVIS_VOICE_DUMP_WAV"):
        try:
            import wave
            dump_path = Path("/tmp/jarvis-voice-last.wav")
            with wave.open(str(dump_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(raw)
            _debug(f"record_audio_vad: dumped to {dump_path}")
        except Exception as exc:
            _debug(f"record_audio_vad: dump failed: {exc}")

    return audio_i16.astype(np.float32) / 32768.0


def _normalize(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
    """RMS-normalize float32 audio to target_rms.

    Peak-normalization over-amplifies single loud clicks.  Targeting RMS is
    more robust for speech that has a wide dynamic range.  Gain is capped
    so we do not blow out silence-only input into painful noise.
    """
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-5:
        return audio
    gain = min(target_rms / rms, 50.0)
    return np.clip(audio * gain, -1.0, 1.0).astype(np.float32)


def transcribe(audio: np.ndarray, model: WhisperModel | None = None, language: str = "en") -> str:
    """Transcribe numpy audio array to text."""
    if audio.size == 0:
        _debug("transcribe: empty audio, skipping")
        return ""
    if model is None:
        model = get_model()

    pre_rms = float(np.sqrt(np.mean(audio ** 2)))
    audio = _normalize(audio)
    post_rms = float(np.sqrt(np.mean(audio ** 2)))
    post_peak = float(np.max(np.abs(audio)))
    _debug(
        f"transcribe: normalized rms {pre_rms:.5f} → {post_rms:.4f} "
        f"(peak {post_peak:.3f})"
    )

    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=1,
        condition_on_previous_text=False,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    _debug(
        f"transcribe: lang={info.language} prob={info.language_probability:.2f} "
        f"duration={info.duration:.2f}s → {text!r}"
    )
    return text


def listen_and_transcribe(duration: float = 5.0, language: str = "da") -> str:
    """Record command from mic (VAD-gated) and return transcribed text."""
    audio = record_audio_vad(max_duration=max(duration, 10.0))
    return transcribe(audio, language=language)