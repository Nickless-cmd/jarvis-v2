"""Text-to-speech — ElevenLabs (primary) with edge-tts fallback."""

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Default: Mathias — Danish, engaging, natural, warm (jutlandic accent).
# Picked 2026-05-09 by Bjørn after sampling against Jesper + Constantin.
# Override via env JARVIS_TTS_VOICE_ID for quick swaps without code change.
# Alternatives: Jesper=Bl1YwS3uJac5zEOSNESn (calm deep professional, rigsdansk),
#               Constantin=Hp07ONf6C5qlCKOeB4oo (calm soothing, rigsdansk),
#               Søren=xj6X4BCUsv9oxohm1E8o (confident versatile, rigsdansk),
#               Camilla=4RklGmuxoAskAbGXplXN (female engaging),
#               George=JBFqnCBsd6RMkjVDRZzb (English, prior default).
ELEVENLABS_VOICE_ID = os.environ.get(
    "JARVIS_TTS_VOICE_ID", "ygiXC2Oa1BiHksD3WkJZ"
)
# edge-tts fallback voices — Danish primary, English fallback
EDGE_VOICES = ["da-DK-JeppeNeural", "en-GB-RyanNeural"]

# Resolve audio-playback binaries dynamically (conda env vs system PATH).
# Fallback paths for the conda ai environment where these are installed.
_CONDA_BIN = Path("/home/bs/miniconda3/envs/ai/bin")
_FFMPEG = shutil.which("ffmpeg") or str(_CONDA_BIN / "ffmpeg")
_PAPLAY = shutil.which("paplay") or str(_CONDA_BIN / "paplay")
_FFPLAY = shutil.which("ffplay") or str(_CONDA_BIN / "ffplay")


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
        model_id="eleven_flash_v2_5",
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


def _run_edge_tts_in_thread(text: str) -> str:
    """Run edge-tts in a dedicated thread+loop (handles both sync/async callers)."""
    import threading
    result: list[str | None] = [None]
    exc: list[Exception | None] = [None]

    def _target():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result[0] = new_loop.run_until_complete(_synthesize_edge(text))
        except Exception as e:
            exc[0] = e
        finally:
            new_loop.close()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    if exc[0]:
        raise exc[0]
    return result[0]  # type: ignore[return-value]


def _edge_fallback(text: str) -> str:
    """Synthesize via edge-tts, handling both sync and async callers."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — normal sync caller
        return asyncio.run(_synthesize_edge(text))
    # Running loop exists — use dedicated thread
    return _run_edge_tts_in_thread(text)


def say(text: str, blocking: bool = True) -> str:
    """Synthesize and play text. ElevenLabs primary, edge-tts fallback."""
    try:
        path = _synthesize_elevenlabs(text)
    except Exception as e:
        print(f"[tts] ElevenLabs failed ({e}), falling back to edge-tts")
        path = _edge_fallback(text)

    if blocking:
        play_audio(path)
        try:
            Path(path).unlink()
        except OSError:
            pass
    else:
        def _play_and_cleanup():
            play_audio(path)
            try:
                Path(path).unlink()
            except OSError:
                pass
        import threading
        threading.Thread(target=_play_and_cleanup, daemon=True).start()

    return path
