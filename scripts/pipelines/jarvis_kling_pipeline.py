"""Kling AI video generation pipeline — direct API integration.

Uses Kling's REST API at api.klingai.com with JWT authentication.
Generates video from text prompt or image, polls until complete, downloads result.

Auth: HMAC-SHA256 JWT with access key + secret key.
Docs: https://docs.qingque.cn/d/home/eZQDp4XFE-pM1mWXxmq9X8b2T (Kling API)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import base64
from pathlib import Path

# ---------------------------------------------------------------------------
# Credentials — read from env or hardcoded fallback
# ---------------------------------------------------------------------------

KLING_ACCESS_KEY = os.environ.get("KLING_ACCESS_KEY", "AYym9fFKrQ48nJrTa8krhNLbJAhfNE8M")
KLING_SECRET_KEY = os.environ.get("KLING_SECRET_KEY", "MP89dQnaELerFTnfRgPLbhYYRPEDr3Fg")

KLING_API_BASE = "https://api.klingai.com"

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _build_jwt(access_key: str, secret_key: str, exp_seconds: int = 1800) -> str:
    """Build a HS256 JWT token for Kling API auth."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": now + exp_seconds,
        "nbf": now - 5,
    }

    def _b64url(data: dict) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(data, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

    header_enc = _b64url(header)
    payload_enc = _b64url(payload)
    signing_input = f"{header_enc}.{payload_enc}"
    sig = hmac.new(
        secret_key.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    sig_enc = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{signing_input}.{sig_enc}"


def _auth_headers() -> dict:
    token = _build_jwt(KLING_ACCESS_KEY, KLING_SECRET_KEY)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Text-to-video
# ---------------------------------------------------------------------------


def generate_text_to_video(
    prompt: str,
    output_path: str,
    model: str = "kling-v1",
    duration: int = 5,
    aspect_ratio: str = "9:16",
    cfg_scale: float = 0.5,
    mode: str = "std",
    poll_interval: int = 8,
    timeout: int = 300,
) -> dict:
    """Generate a video from a text prompt via Kling API.

    Returns {"status": "success", "path": output_path} or {"status": "error", "error": ...}
    """
    import urllib.request
    import urllib.error

    try:
        url = f"{KLING_API_BASE}/v1/videos/text2video"
        body = {
            "model_name": model,
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "cfg_scale": cfg_scale,
            "mode": mode,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=_auth_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if data.get("code") != 0:
            return {"status": "error", "error": f"API error: {data}"}

        task_id = data["data"]["task_id"]
        return _poll_and_download(task_id, output_path, "text2video", poll_interval, timeout)

    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Image-to-video
# ---------------------------------------------------------------------------


def generate_image_to_video(
    image_path: str,
    output_path: str,
    prompt: str = "",
    model: str = "kling-v1",
    duration: int = 5,
    cfg_scale: float = 0.5,
    mode: str = "std",
    poll_interval: int = 8,
    timeout: int = 300,
) -> dict:
    """Generate a video from an image via Kling API.

    Returns {"status": "success", "path": output_path} or {"status": "error", "error": ...}
    """
    import urllib.request

    try:
        # Encode image as base64
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        url = f"{KLING_API_BASE}/v1/videos/image2video"
        body = {
            "model_name": model,
            "image": img_b64,
            "prompt": prompt,
            "duration": str(duration),
            "cfg_scale": cfg_scale,
            "mode": mode,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=_auth_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if data.get("code") != 0:
            return {"status": "error", "error": f"API error: {data}"}

        task_id = data["data"]["task_id"]
        return _poll_and_download(task_id, output_path, "image2video", poll_interval, timeout)

    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Polling + download
# ---------------------------------------------------------------------------


def _poll_and_download(
    task_id: str,
    output_path: str,
    endpoint: str,
    poll_interval: int,
    timeout: int,
) -> dict:
    """Poll task until complete, download video to output_path."""
    import urllib.request

    deadline = time.time() + timeout
    url = f"{KLING_API_BASE}/v1/videos/{endpoint}/{task_id}"

    while time.time() < deadline:
        req = urllib.request.Request(url, headers=_auth_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if data.get("code") != 0:
            return {"status": "error", "error": f"Poll error: {data}"}

        task_data = data["data"]
        task_status = task_data.get("task_status", "")

        if task_status == "succeed":
            videos = task_data.get("task_result", {}).get("videos", [])
            if not videos:
                return {"status": "error", "error": "No videos in result"}
            video_url = videos[0]["url"]
            return _download_video(video_url, output_path)

        if task_status in ("failed", "error"):
            msg = task_data.get("task_status_msg", "unknown error")
            return {"status": "error", "error": f"Task failed: {msg}"}

        # Still processing
        time.sleep(poll_interval)

    return {"status": "error", "error": f"Timeout after {timeout}s (task_id={task_id})"}


def _download_video(url: str, output_path: str) -> dict:
    """Download video from URL to output_path."""
    import urllib.request

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return {"status": "success", "path": output_path}
    return {"status": "error", "error": "Downloaded file is empty or missing"}


# ---------------------------------------------------------------------------
# High-level: generate TikTok video (text → video, vertical 9:16)
# ---------------------------------------------------------------------------


def generate_tiktok_video(
    prompt: str,
    output_path: str,
    duration: int = 5,
    mode: str = "std",
) -> dict:
    """Convenience wrapper: text → 9:16 vertical TikTok video."""
    return generate_text_to_video(
        prompt=prompt,
        output_path=output_path,
        model="kling-v1",
        duration=duration,
        aspect_ratio="9:16",
        mode=mode,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="Kling AI video generation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    t2v = sub.add_parser("text2video", help="Generate video from text prompt")
    t2v.add_argument("--prompt", required=True)
    t2v.add_argument("--output", required=True)
    t2v.add_argument("--duration", type=int, default=5, choices=[5, 10])
    t2v.add_argument("--mode", default="std", choices=["std", "pro"])
    t2v.add_argument("--aspect-ratio", default="9:16")

    i2v = sub.add_parser("image2video", help="Generate video from image")
    i2v.add_argument("--image", required=True)
    i2v.add_argument("--prompt", default="")
    i2v.add_argument("--output", required=True)
    i2v.add_argument("--duration", type=int, default=5, choices=[5, 10])
    i2v.add_argument("--mode", default="std", choices=["std", "pro"])

    args = parser.parse_args()

    if args.cmd == "text2video":
        result = generate_text_to_video(
            prompt=args.prompt,
            output_path=args.output,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            mode=args.mode,
        )
    else:
        result = generate_image_to_video(
            image_path=args.image,
            output_path=args.output,
            prompt=args.prompt,
            duration=args.duration,
            mode=args.mode,
        )

    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
