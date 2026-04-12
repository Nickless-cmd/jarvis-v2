"""Text-to-speech — ElevenLabs (primary) with edge-tts fallback."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

# ElevenLabs: George — British, warm, captivating (fits Jarvis well)
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
# edge-tts fallback voices
EDGE_VOICES = ["da-DK-JeppeNeural", "en-GB-RyanNeural"]

_FFMPEG = "/home/linuxbrew/.linuxbrew/bin/ffmpeg"
_PAPLAY = "/home/linuxbrew/.linuxbrew/bin/paplay"
_FFPLAY = "/home/linuxbrew/.linuxbrew/bin/ffplay"


def _get_elevenlabs_key() -> str | None:
    try:
        import json
        from pathlib import Path as P
        cfg = P.home() / ".jarvis-v2" / "config" / "runtime.json"
        return json.loads(cfg.read_text()).get("elevenlabs_api_key")
    except Exception:
        return None


def _synthesize_elevenlabs(text: str) -> str:
    """Generate MP3 via ElevenLabs API. Returns path to temp file."""
    from elevenlabs.client import ElevenLabs
    key = _get_elevenlabs_key()
    if not key:
        raise RuntimeError("No ElevenLabs API key")
    client = ElevenLabs(api_key=key)
    audio = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    path = tempfile.mktemp(suffix=".mp3", prefix="jarvis_el_")
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return path


async def _synthesize_edge(text: str) -> str:
    """Generate MP3 via edge-tts. Returns path to temp file."""
    import edge_tts
    path = tempfile.mktemp(suffix=".mp3", prefix="jarvis_edge_")
    communicate = edge_tts.Communicate(text, EDGE_VOICES[0])
    await communicate.save(path)
    return path


def _pipewire_env() -> dict:
    import os
    return {**os.environ, "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}


def play_audio(path: str) -> None:
    """Play an audio file through PipeWire/PulseAudio default sink."""
    wav_path = path + ".play.wav"
    subprocess.run(
        [_FFMPEG, "-y", "-i", path, "-ar", "48000", "-ac", "2", wav_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    try:
        subprocess.run(
            [_PAPLAY, wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_pipewire_env(),
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run(
            [_FFPLAY, "-nodisp", "-autoexit", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    finally:
        try:
            Path(wav_path).unlink()
        except OSError:
            pass


def say(text: str, blocking: bool = True) -> str:
    """Synthesize and play text. ElevenLabs primary, edge-tts fallback."""
    try:
        path = _synthesize_elevenlabs(text)
    except Exception as e:
        print(f"[tts] ElevenLabs failed ({e}), falling back to edge-tts")
        path = asyncio.run(_synthesize_edge(text))

    if blocking:
        play_audio(path)
    else:
        import threading
        threading.Thread(target=play_audio, args=(path,), daemon=True).start()

    try:
        Path(path).unlink()
    except OSError:
        pass

    return path
