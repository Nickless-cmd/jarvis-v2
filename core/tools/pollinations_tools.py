"""Pollinations.ai tools — free, no-auth image + video generation.

Pollinations is a URL-based gen-AI API: a GET request returns an image or
video bytes. No key, no account, no RAM footprint on SRVLAB — all heavy
compute happens on their end. Perfect for the TikTok content pipeline
where ComfyUI was eating local memory.

Endpoints used:
- https://image.pollinations.ai/prompt/{URL-encoded prompt}
  Optional query params: width, height, model, seed, nologo, enhance
  Models: flux, turbo (fastest), variation, anime
- https://text.pollinations.ai/{URL-encoded prompt}
  (Text only — we skip it; Jarvis has better text lanes)

Video: Pollinations' video path is still beta / not URL-GET-shaped in
public docs. We expose a placeholder that errors cleanly so Jarvis can
try it but not silently fail.

All images are saved into the workspace under
~/.jarvis-v2/workspaces/default/memory/generated/ with a short metadata
JSON sidecar.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_IMAGE_ENDPOINT = "https://image.pollinations.ai/prompt"
_GENERATED_REL = "workspaces/default/memory/generated"
_DEFAULT_MODEL = "flux"  # Options: flux, turbo, variation, anime
_ALLOWED_MODELS = ("flux", "turbo", "variation", "anime")
_DEFAULT_WIDTH = 1024
_DEFAULT_HEIGHT = 1024
_MAX_WIDTH = 2048
_MAX_HEIGHT = 2048
_REQUEST_TIMEOUT = 120
_USER_AGENT = "Jarvis-v2/pollinations-tool"


def _generated_dir() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _GENERATED_REL


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _safe_filename(prompt: str, gen_id: str, ext: str) -> str:
    # Slug the prompt into a short filename token
    import re
    slug = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", prompt.strip())[:60]
    slug = re.sub(r"-+", "-", slug).strip("-") or "image"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slug}-{gen_id[-6:]}{ext}"


def _write_sidecar(image_path: Path, metadata: dict[str, Any]) -> None:
    try:
        sidecar = image_path.with_suffix(image_path.suffix + ".json")
        with sidecar.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.debug("pollinations_tools: sidecar write failed: %s", exc)


def generate_image(
    *,
    prompt: str,
    model: str = _DEFAULT_MODEL,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    seed: int | None = None,
    nologo: bool = True,
    enhance: bool = False,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """Fetch an image from Pollinations and save to disk. Returns result dict."""
    if not prompt or not str(prompt).strip():
        return {"status": "error", "text": "prompt is empty"}

    if model not in _ALLOWED_MODELS:
        model = _DEFAULT_MODEL

    width = _clamp(width, 256, _MAX_WIDTH)
    height = _clamp(height, 256, _MAX_HEIGHT)

    encoded = urllib.parse.quote(prompt.strip(), safe="")
    params: dict[str, str] = {
        "model": model,
        "width": str(width),
        "height": str(height),
    }
    if seed is not None:
        params["seed"] = str(int(seed))
    if nologo:
        params["nologo"] = "true"
    if enhance:
        params["enhance"] = "true"
    qs = urllib.parse.urlencode(params)
    url = f"{_IMAGE_ENDPOINT}/{encoded}?{qs}"

    gen_id = f"gen-{uuid4().hex[:12]}"
    target_dir = save_dir or _generated_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            data = resp.read()
    except Exception as exc:
        return {"status": "error", "text": f"fetch failed: {exc}", "url": url}

    # Determine extension from content-type
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"

    filename = _safe_filename(prompt, gen_id, ext)
    path = target_dir / filename
    try:
        path.write_bytes(data)
    except Exception as exc:
        return {"status": "error", "text": f"write failed: {exc}"}

    metadata = {
        "generation_id": gen_id,
        "prompt": prompt,
        "model": model,
        "width": width,
        "height": height,
        "seed": seed,
        "enhance": enhance,
        "nologo": nologo,
        "url": url,
        "content_type": content_type,
        "bytes": len(data),
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "pollinations.ai",
    }
    _write_sidecar(path, metadata)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "pollinations.image_generated",
            "payload": {
                "generation_id": gen_id,
                "model": model,
                "path": str(path),
                "bytes": len(data),
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "generation_id": gen_id,
        "path": str(path),
        "bytes": len(data),
        "content_type": content_type,
        "model": model,
        "width": width,
        "height": height,
    }


# ---------------------------------------------------------------------------
# Tool executors (Ollama-compatible)
# ---------------------------------------------------------------------------


def _exec_pollinations_image(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}

    model = str(args.get("model") or _DEFAULT_MODEL).lower().strip()
    try:
        width = int(args.get("width") or _DEFAULT_WIDTH)
    except Exception:
        width = _DEFAULT_WIDTH
    try:
        height = int(args.get("height") or _DEFAULT_HEIGHT)
    except Exception:
        height = _DEFAULT_HEIGHT
    seed = args.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception:
            seed = None
    nologo = bool(args.get("nologo", True))
    enhance = bool(args.get("enhance", False))

    result = generate_image(
        prompt=prompt, model=model, width=width, height=height,
        seed=seed, nologo=nologo, enhance=enhance,
    )
    if result.get("status") == "ok":
        return {
            "status": "ok",
            "text": (
                f"Image generated ({result['bytes']} bytes, {result['content_type']}) "
                f"saved to {result['path']}"
            ),
            **result,
        }
    return result


def _exec_pollinations_video(args: dict[str, Any]) -> dict[str, Any]:
    """Video generation stub — Pollinations' public video API is not yet
    a simple GET-URL contract. Return clean error so Jarvis knows to use
    another path (e.g. fal.ai) for video."""
    return {
        "status": "error",
        "text": (
            "Pollinations video API is not available via simple URL-GET yet. "
            "Use fal.ai or another provider for text-to-video until Pollinations "
            "publishes a stable REST endpoint."
        ),
    }


POLLINATIONS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "pollinations_image",
            "description": (
                "Generate a free image via pollinations.ai (no API key, no RAM cost). "
                "Ideal for TikTok content when ComfyUI is too heavy. Returns saved "
                "image path. Models: flux (default, best quality), turbo (fastest), "
                "variation, anime."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the image.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model: flux | turbo | variation | anime. Default: flux.",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width in pixels (256-2048). Default 1024.",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height in pixels (256-2048). Default 1024.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility.",
                    },
                    "nologo": {
                        "type": "boolean",
                        "description": "Remove pollinations watermark. Default true.",
                    },
                    "enhance": {
                        "type": "boolean",
                        "description": "Enable LLM prompt enhancement. Default false.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pollinations_video",
            "description": (
                "Placeholder for pollinations.ai video generation. Currently not "
                "available via simple URL-GET; use fal.ai or similar for video. "
                "Call this only to confirm it's not yet implemented."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt for the video.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
]
