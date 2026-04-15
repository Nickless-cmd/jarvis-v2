#!/usr/bin/env python3
"""
Jarvis SVD Video Pipeline
Generates animated videos from images using Stable Video Diffusion via ComfyUI API.

Usage:
  python jarvis_svd_pipeline.py --image input.png --output output.mp4 [options]

Options:
  --image PATH         Input image path (required)
  --output PATH        Output video path (default: /tmp/jarvis_svd_output.mp4)
  --width INT          Width in pixels (default: 576)
  --height INT         Height in pixels (default: 1024, TikTok vertical)
  --frames INT         Number of frames (default: 25)
  --fps INT            Frames per second (default: 6)
  --motion INT         Motion bucket id — 1=subtle, 255=max (default: 100)
  --steps INT          Sampling steps (default: 20)
  --comfy-url URL      ComfyUI server URL (default: http://localhost:8188)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

import requests
from PIL import Image


COMFY_URL = "http://localhost:8188"
COMFY_OUTPUT_DIR = Path("/home/bs/ai/ComfyUI/output")
SVD_CHECKPOINT = "svd_xt.safetensors"


# ---------------------------------------------------------------------------
# ComfyUI workflow builder
# ---------------------------------------------------------------------------

def _build_svd_workflow(
    image_name: str,
    width: int,
    height: int,
    frames: int,
    fps: int,
    motion: int,
    steps: int,
    output_prefix: str,
) -> dict:
    """Build ComfyUI prompt JSON for SVD img2vid."""
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
            "inputs": {
                "model": ["1", 0],
                "min_cfg": 1.0,
            },
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
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["6", 0],
                "fps": float(fps),
            },
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


# ---------------------------------------------------------------------------
# ComfyUI API helpers
# ---------------------------------------------------------------------------

def _upload_image(image_path: str, comfy_url: str = COMFY_URL) -> str:
    """Upload image to ComfyUI and return the server-side filename."""
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{comfy_url}/upload/image",
            files={"image": (Path(image_path).name, f, "image/png")},
            data={"overwrite": "true"},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()["name"]


def _submit_workflow(workflow: dict, comfy_url: str = COMFY_URL) -> str:
    """Submit workflow to ComfyUI queue and return prompt_id."""
    client_id = uuid.uuid4().hex
    payload = {"prompt": workflow, "client_id": client_id}
    resp = requests.post(f"{comfy_url}/prompt", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _wait_for_completion(
    prompt_id: str,
    comfy_url: str = COMFY_URL,
    timeout: int = 300,
    poll_interval: float = 2.0,
) -> dict:
    """Poll /history until the prompt completes. Returns outputs dict."""
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
        time.sleep(poll_interval)
    raise TimeoutError(f"SVD generation timed out after {timeout}s")


def _find_output_video(outputs: dict, comfy_url: str = COMFY_URL) -> str | None:
    """Find video file path from ComfyUI outputs dict."""
    for node_outputs in outputs.values():
        for key in ("gifs", "videos"):
            for item in node_outputs.get(key, []):
                filename = item.get("filename")
                subfolder = item.get("subfolder", "")
                if filename:
                    return filename, subfolder
    return None, None


def _download_video(
    filename: str,
    subfolder: str,
    dest_path: str,
    comfy_url: str = COMFY_URL,
) -> str:
    """Download generated video from ComfyUI output dir or via API."""
    # Try direct file copy first (same machine)
    src_dir = COMFY_OUTPUT_DIR / subfolder if subfolder else COMFY_OUTPUT_DIR
    src_path = src_dir / filename
    if src_path.exists():
        shutil.copy2(str(src_path), dest_path)
        return dest_path

    # Fallback: download via /view endpoint
    params = {"filename": filename, "type": "output"}
    if subfolder:
        params["subfolder"] = subfolder
    resp = requests.get(f"{comfy_url}/view", params=params, timeout=60, stream=True)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_svd_video(
    image_path: str,
    output_path: str = "/tmp/jarvis_svd_output.mp4",
    width: int = 576,
    height: int = 1024,
    frames: int = 25,
    fps: int = 6,
    motion: int = 100,
    steps: int = 20,
    comfy_url: str = COMFY_URL,
) -> str:
    """Generate an animated video from an image using SVD via ComfyUI.

    Returns the path to the generated video file.
    Raises on error.
    """
    # Prepare and resize input image
    img = Image.open(image_path).convert("RGB")
    # Resize to target dimensions preserving aspect via crop
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

    # Save resized image to temp
    tmp_img = f"/tmp/jarvis_svd_input_{uuid.uuid4().hex[:8]}.png"
    img.save(tmp_img)

    try:
        print(f"[svd] Uploading image to ComfyUI...")
        server_name = _upload_image(tmp_img, comfy_url)

        output_prefix = f"jarvis_svd_{uuid.uuid4().hex[:8]}"
        workflow = _build_svd_workflow(
            image_name=server_name,
            width=width,
            height=height,
            frames=frames,
            fps=fps,
            motion=motion,
            steps=steps,
            output_prefix=output_prefix,
        )

        print(f"[svd] Submitting SVD workflow ({frames} frames @ {fps}fps, {steps} steps)...")
        prompt_id = _submit_workflow(workflow, comfy_url)

        print(f"[svd] Generating... (prompt_id={prompt_id})")
        outputs = _wait_for_completion(prompt_id, comfy_url, timeout=300)

        filename, subfolder = _find_output_video(outputs, comfy_url)
        if not filename:
            raise RuntimeError("No video output found in ComfyUI response")

        print(f"[svd] Downloading result: {filename}")
        result = _download_video(filename, subfolder or "", output_path, comfy_url)
        print(f"[svd] Done: {result}")
        return result
    finally:
        if os.path.exists(tmp_img):
            os.remove(tmp_img)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis SVD Video Pipeline")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", default="/tmp/jarvis_svd_output.mp4", help="Output video path")
    parser.add_argument("--width", type=int, default=576, help="Width (default 576)")
    parser.add_argument("--height", type=int, default=1024, help="Height (default 1024, TikTok vertical)")
    parser.add_argument("--frames", type=int, default=25, help="Number of frames (default 25)")
    parser.add_argument("--fps", type=int, default=6, help="Frames per second (default 6)")
    parser.add_argument("--motion", type=int, default=100, help="Motion bucket 1-255 (default 100)")
    parser.add_argument("--steps", type=int, default=20, help="Sampling steps (default 20)")
    parser.add_argument("--comfy-url", default=COMFY_URL, help=f"ComfyUI URL (default {COMFY_URL})")
    args = parser.parse_args()

    result = generate_svd_video(
        image_path=args.image,
        output_path=args.output,
        width=args.width,
        height=args.height,
        frames=args.frames,
        fps=args.fps,
        motion=args.motion,
        steps=args.steps,
        comfy_url=args.comfy_url,
    )
    print(f"DONE: {result}")
