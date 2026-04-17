#!/usr/bin/env python3
"""
Jarvis TikTok Video Pipeline
Generates satisfying zoom videos from images with optional text overlay.
Uses MoviePy v1.0.3 (moviepy.editor imports)
"""
import argparse
import os
import random
import textwrap

from moviepy.editor import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    AudioFileClip,
    concatenate_videoclips,
)
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_zoom_video(image_path, duration=15, zoom_start=1.0, zoom_end=1.3,
                      fps=30, output_path=None):
    """Create a satisfying slow-zoom video from an image."""
    img = Image.open(image_path)
    w, h = img.size

    def make_frame(t):
        progress = t / duration
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        new_w = int(w * zoom)
        new_h = int(h * zoom)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        # Center crop back to original size
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))
        return np.array(cropped)

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_fps(fps)

    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_video.mp4"

    clip.write_videofile(output_path, fps=fps, codec="libx264",
                         audio=False, preset="medium", threads=4)
    return output_path


def add_text_overlay(image_path, text, font_size=0, color="white",
                     output_path=None):
    """Add centered text overlay to an image.

    Font size and line width adapt to text length so the text always
    fits within the lower third of the image (max 40 % of image height).
    """
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    # Try to find a font
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    font_path = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break

    # --- Adaptive sizing: iterate until text fits ---
    max_text_height = int(img_h * 0.28)   # text must not exceed 28 % of image
    max_text_width  = int(img_w  * 0.85)  # 85 % horizontal margin

    word_count = len(text.split())

    # Initial guesses: keep font small enough for TikTok readability
    if font_size <= 0:
        if word_count <= 4:
            font_size = 32
        elif word_count <= 7:
            font_size = 28
        elif word_count <= 10:
            font_size = 24
        else:
            font_size = 20

    # Adaptive wrap width: fewer words → wider lines allowed
    if word_count <= 5:
        max_chars = 28
    elif word_count <= 8:
        max_chars = 22
    else:
        max_chars = 18

    for attempt in range(8):
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()

        lines = textwrap.wrap(text, width=max_chars)
        text_str = "\n".join(lines)

        bbox = draw.multiline_textbbox((0, 0), text_str, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_h <= max_text_height and text_w <= max_text_width:
            break  # fits!

        # Shrink and retry
        font_size = max(font_size - 4, 16)
        max_chars = min(max_chars + 3, 35)

    # Center text in lower third
    x = (img_w - text_w) // 2
    y = int(img_h * 0.68)

    # Make sure text doesn't go below image
    if y + text_h > img_h - 20:
        y = img_h - text_h - 20

    # Shadow
    draw.multiline_text((x + 2, y + 2), text_str, font=font, fill="black",
                        align="center")
    # Main text
    draw.multiline_text((x, y), text_str, font=font, fill=color,
                        align="center")

    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_text.png"

    img.convert("RGB").save(output_path)
    return output_path


def create_quote_video(image_path, quote, duration=15, zoom_start=1.0,
                       zoom_end=1.15, fps=30, output_path=None):
    """Create a satisfying zoom video with a motivational quote overlay."""
    # First add text to image
    text_img = add_text_overlay(image_path, quote)

    # Then create zoom video
    output = create_zoom_video(text_img, duration=duration,
                               zoom_start=zoom_start, zoom_end=zoom_end,
                               fps=fps, output_path=output_path)

    # Clean up temp text image
    if os.path.exists(text_img) and "_text" in text_img:
        os.remove(text_img)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis TikTok Video Pipeline")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--quote", default=None, help="Quote text overlay")
    parser.add_argument("--no-text", action="store_true", help="No text overlay")
    parser.add_argument("--duration", type=int, default=15, help="Video duration in seconds")
    parser.add_argument("--output", default=None, help="Output video path")
    args = parser.parse_args()

    # Import VideoClip here since it's from the base module
    from moviepy.editor import VideoClip

    if args.no_text or args.quote is None:
        result = create_zoom_video(args.image, duration=args.duration,
                                   output_path=args.output)
    else:
        result = create_quote_video(args.image, args.quote,
                                    duration=args.duration,
                                    output_path=args.output)

    print(f"DONE: {result}")