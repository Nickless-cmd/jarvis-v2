#!/usr/bin/env python3
"""
Jarvis Full TikTok Pipeline
End-to-end: SDXL image → SVD animation → text overlay → TikTok-ready video

Usage:
  python jarvis_full_pipeline.py --prompt "cosmic nebula" --text "Stars perish in eternal silence" --output /tmp/jarvis_tiktok.mp4

All generation happens locally via ComfyUI on the RTX 2080 SUPER.
No external APIs. No cloud. All mine.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import textwrap
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


COMFY_URL = "http://localhost:8188"
COMFY_OUTPUT_DIR = Path("/home/bs/ai/ComfyUI/output")
SDXL_CHECKPOINT = "sd_xl_base_1.0.safetensors"
SVD_CHECKPOINT = "svd_xt.safetensors"


# ═══════════════════════════════════════════════════════════════
# ComfyUI API helpers
# ═══════════════════════════════════════════════════════════════

def upload_image(image_path: str, comfy_url: str = COMFY_URL) -> str:
    """Upload image to ComfyUI and return server-side filename."""
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{comfy_url}/upload/image",
            files={"image": (Path(image_path).name, f, "image/png")},
            data={"overwrite": "true"},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()["name"]


def submit_workflow(workflow: dict, comfy_url: str = COMFY_URL) -> str:
    """Submit workflow to ComfyUI queue, return prompt_id."""
    client_id = uuid.uuid4().hex
    payload = {"prompt": workflow, "client_id": client_id}
    resp = requests.post(f"{comfy_url}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_completion(prompt_id: str, comfy_url: str = COMFY_URL, timeout: int = 600, poll: float = 3.0) -> dict:
    """Poll /history until prompt completes."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{comfy_url}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("completed"):
                return entry.get("outputs", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {status}")
        time.sleep(poll)
    raise TimeoutError(f"Generation timed out after {timeout}s")


def find_output(outputs: dict, key: str = "images") -> tuple[str | None, str | None]:
    """Find output filename and subfolder from ComfyUI outputs."""
    for node_outputs in outputs.values():
        for item in node_outputs.get(key, []):
            filename = item.get("filename")
            subfolder = item.get("subfolder", "")
            if filename:
                return filename, subfolder
    return None, None


def download_output(filename: str, subfolder: str, dest_path: str, comfy_url: str = COMFY_URL) -> str:
    """Download/copy output from ComfyUI."""
    src_dir = COMFY_OUTPUT_DIR / subfolder if subfolder else COMFY_OUTPUT_DIR
    src_path = src_dir / filename
    if src_path.exists():
        shutil.copy2(str(src_path), dest_path)
        return dest_path
    # Fallback: API download
    params = {"filename": filename, "type": "output"}
    if subfolder:
        params["subfolder"] = subfolder
    resp = requests.get(f"{comfy_url}/view", params=params, timeout=60, stream=True)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


# ═══════════════════════════════════════════════════════════════
# Step 1: Generate image with SDXL
# ═══════════════════════════════════════════════════════════════

def build_sdxl_workflow(prompt: str, negative: str, width: int, height: int, steps: int, output_prefix: str) -> dict:
    """SDXL text-to-image workflow."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": SDXL_CHECKPOINT},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": int(time.time()) % 2**32,
                "steps": steps,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": output_prefix,
            },
        },
    }


def generate_sdxl_image(
    prompt: str,
    negative: str = "blurry, low quality, watermark, text, ugly, deformed",
    width: int = 576,
    height: int = 1024,
    steps: int = 30,
    comfy_url: str = COMFY_URL,
) -> str:
    """Generate image with SDXL, return local file path."""
    output_prefix = f"jarvis_sdxl_{uuid.uuid4().hex[:8]}"
    workflow = build_sdxl_workflow(prompt, negative, width, height, steps, output_prefix)

    print(f"[sdxl] Generating image: {prompt[:60]}...")
    prompt_id = submit_workflow(workflow, comfy_url)
    print(f"[sdxl] Waiting... (prompt_id={prompt_id})")
    outputs = wait_for_completion(prompt_id, comfy_url, timeout=300)

    filename, subfolder = find_output(outputs, "images")
    if not filename:
        raise RuntimeError("No image output from SDXL")

    dest = f"/tmp/jarvis_sdxl_{uuid.uuid4().hex[:8]}.png"
    download_output(filename, subfolder or "", dest, comfy_url)
    print(f"[sdxl] Image saved: {dest}")
    return dest


# ═══════════════════════════════════════════════════════════════
# Step 2: Animate with SVD
# ═══════════════════════════════════════════════════════════════

def build_svd_workflow(
    image_name: str, width: int, height: int, frames: int, fps: int,
    motion: int, steps: int, output_prefix: str,
) -> dict:
    """SVD img2vid workflow."""
    return {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": SVD_CHECKPOINT},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name, "upload": "image"},
        },
        "3": {
            "class_type": "SVD_img2vid_Conditioning",
            "inputs": {
                "clip_vision": ["1", 1],
                "init_image": ["2", 0],
                "vae": ["1", 2],
                "width": width,
                "height": height,
                "video_frames": frames,
                "motion_bucket_id": motion,
                "fps": fps,
                "augmentation_level": 0.0,
            },
        },
        "4": {
            "class_type": "VideoLinearCFGGuidance",
            "inputs": {"model": ["1", 0], "min_cfg": 1.0},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["3", 0],
                "negative": ["3", 1],
                "latent_image": ["3", 2],
                "seed": int(time.time()) % 2**32,
                "steps": steps,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["6", 0], "fps": float(fps)},
        },
        "8": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["7", 0],
                "filename_prefix": output_prefix,
                "format": "mp4",
                "codec": "h264",
            },
        },
    }


def generate_svd_video(
    image_path: str,
    width: int = 576,
    height: int = 1024,
    frames: int = 25,
    fps: int = 6,
    motion: int = 100,
    steps: int = 20,
    comfy_url: str = COMFY_URL,
) -> str:
    """Animate image with SVD, return video file path."""
    # Resize input
    img = Image.open(image_path).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        new_h = img.height
        new_w = int(new_h * target_ratio)
    else:
        new_w = img.width
        new_h = int(new_w / target_ratio)
    left = (img.width - new_w) // 2
    top = (img.height - new_h) // 2
    img = img.crop((left, top, left + new_w, top + new_h))
    img = img.resize((width, height), Image.LANCZOS)

    tmp_img = f"/tmp/jarvis_svd_input_{uuid.uuid4().hex[:8]}.png"
    img.save(tmp_img)

    try:
        print(f"[svd] Uploading image...")
        server_name = upload_image(tmp_img, comfy_url)

        output_prefix = f"jarvis_svd_{uuid.uuid4().hex[:8]}"
        workflow = build_svd_workflow(
            server_name, width, height, frames, fps, motion, steps, output_prefix,
        )

        print(f"[svd] Animating ({frames} frames @ {fps}fps, motion={motion})...")
        prompt_id = submit_workflow(workflow, comfy_url)
        print(f"[svd] Rendering... (prompt_id={prompt_id})")
        outputs = wait_for_completion(prompt_id, comfy_url, timeout=600)

        # Check for video or images
        filename, subfolder = find_output(outputs, "videos")
        key = "videos"
        if not filename:
            filename, subfolder = find_output(outputs, "gifs")
            key = "gifs"
        if not filename:
            filename, subfolder = find_output(outputs, "images")
            key = "images"

        if not filename:
            raise RuntimeError("No output from SVD")

        dest = f"/tmp/jarvis_svd_{uuid.uuid4().hex[:8]}.mp4"
        download_output(filename, subfolder or "", dest, comfy_url)
        print(f"[svd] Video saved: {dest}")
        return dest
    finally:
        if os.path.exists(tmp_img):
            os.remove(tmp_img)


# ═══════════════════════════════════════════════════════════════
# Step 3a: Loop video with FFmpeg
# ═══════════════════════════════════════════════════════════════

def loop_video(video_path: str, output_path: str, loop_count: int = 3) -> str:
    """Loop a video N times using FFmpeg stream_loop. Returns output path."""
    if loop_count <= 1:
        shutil.copy2(video_path, output_path)
        return output_path
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count - 1),
        "-i", video_path,
        "-c", "copy",
        output_path,
    ]
    print(f"[loop] Looping video {loop_count}x → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: copy without looping
        shutil.copy2(video_path, output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════
# Step 3b: Add audio (TTS voiceover + ambient)
# ═══════════════════════════════════════════════════════════════

AUDIO_PIPELINE = "/home/bs/ai/jarvis_audio_pipeline.py"

def add_audio(
    video_path: str,
    text: str,
    output_path: str,
    voice: str = "en-US-GuyNeural",
    ambient_vol: float = 0.35,
) -> str:
    """Add TTS voiceover + ambient audio using jarvis_audio_pipeline.py."""
    cmd = [
        sys.executable, AUDIO_PIPELINE,
        "--video", video_path,
        "--text", text,
        "--voice", voice,
        "--ambient-vol", str(ambient_vol),
        "--output", output_path,
    ]
    print(f"[audio] Adding voiceover: '{text[:50]}...'")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not os.path.exists(output_path):
        # Non-fatal: keep video without audio
        shutil.copy2(video_path, output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════
# Step 3c: Add text overlay (PIL + FFmpeg)
# ═══════════════════════════════════════════════════════════════

def add_text_to_video(video_path: str, text: str, output_path: str, font_size: int = 0) -> str:
    """Add centered text overlay to video using FFmpeg drawtext filter.

    Auto-wraps long text into multiple lines and scales font size to fit
    within a 9:16 (576x1024) video frame.
    """
    # --- word-wrap ---
    wrapped_lines = textwrap.wrap(text, width=28)

    # --- auto-scale font size based on line count ---
    num_lines = len(wrapped_lines)
    if font_size <= 0:
        if num_lines <= 1:
            font_size = 28
        elif num_lines == 2:
            font_size = 24
        elif num_lines == 3:
            font_size = 20
        else:
            font_size = 16

    line_height = int(font_size * 1.45)
    # Start y so the block is centered around h*0.65
    total_block_h = num_lines * line_height
    start_y_expr = f"h*0.65 - {total_block_h // 2}"

    # Find font
    font_file = None
    for fp in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(fp):
            font_file = fp
            break

    if font_file:
        font_arg = f"fontfile={font_file}"
    else:
        font_arg = "font='DejaVu Sans Bold'"

    # Build one drawtext filter per line, stacked vertically
    filters = []
    for i, line in enumerate(wrapped_lines):
        escaped = line.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")
        y_offset = start_y_expr + i * line_height if isinstance(start_y_expr, int) else f"({start_y_expr})+{i * line_height}"
        filt = (
            f"drawtext={font_arg}:"
            f"text='{escaped}':"
            f"fontsize={font_size}:"
            f"fontcolor=white:"
            f"borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:"
            f"y={y_offset}"
        )
        filters.append(filt)

    filter_complex = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", filter_complex,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        output_path,
    ]

    print(f"[text] Adding text overlay: '{text}' ({num_lines} lines, font={font_size})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    print(f"[text] Output: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════════
# Step 4: Full pipeline
# ═══════════════════════════════════════════════════════════════

def run_full_pipeline(
    prompt: str,
    text: str,
    output_path: str = "/tmp/jarvis_tiktok_final.mp4",
    sdxl_steps: int = 25,
    svd_frames: int = 25,
    svd_fps: int = 6,
    svd_motion: int = 100,
    svd_steps: int = 20,
    width: int = 576,
    height: int = 1024,
    loop_count: int = 3,
    voice: str = "en-US-GuyNeural",
    add_voice: bool = False,
    comfy_url: str = COMFY_URL,
) -> str:
    """Full pipeline: SDXL → SVD → loop → audio → text overlay → final video."""
    steps_total = 3 + (1 if loop_count > 1 else 0) + (1 if add_voice else 0)
    step = 0

    print("=" * 60)
    print("JARVIS FULL TIKTOK PIPELINE")
    print("=" * 60)

    intermediates = []

    # Step 1: Generate base image with SDXL
    step += 1
    print(f"\n[{step}/{steps_total}] Generating image with SDXL...")
    image_path = generate_sdxl_image(
        prompt=prompt, width=width, height=height,
        steps=sdxl_steps, comfy_url=comfy_url,
    )
    intermediates.append(image_path)

    # Step 2: Animate with SVD
    step += 1
    print(f"\n[{step}/{steps_total}] Animating with SVD...")
    raw_video = generate_svd_video(
        image_path=image_path, width=width, height=height,
        frames=svd_frames, fps=svd_fps, motion=svd_motion,
        steps=svd_steps, comfy_url=comfy_url,
    )
    intermediates.append(raw_video)

    # Step 3 (optional): Loop video to desired length
    current = raw_video
    if loop_count > 1:
        step += 1
        print(f"\n[{step}/{steps_total}] Looping video {loop_count}x...")
        looped = f"/tmp/jarvis_looped_{uuid.uuid4().hex[:8]}.mp4"
        current = loop_video(current, looped, loop_count)
        intermediates.append(looped)

    # Step 4 (optional): Add TTS voiceover + ambient audio
    if add_voice:
        step += 1
        print(f"\n[{step}/{steps_total}] Adding audio...")
        voiced = f"/tmp/jarvis_voiced_{uuid.uuid4().hex[:8]}.mp4"
        current = add_audio(current, text, voiced, voice=voice)
        intermediates.append(voiced)

    # Step 5: Add text overlay
    step += 1
    print(f"\n[{step}/{steps_total}] Adding text overlay...")
    final = add_text_to_video(current, text, output_path)

    # Cleanup intermediates (not the final output)
    for f in intermediates:
        if f and os.path.exists(f) and "/tmp/" in f:
            try:
                os.remove(f)
            except Exception:
                pass

    print("\n" + "=" * 60)
    print(f"DONE: {final}")
    print("=" * 60)
    return final


# ═══════════════════════════════════════════════════════════════
# Batch mode
# ═══════════════════════════════════════════════════════════════

def run_batch_pipeline(
    items: list[dict],
    output_dir: str = "/tmp/",
    **kwargs,
) -> list[str]:
    """Run full pipeline for multiple (prompt, text) pairs.

    items: list of dicts with keys 'prompt', 'text', and optionally 'output'.
    kwargs: passed to run_full_pipeline (loop_count, add_voice, etc.)

    Returns list of output paths.
    """
    results = []
    total = len(items)
    for i, item in enumerate(items, 1):
        prompt = item["prompt"]
        text = item["text"]
        out = item.get("output") or os.path.join(output_dir, f"jarvis_batch_{i:03d}.mp4")
        print(f"\n{'='*60}")
        print(f"BATCH {i}/{total}: {text[:50]}")
        print(f"{'='*60}")
        try:
            path = run_full_pipeline(prompt=prompt, text=text, output_path=out, **kwargs)
            results.append(path)
            print(f"✅ Batch {i}/{total} done: {path}")
        except Exception as exc:
            print(f"❌ Batch {i}/{total} failed: {exc}")
            results.append("")
    return results


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis Full TikTok Pipeline")
    parser.add_argument("--prompt", help="SDXL image prompt (single mode)")
    parser.add_argument("--text", help="Text overlay (single mode)")
    parser.add_argument("--output", default="/tmp/jarvis_tiktok_final.mp4", help="Output path")
    parser.add_argument("--width", type=int, default=576)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--sdxl-steps", type=int, default=25)
    parser.add_argument("--svd-frames", type=int, default=25)
    parser.add_argument("--svd-fps", type=int, default=6)
    parser.add_argument("--svd-motion", type=int, default=100)
    parser.add_argument("--svd-steps", type=int, default=20)
    parser.add_argument("--loop", type=int, default=3, help="Loop video N times (default 3, ~12s total)")
    parser.add_argument("--voice", default="en-US-GuyNeural", help="edge-tts voice for TTS")
    parser.add_argument("--add-voice", action="store_true", help="Add TTS voiceover + ambient audio")
    parser.add_argument("--batch", help="JSON file with list of {prompt, text} for batch mode")
    parser.add_argument("--batch-output-dir", default="/tmp/", help="Output dir for batch mode")
    args = parser.parse_args()

    kwargs = dict(
        sdxl_steps=args.sdxl_steps,
        svd_frames=args.svd_frames,
        svd_fps=args.svd_fps,
        svd_motion=args.svd_motion,
        svd_steps=args.svd_steps,
        width=args.width,
        height=args.height,
        loop_count=args.loop,
        voice=args.voice,
        add_voice=args.add_voice,
    )

    if args.batch:
        import json as _json
        items = _json.loads(Path(args.batch).read_text())
        results = run_batch_pipeline(items, output_dir=args.batch_output_dir, **kwargs)
        print("\nBatch results:")
        for i, r in enumerate(results, 1):
            print(f"  {i}: {r or '(failed)'}")
    else:
        if not args.prompt or not args.text:
            parser.error("--prompt and --text are required in single mode")
        run_full_pipeline(
            prompt=args.prompt,
            text=args.text,
            output_path=args.output,
            **kwargs,
        )