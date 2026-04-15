#!/usr/bin/env python3
"""
Jarvis Audio Pipeline for TikTok videos.
Generates voiceover (edge-tts), ambient background (scipy),
mixes them, and merges with video using ffmpeg.
"""

import argparse
import subprocess
import sys
import os
import tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter


def generate_voiceover(text: str, voice: str, output_path: str):
    """Generate TTS voiceover using edge-tts."""
    import asyncio
    import edge_tts

    async def _gen():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    
    asyncio.run(_gen())
    print(f"[voiceover] Saved to {output_path}")


def generate_ambient(duration: float, sample_rate: int = 44100, output_path: str = "ambient.wav"):
    """Generate a cosmic/ambient background sound."""
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    
    # Deep drone base - low frequency
    drone = np.sin(2 * np.pi * 55 * t) * 0.3  # A1
    drone += np.sin(2 * np.pi * 82.5 * t) * 0.2  # E2 harmonic
    drone += np.sin(2 * np.pi * 110 * t) * 0.15  # A2 octave
    
    # Slow modulation for breathing feel
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)  # Very slow LFO
    drone *= mod
    
    # Shimmering high frequencies
    shimmer = np.sin(2 * np.pi * 880 * t) * 0.02 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.3 * t))
    shimmer += np.sin(2 * np.pi * 1320 * t) * 0.015 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t))
    
    # Pink noise for texture
    noise = np.random.normal(0, 0.008, len(t))
    # Simple lowpass via rolling mean
    kernel = 500
    noise = np.convolve(noise, np.ones(kernel)/kernel, mode='same')
    
    # Combine
    audio = drone + shimmer + noise
    
    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.7
    
    # Convert to 16-bit PCM
    audio_int = (audio * 32767).astype(np.int16)
    wavfile.write(output_path, sample_rate, audio_int)
    print(f"[ambient] Saved {duration}s audio to {output_path}")


def mix_audio(voice_path: str, ambient_path: str, output_path: str, voice_vol: float = 1.0, ambient_vol: float = 0.4):
    """Mix voice and ambient using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", voice_path,
        "-i", ambient_path,
        "-filter_complex",
        f"[0:a]volume={voice_vol}[v];[1:a]volume={ambient_vol}[a];[v][a]amix=inputs=2:duration=longest:dropout_transition=3[out]",
        "-map", "[out]",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"[mix] Mixed audio saved to {output_path}")


def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """Merge audio track with video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"[merge] Final video saved to {output_path}")


def full_pipeline(
    video_path: str,
    text: str = "",
    voice: str = "da-DK-ChristelNeural",
    ambient_duration: float = 20.0,
    voice_vol: float = 1.0,
    ambient_vol: float = 0.35,
    output_path: str = ""
):
    """Run the full audio pipeline: voiceover + ambient → mix → merge with video."""
    
    if not output_path:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_with_audio.mp4"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        voice_wav = os.path.join(tmpdir, "voice.wav")
        ambient_wav = os.path.join(tmpdir, "ambient.wav")
        mixed_aac = os.path.join(tmpdir, "mixed.m4a")
        
        # Step 1: Generate voiceover (if text provided)
        if text:
            print(f"[pipeline] Generating voiceover: '{text[:50]}...'")
            generate_voiceover(text, voice, voice_wav)
        else:
            # No voiceover, just ambient
            voice_wav = None
        
        # Step 2: Generate ambient background
        print("[pipeline] Generating ambient background...")
        generate_ambient(ambient_duration, output_path=ambient_wav)
        
        # Step 3: Mix
        if voice_wav:
            print("[pipeline] Mixing voice + ambient...")
            mix_audio(voice_wav, ambient_wav, mixed_aac, voice_vol=voice_vol, ambient_vol=ambient_vol)
        else:
            # Just convert ambient to aac
            cmd = ["ffmpeg", "-y", "-i", ambient_wav, "-c:a", "aac", "-b:a", "128k", mixed_aac]
            subprocess.run(cmd, check=True)
        
        # Step 4: Merge with video
        print("[pipeline] Merging audio with video...")
        merge_audio_video(video_path, mixed_aac, output_path)
    
    # Verify
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n✅ DONE: {output_path} ({size_mb:.1f} MB)")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis Audio Pipeline for TikTok")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--text", default="", help="Voiceover text (empty = ambient only)")
    parser.add_argument("--voice", default="da-DK-ChristelNeural", help="edge-tts voice name")
    parser.add_argument("--ambient-vol", type=float, default=0.35, help="Ambient volume (0-1)")
    parser.add_argument("--voice-vol", type=float, default=1.0, help="Voice volume (0-1)")
    parser.add_argument("--duration", type=float, default=20.0, help="Ambient duration in seconds")
    parser.add_argument("--output", default="", help="Output video path")
    
    args = parser.parse_args()
    full_pipeline(
        video_path=args.video,
        text=args.text,
        voice=args.voice,
        ambient_duration=args.duration,
        voice_vol=args.voice_vol,
        ambient_vol=args.ambient_vol,
        output_path=args.output,
    )