#!/usr/bin/env python3
"""Jarvis TikTok pipeline — ComfyUI-free.

Replacement for jarvis_full_pipeline.py that kept OOM-killing SRVLAB.
This one:

  Step 1: Generate image via pollinations.ai (cloud, zero RAM on SRVLAB)
  Step 2: Build Ken Burns slow-zoom video with MoviePy (CPU, bounded RAM)
  Step 3: Optional TTS voiceover
  Step 4: Text overlay
  Result: TikTok-ready .mp4

No GPU, no ComfyUI, no model loading. Heaviest step is MoviePy encoding.

Usage:
  python jarvis_pollinations_pipeline.py \\
    --prompt "cosmic nebula swirling in deep space" \\
    --text "Stars perish in eternal silence" \\
    --output /tmp/jarvis_tiktok.mp4
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

# Allow running as a script
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from core.tools.pollinations_tools import generate_image


# ─── Image step ───────────────────────────────────────────────────────

def generate_base_image(
    *,
    prompt: str,
    width: int = 1024,
    height: int = 1792,  # 9:16 TikTok aspect
    model: str = "flux",
    seed: int | None = None,
    enhance: bool = False,
) -> str:
    """Generate a base image via pollinations.ai. Returns saved path."""
    result = generate_image(
        prompt=prompt,
        width=width, height=height,
        model=model, seed=seed, enhance=enhance, nologo=True,
    )
    if result.get("status") != "ok":
        raise RuntimeError(f"pollinations image failed: {result.get('text')}")
    return str(result["path"])


# ─── Video step (Ken Burns zoom) ──────────────────────────────────────

def build_zoom_video(
    *,
    image_path: str,
    duration: float = 8.0,
    zoom_start: float = 1.0,
    zoom_end: float = 1.25,
    fps: int = 30,
    output_path: str | None = None,
) -> str:
    """Slow-zoom animation from a still image. No GPU, bounded RAM."""
    from moviepy.editor import VideoClip
    import numpy as np
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    def make_frame(t):
        progress = min(1.0, max(0.0, t / duration))
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        new_w, new_h = int(w * zoom), int(h * zoom)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))
        return np.array(cropped)

    clip = VideoClip(make_frame, duration=duration).set_fps(fps)

    if output_path is None:
        output_path = f"/tmp/jarvis_zoom_{uuid.uuid4().hex[:8]}.mp4"

    clip.write_videofile(
        output_path, fps=fps, codec="libx264",
        audio=False, preset="medium", threads=4,
        logger=None,  # quiet
    )
    clip.close()
    return output_path


# ─── Text overlay ─────────────────────────────────────────────────────

def _render_text_png(
    text: str,
    *,
    canvas_w: int,
    canvas_h: int,
    position: str = "bottom",
    font_size: int = 0,
) -> str:
    """Render wrapped text to a transparent PNG via PIL (no ImageMagick)."""
    import textwrap
    from PIL import Image, ImageDraw, ImageFont

    if font_size <= 0:
        font_size = max(28, int(canvas_h / 22))

    # Pick a reasonable font
    font = None
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(candidate):
            try:
                font = ImageFont.truetype(candidate, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    wrapped = "\n".join(textwrap.wrap(text, width=28))
    lines = wrapped.split("\n")

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Measure total block height
    line_height = int(font_size * 1.3)
    total_h = line_height * len(lines)

    # Place block by position
    if position == "top":
        top_y = int(canvas_h * 0.1)
    elif position == "center":
        top_y = int((canvas_h - total_h) / 2)
    else:  # bottom
        top_y = int(canvas_h * 0.72)

    stroke_w = max(2, font_size // 12)
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
        except Exception:
            text_w = font.getlength(line) if hasattr(font, "getlength") else font_size * len(line) // 2
        x = int((canvas_w - text_w) / 2)
        y = top_y + i * line_height
        # Draw stroke via multiple offset draws, then white fill
        try:
            draw.text(
                (x, y), line, font=font, fill=(255, 255, 255, 255),
                stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255),
            )
        except TypeError:
            # Older PIL without stroke_width
            for dx in range(-stroke_w, stroke_w + 1):
                for dy in range(-stroke_w, stroke_w + 1):
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    out_path = f"/tmp/jarvis_text_{uuid.uuid4().hex[:8]}.png"
    canvas.save(out_path, "PNG")
    return out_path


def add_text_overlay(
    *,
    video_path: str,
    text: str,
    output_path: str | None = None,
    font_size: int = 0,
    position: str = "bottom",
) -> str:
    """Burn a text overlay onto the video using PIL-rendered PNG (no ImageMagick)."""
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

    if output_path is None:
        output_path = f"/tmp/jarvis_texted_{uuid.uuid4().hex[:8]}.mp4"

    base = VideoFileClip(video_path)
    w, h = base.size

    text_png = _render_text_png(
        text, canvas_w=w, canvas_h=h,
        position=position, font_size=font_size,
    )
    text_clip = ImageClip(text_png).set_duration(base.duration)

    final = CompositeVideoClip([base, text_clip])
    final.write_videofile(
        output_path, fps=base.fps, codec="libx264",
        audio_codec="aac", preset="medium", threads=4,
        logger=None,
    )
    final.close()
    base.close()
    text_clip.close()
    try:
        os.remove(text_png)
    except Exception:
        pass
    return output_path


# ─── TTS voice (optional) ─────────────────────────────────────────────

def add_voice(
    *,
    video_path: str,
    text: str,
    output_path: str | None = None,
    voice: str = "en-US-GuyNeural",
) -> str:
    """Add a TTS voiceover via edge-tts. Returns path with audio.

    Gracefully falls back: if edge-tts is unavailable, returns the input
    video unchanged (caller should check stderr for the reason).
    """
    if output_path is None:
        output_path = f"/tmp/jarvis_voiced_{uuid.uuid4().hex[:8]}.mp4"

    try:
        import subprocess
        tts_path = f"/tmp/jarvis_tts_{uuid.uuid4().hex[:8]}.mp3"
        subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text, "--write-media", tts_path],
            check=True, capture_output=True, timeout=60,
        )
    except Exception as exc:
        print(f"[warn] TTS failed ({exc}); keeping original audio", file=sys.stderr)
        return video_path

    from moviepy.editor import VideoFileClip, AudioFileClip
    base = VideoFileClip(video_path)
    audio = AudioFileClip(tts_path)
    # Fit audio to video duration
    if audio.duration > base.duration:
        audio = audio.subclip(0, base.duration)
    base = base.set_audio(audio)
    base.write_videofile(
        output_path, fps=base.fps, codec="libx264",
        audio_codec="aac", preset="medium", threads=4,
        logger=None,
    )
    base.close()
    audio.close()
    try:
        os.remove(tts_path)
    except Exception:
        pass
    return output_path


# ─── Full pipeline ────────────────────────────────────────────────────

def run_pipeline(
    *,
    prompt: str,
    text: str,
    output_path: str = "/tmp/jarvis_tiktok_final.mp4",
    image_model: str = "flux",
    width: int = 1024,
    height: int = 1792,  # 9:16
    duration: float = 8.0,
    zoom_start: float = 1.0,
    zoom_end: float = 1.25,
    fps: int = 30,
    add_tts: bool = False,
    voice: str = "en-US-GuyNeural",
    seed: int | None = None,
    enhance_prompt: bool = False,
    keep_intermediates: bool = False,
    text_position: str = "bottom",
) -> dict:
    """Full pipeline returning dict with paths + timings."""
    start_total = time.time()
    timings: dict[str, float] = {}
    intermediates: list[str] = []

    print("=" * 60)
    print("JARVIS TIKTOK PIPELINE (pollinations + moviepy — no GPU)")
    print("=" * 60)
    print(f"Prompt:  {prompt[:100]}")
    print(f"Text:    {text[:100]}")
    print(f"Output:  {output_path}")

    # Step 1 — image
    t0 = time.time()
    print(f"\n[1/{4 if add_tts else 3}] Generating image via pollinations.ai ({image_model})...")
    image_path = generate_base_image(
        prompt=prompt, width=width, height=height,
        model=image_model, seed=seed, enhance=enhance_prompt,
    )
    timings["image_generation_s"] = round(time.time() - t0, 2)
    print(f"     → {image_path}  ({timings['image_generation_s']}s)")

    # Step 2 — zoom video
    t0 = time.time()
    print(f"\n[2/{4 if add_tts else 3}] Building Ken-Burns zoom video ({duration}s @ {fps}fps)...")
    zoom_path = build_zoom_video(
        image_path=image_path,
        duration=duration, zoom_start=zoom_start, zoom_end=zoom_end, fps=fps,
    )
    intermediates.append(zoom_path)
    timings["zoom_video_s"] = round(time.time() - t0, 2)
    print(f"     → {zoom_path}  ({timings['zoom_video_s']}s)")

    current = zoom_path

    # Step 3 — optional TTS
    if add_tts:
        t0 = time.time()
        print(f"\n[3/4] Adding TTS voiceover ({voice})...")
        voiced = add_voice(video_path=current, text=text, voice=voice)
        if voiced != current:
            intermediates.append(voiced)
            current = voiced
        timings["voice_s"] = round(time.time() - t0, 2)
        print(f"     → {current}  ({timings['voice_s']}s)")

    # Step 4 — text overlay (final output)
    t0 = time.time()
    step_n = 4 if add_tts else 3
    print(f"\n[{step_n}/{step_n}] Burning text overlay...")
    final = add_text_overlay(
        video_path=current, text=text, output_path=output_path,
        position=text_position,
    )
    timings["overlay_s"] = round(time.time() - t0, 2)
    print(f"     → {final}  ({timings['overlay_s']}s)")

    # Cleanup
    if not keep_intermediates:
        for p in intermediates:
            if p and os.path.exists(p) and "/tmp/" in p:
                try:
                    os.remove(p)
                except Exception:
                    pass

    total = round(time.time() - start_total, 2)
    print("\n" + "=" * 60)
    print(f"DONE in {total}s: {final}")
    print(f"Timings: {timings}")
    print("=" * 60)
    return {
        "output_path": final,
        "image_path": image_path,
        "duration_s": total,
        "timings": timings,
    }


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="TikTok pipeline (no GPU, no ComfyUI)")
    p.add_argument("--prompt", required=True, help="Image generation prompt")
    p.add_argument("--text", required=True, help="Text overlay")
    p.add_argument("--output", default="/tmp/jarvis_tiktok_final.mp4")
    p.add_argument("--image-model", default="flux", choices=["flux", "turbo", "variation", "anime"])
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1792)
    p.add_argument("--duration", type=float, default=8.0)
    p.add_argument("--zoom-start", type=float, default=1.0)
    p.add_argument("--zoom-end", type=float, default=1.25)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--tts", action="store_true", help="Add TTS voiceover")
    p.add_argument("--voice", default="en-US-GuyNeural")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--enhance", action="store_true", help="LLM prompt enhancement")
    p.add_argument("--keep-intermediates", action="store_true")
    p.add_argument("--text-position", default="bottom", choices=["top", "center", "bottom"])
    args = p.parse_args()

    try:
        run_pipeline(
            prompt=args.prompt,
            text=args.text,
            output_path=args.output,
            image_model=args.image_model,
            width=args.width, height=args.height,
            duration=args.duration,
            zoom_start=args.zoom_start, zoom_end=args.zoom_end,
            fps=args.fps,
            add_tts=args.tts, voice=args.voice,
            seed=args.seed,
            enhance_prompt=args.enhance,
            keep_intermediates=args.keep_intermediates,
            text_position=args.text_position,
        )
    except KeyboardInterrupt:
        print("\n[cancelled]", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"\n[error] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
