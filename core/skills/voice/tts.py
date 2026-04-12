"""Text-to-speech using edge-tts with British male voices."""

import asyncio
import subprocess
import tempfile
from pathlib import Path

# Preferred voices: Danish male first, British male fallback
VOICES = ["da-DK-JeppeNeural", "en-GB-RyanNeural"]
DEFAULT_VOICE = VOICES[0]


async def synthesize(text: str, voice: str = DEFAULT_VOICE, output_path: str | None = None) -> str:
    """Synthesize text to speech and return path to audio file."""
    import edge_tts

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp3", prefix="jarvis_voice_")

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path


def say(text: str, voice: str = DEFAULT_VOICE, blocking: bool = True) -> str:
    """Synthesize and play audio. Returns the audio file path."""
    output_path = asyncio.run(synthesize(text, voice))

    if blocking:
        play_audio(output_path)
    else:
        import threading
        threading.Thread(target=play_audio, args=(output_path,), daemon=True).start()

    return output_path


def play_audio(path: str) -> None:
    """Play an audio file through PulseAudio/PipeWire default sink."""
    # Convert to WAV first so paplay can handle any source format
    wav_path = path + ".play.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-ar", "48000", "-ac", "2", wav_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    try:
        # paplay routes to system default sink (Bluetooth, analog — whatever is active)
        subprocess.run(["paplay", wav_path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        # Fallback to ffplay
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    finally:
        try:
            Path(wav_path).unlink()
        except OSError:
            pass