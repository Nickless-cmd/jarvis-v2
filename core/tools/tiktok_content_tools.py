"""TikTok content generation tool — wraps jarvis_pollinations_pipeline.

Lets Jarvis call the full pipeline as a single tool:
  pollinations.ai image → MoviePy Ken-Burns zoom → text overlay → MP4

No GPU, no ComfyUI, bounded RAM. Uses the pollinations.ai API key from
runtime.json (already wired via pollinations_tools).

The result dict contains output_path + image_path so Jarvis can
preview the image separately or use the final MP4 for TikTok upload.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _exec_tiktok_generate_video(args: dict[str, Any]) -> dict[str, Any]:
    prompt = str(args.get("prompt") or "").strip()
    text = str(args.get("text") or "").strip()
    if not prompt:
        return {"status": "error", "text": "prompt required"}
    if not text:
        return {"status": "error", "text": "text overlay required"}

    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        # Default to workspace directory so outputs are tracked
        import os, uuid
        from datetime import UTC, datetime
        base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
        out_dir = Path(base) / "workspaces/default/memory/generated/tiktok"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            out_dir = Path("/tmp")
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        output_path = str(out_dir / f"tiktok-{ts}-{uuid.uuid4().hex[:8]}.mp4")

    image_model = str(args.get("image_model") or "flux").lower().strip()
    if image_model not in ("flux", "turbo", "variation", "anime"):
        image_model = "flux"

    try:
        width = int(args.get("width") or 1024)
        height = int(args.get("height") or 1792)
        duration = float(args.get("duration") or 8.0)
        fps = int(args.get("fps") or 30)
        zoom_start = float(args.get("zoom_start") or 1.0)
        zoom_end = float(args.get("zoom_end") or 1.25)
    except Exception as exc:
        return {"status": "error", "text": f"bad numeric arg: {exc}"}

    add_tts = bool(args.get("add_tts", False))
    voice = str(args.get("voice") or "en-US-GuyNeural")
    text_position = str(args.get("text_position") or "bottom")
    if text_position not in ("top", "center", "bottom"):
        text_position = "bottom"

    seed = args.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception:
            seed = None
    enhance = bool(args.get("enhance", False))

    # Import lazily — MoviePy takes time to import
    try:
        import sys
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from scripts.pipelines.jarvis_pollinations_pipeline import run_pipeline
    except Exception as exc:
        return {"status": "error", "text": f"pipeline import failed: {exc}"}

    try:
        result = run_pipeline(
            prompt=prompt,
            text=text,
            output_path=output_path,
            image_model=image_model,
            width=width, height=height,
            duration=duration, fps=fps,
            zoom_start=zoom_start, zoom_end=zoom_end,
            add_tts=add_tts, voice=voice,
            seed=seed, enhance_prompt=enhance,
            text_position=text_position,
            keep_intermediates=False,
        )
    except Exception as exc:
        logger.warning("tiktok_generate_video failed: %s", exc)
        return {"status": "error", "text": f"pipeline failed: {exc}"}

    try:
        import os
        size_bytes = os.path.getsize(result["output_path"])
    except Exception:
        size_bytes = None

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "tiktok.video_generated",
            "payload": {
                "output_path": result["output_path"],
                "image_path": result.get("image_path"),
                "duration_s": result.get("duration_s"),
                "prompt": prompt[:120],
                "text": text[:120],
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "text": (
            f"TikTok video generated in {result.get('duration_s')}s: "
            f"{result['output_path']} ({size_bytes} bytes). "
            f"Timings: {result.get('timings')}"
        ),
        "output_path": result["output_path"],
        "image_path": result.get("image_path"),
        "duration_s": result.get("duration_s"),
        "timings": result.get("timings"),
        "size_bytes": size_bytes,
    }


TIKTOK_CONTENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tiktok_generate_video",
            "description": (
                "Generate a TikTok-ready vertical video end-to-end: flux image "
                "via pollinations.ai → Ken Burns slow-zoom via MoviePy → text "
                "overlay via PIL → MP4. No GPU, no ComfyUI, bounded RAM. "
                "Default output is 1024×1792 (9:16), 8s, 30fps. Returns path "
                "to saved MP4."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Image generation prompt (what the video should show).",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text overlay burned onto the video.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": (
                            "Optional MP4 output path. Default: "
                            "workspace/memory/generated/tiktok/tiktok-YYYYMMDD-HHMMSS-*.mp4"
                        ),
                    },
                    "image_model": {
                        "type": "string",
                        "description": "flux (default) | turbo | variation | anime",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Video width in pixels. Default 1024.",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Video height in pixels. Default 1792 (9:16).",
                    },
                    "duration": {
                        "type": "number",
                        "description": "Video length in seconds. Default 8.0.",
                    },
                    "fps": {
                        "type": "integer",
                        "description": "Frames per second. Default 30.",
                    },
                    "zoom_start": {
                        "type": "number",
                        "description": "Ken Burns zoom start factor. Default 1.0.",
                    },
                    "zoom_end": {
                        "type": "number",
                        "description": "Ken Burns zoom end factor. Default 1.25.",
                    },
                    "add_tts": {
                        "type": "boolean",
                        "description": "Add edge-tts voiceover reading the text. Default false.",
                    },
                    "voice": {
                        "type": "string",
                        "description": "edge-tts voice id. Default en-US-GuyNeural.",
                    },
                    "text_position": {
                        "type": "string",
                        "description": "top | center | bottom. Default bottom.",
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Optional image seed for reproducibility.",
                    },
                    "enhance": {
                        "type": "boolean",
                        "description": "Enable pollinations LLM prompt enhancement. Default false.",
                    },
                },
                "required": ["prompt", "text"],
            },
        },
    },
]
