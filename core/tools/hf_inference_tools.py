"""Hugging Face Inference API tools — free-tier text-to-video + fallback image gen.

HF's serverless inference API gives free access (rate-limited, ~200-500
requests/hour on free tier) to warm text-to-video models including:
- Lightricks/LTX-Video — fast, good motion adherence
- Lightricks/LTX-Video-0.9.8-13B-distilled — fastest distilled variant
- tencent/HunyuanVideo — highest quality, slower

Auth: requires huggingface_token in runtime.json. Never hardcoded.

This complements pollinations_tools.py:
- Use pollinations_image for free unlimited images (no auth needed for
  basic, faster with auth)
- Use hf_text_to_video for genuinely-free video generation (rate-limited)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_HF_BASE = "https://router.huggingface.co/hf-inference/models"
_VIDEO_REL = "workspaces/default/memory/generated/video"
_DEFAULT_VIDEO_MODEL = "Lightricks/LTX-Video-0.9.8-13B-distilled"
_ALLOWED_VIDEO_MODELS = (
    "Lightricks/LTX-Video-0.9.8-13B-distilled",
    "Lightricks/LTX-Video",
    "tencent/HunyuanVideo",
)
_REQUEST_TIMEOUT = 600  # inference can queue on free tier
_USER_AGENT = "Jarvis-v2/hf-inference"


def _hf_token() -> str | None:
    """Read HF token from runtime.json (never hardcoded)."""
    try:
        from core.runtime.secrets import read_runtime_key
        key = read_runtime_key("huggingface_token")
        if key:
            return str(key)
    except Exception:
        pass
    return None


def _auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/json",
    }
    token = _hf_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _video_dir() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _VIDEO_REL


def _safe_filename(prompt: str, gen_id: str, ext: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", prompt.strip())[:60]
    slug = re.sub(r"-+", "-", slug).strip("-") or "video"
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slug}-{gen_id[-6:]}{ext}"


def _write_sidecar(path: Path, metadata: dict[str, Any]) -> None:
    try:
        sidecar = path.with_suffix(path.suffix + ".json")
        with sidecar.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.debug("hf_inference_tools: sidecar write failed: %s", exc)


def generate_video(
    *,
    prompt: str,
    model: str = _DEFAULT_VIDEO_MODEL,
    num_frames: int | None = None,
    guidance_scale: float | None = None,
    negative_prompt: str | None = None,
    num_inference_steps: int | None = None,
    seed: int | None = None,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate a video via HF serverless inference API."""
    if not prompt or not str(prompt).strip():
        return {"status": "error", "text": "prompt is empty"}
    if not _hf_token():
        return {
            "status": "error",
            "text": "huggingface_token missing from runtime.json",
        }
    if model not in _ALLOWED_VIDEO_MODELS:
        model = _DEFAULT_VIDEO_MODEL

    parameters: dict[str, Any] = {}
    if num_frames is not None:
        parameters["num_frames"] = int(num_frames)
    if guidance_scale is not None:
        parameters["guidance_scale"] = float(guidance_scale)
    if negative_prompt:
        parameters["negative_prompt"] = [str(negative_prompt)]
    if num_inference_steps is not None:
        parameters["num_inference_steps"] = int(num_inference_steps)
    if seed is not None:
        parameters["seed"] = int(seed)

    payload: dict[str, Any] = {"inputs": prompt.strip()}
    if parameters:
        payload["parameters"] = parameters

    url = f"{_HF_BASE}/{model}"
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=_auth_headers(), method="POST")
    gen_id = f"hfvid-{uuid4().hex[:12]}"
    target_dir = save_dir or _video_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "text": f"could not create dir: {exc}"}

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "video/mp4")
            data = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {
            "status": "error",
            "text": f"HF HTTP {exc.code}: {err_body}",
            "url": url,
        }
    except Exception as exc:
        return {"status": "error", "text": f"HF fetch failed: {exc}", "url": url}

    if not data or len(data) < 1024:
        return {
            "status": "error",
            "text": f"response too small ({len(data)} bytes)",
            "content_type": content_type,
        }

    # Infer extension
    ext = ".mp4"
    if "webm" in content_type:
        ext = ".webm"
    elif "image" in content_type:
        ext = ".gif"  # some text-to-video models return animated GIF

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
        "parameters": parameters,
        "url": url,
        "content_type": content_type,
        "bytes": len(data),
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "huggingface",
        "kind": "video",
    }
    _write_sidecar(path, metadata)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "hf_inference.video_generated",
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
    }


def _exec_hf_text_to_video(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    model = str(args.get("model") or _DEFAULT_VIDEO_MODEL).strip()
    num_frames = args.get("num_frames")
    if num_frames is not None:
        try:
            num_frames = int(num_frames)
        except Exception:
            num_frames = None
    guidance_scale = args.get("guidance_scale")
    if guidance_scale is not None:
        try:
            guidance_scale = float(guidance_scale)
        except Exception:
            guidance_scale = None
    negative = args.get("negative_prompt")
    steps = args.get("num_inference_steps")
    if steps is not None:
        try:
            steps = int(steps)
        except Exception:
            steps = None
    seed = args.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception:
            seed = None

    result = generate_video(
        prompt=prompt,
        model=model,
        num_frames=num_frames,
        guidance_scale=guidance_scale,
        negative_prompt=str(negative) if negative else None,
        num_inference_steps=steps,
        seed=seed,
    )
    if result.get("status") == "ok":
        return {
            "status": "ok",
            "text": (
                f"HF video generated ({result['bytes']} bytes, {result['content_type']}, "
                f"model={result['model']}) saved to {result['path']}"
            ),
            **result,
        }
    return result


HF_INFERENCE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "hf_text_to_video",
            "description": (
                "Generate a video from a text prompt via Hugging Face serverless "
                "inference API. Genuinely free (rate-limited on free tier). "
                "Models: Lightricks/LTX-Video-0.9.8-13B-distilled (default, fast) | "
                "Lightricks/LTX-Video (higher quality) | tencent/HunyuanVideo (best, slowest). "
                "Returns saved MP4 path."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt describing the video.",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "Lightricks/LTX-Video-0.9.8-13B-distilled (default) | "
                            "Lightricks/LTX-Video | tencent/HunyuanVideo"
                        ),
                    },
                    "num_frames": {
                        "type": "integer",
                        "description": "Number of frames to generate. Model-dependent.",
                    },
                    "guidance_scale": {
                        "type": "number",
                        "description": "Prompt adherence strength. Typical 3-9.",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What to avoid in the video.",
                    },
                    "num_inference_steps": {
                        "type": "integer",
                        "description": "Denoising steps. Higher = better quality, slower.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional seed for reproducibility.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
]
