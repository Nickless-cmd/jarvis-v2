"""PiAPI.ai video generation pipeline — Kling AI via PiAPI proxy.

PiAPI provides access to Kling AI video generation without needing a direct
Kling account. Uses PiAPI's unified task API.

API: POST /api/v1/task  →  GET /api/v1/task/{id}
Auth: X-API-Key header
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PIAPI_KEY = os.environ.get("PIAPI_KEY", "85703ebb2f404ee998befa9a9759b51693ac1c5c6f0c48e67e43d968394eec85")
PIAPI_BASE = "https://api.piapi.ai"

_HEADERS = {
    "X-API-Key": PIAPI_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _post(endpoint: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{PIAPI_BASE}{endpoint}",
        data=json.dumps(body).encode(),
        headers=_HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get(endpoint: str) -> dict:
    req = urllib.request.Request(
        f"{PIAPI_BASE}{endpoint}",
        headers=_HEADERS,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _download(url: str, output_path: str) -> None:
    """Download a file from url to output_path."""
    req = urllib.request.Request(url, headers={"User-Agent": _HEADERS["User-Agent"]})
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())


# ---------------------------------------------------------------------------
# Task submission + polling
# ---------------------------------------------------------------------------


def _submit_task(body: dict) -> str:
    """Submit a task. Returns task_id or raises on error."""
    resp = _post("/api/v1/task", body)
    if resp.get("code") != 200:
        raise RuntimeError(f"Task submission failed: {resp}")
    task_id = resp["data"]["task_id"]
    if not task_id:
        raise RuntimeError(f"No task_id in response: {resp}")
    return task_id


def _poll_task(task_id: str, poll_interval: int = 8, timeout: int = 360) -> dict:
    """Poll until task is completed/failed. Returns final data dict."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = _get(f"/api/v1/task/{task_id}")
        if resp.get("code") != 200:
            raise RuntimeError(f"Poll error: {resp}")
        data = resp["data"]
        status = data.get("status", "")
        if status == "completed":
            return data
        if status == "failed":
            err = data.get("error", {})
            raise RuntimeError(f"Task failed: {err.get('message') or err}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Task {task_id} timed out after {timeout}s")


def _extract_video_url(data: dict) -> str:
    """Extract watermark-free video URL from completed task data.

    Priority:
    1. output.video_url (top-level, always watermark-free via storage.theapi.app)
    2. works[*].video.resource_without_watermark
    3. works[*].video.resource (may have watermark)
    """
    output = data.get("output", {})

    # Best: top-level video_url (set by PiAPI, always watermark-free)
    if output.get("video_url"):
        return output["video_url"]

    # Fallback: walk works array
    for work in (output.get("works") or []):
        if not isinstance(work, dict):
            continue
        video = work.get("video", {})
        url = video.get("resource_without_watermark") or video.get("resource")
        if url:
            return url

    raise RuntimeError(f"No video URL in output: {output}")


# ---------------------------------------------------------------------------
# Text-to-video
# ---------------------------------------------------------------------------


def generate_text_to_video(
    prompt: str,
    output_path: str,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    mode: str = "std",
    poll_interval: int = 8,
    timeout: int = 360,
) -> dict:
    """Generate video from text prompt via PiAPI Kling.

    Returns {"status": "success", "path": output_path} or {"status": "error", "error": ...}
    """
    try:
        task_id = _submit_task({
            "model": "kling",
            "task_type": "video_generation",
            "input": {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "mode": mode,
            },
        })
        data = _poll_task(task_id, poll_interval, timeout)
        video_url = _extract_video_url(data)
        _download(video_url, output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return {"status": "success", "path": output_path, "task_id": task_id}
        return {"status": "error", "error": "Downloaded file empty"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Image-to-video
# ---------------------------------------------------------------------------


def generate_image_to_video(
    image_path: str,
    output_path: str,
    prompt: str = "",
    duration: int = 5,
    mode: str = "std",
    poll_interval: int = 8,
    timeout: int = 360,
) -> dict:
    """Generate video from an image via PiAPI Kling.

    Returns {"status": "success", "path": output_path} or {"status": "error", "error": ...}
    """
    import base64

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        task_id = _submit_task({
            "model": "kling",
            "task_type": "video_generation",
            "input": {
                "image": img_b64,
                "prompt": prompt,
                "duration": duration,
                "mode": mode,
            },
        })
        data = _poll_task(task_id, poll_interval, timeout)
        video_url = _extract_video_url(data)
        _download(video_url, output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return {"status": "success", "path": output_path, "task_id": task_id}
        return {"status": "error", "error": "Downloaded file empty"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Convenience: TikTok vertical video
# ---------------------------------------------------------------------------


def generate_tiktok_video(
    prompt: str,
    output_path: str,
    duration: int = 5,
    mode: str = "std",
) -> dict:
    """Text → 9:16 TikTok video via PiAPI Kling."""
    return generate_text_to_video(
        prompt=prompt,
        output_path=output_path,
        duration=duration,
        aspect_ratio="9:16",
        mode=mode,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="PiAPI Kling video generation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    t2v = sub.add_parser("text2video")
    t2v.add_argument("--prompt", required=True)
    t2v.add_argument("--output", required=True)
    t2v.add_argument("--duration", type=int, default=5, choices=[5, 10])
    t2v.add_argument("--mode", default="std", choices=["std", "pro"])
    t2v.add_argument("--aspect-ratio", default="9:16")

    i2v = sub.add_parser("image2video")
    i2v.add_argument("--image", required=True)
    i2v.add_argument("--prompt", default="")
    i2v.add_argument("--output", required=True)
    i2v.add_argument("--duration", type=int, default=5, choices=[5, 10])
    i2v.add_argument("--mode", default="std", choices=["std", "pro"])

    poll_sub = sub.add_parser("poll", help="Poll existing task by ID")
    poll_sub.add_argument("task_id")
    poll_sub.add_argument("--output", help="Download video to this path if completed")

    args = parser.parse_args()

    if args.cmd == "text2video":
        result = generate_text_to_video(
            prompt=args.prompt,
            output_path=args.output,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            mode=args.mode,
        )
    elif args.cmd == "image2video":
        result = generate_image_to_video(
            image_path=args.image,
            output_path=args.output,
            prompt=args.prompt,
            duration=args.duration,
            mode=args.mode,
        )
    elif args.cmd == "poll":
        try:
            data = _poll_task(args.task_id, timeout=5)
            result = {"status": "completed", "data": data}
            if args.output:
                url = _extract_video_url(data)
                _download(url, args.output)
                result["path"] = args.output
        except Exception as e:
            # Just show current state
            resp = _get(f"/api/v1/task/{args.task_id}")
            result = resp.get("data", {})

    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and result.get("status") not in ("success", "completed"):
        if "error" in result:
            raise SystemExit(1)


if __name__ == "__main__":
    _cli()
