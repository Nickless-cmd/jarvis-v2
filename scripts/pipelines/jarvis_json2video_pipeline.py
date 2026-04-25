"""JSON2Video pipeline — creates TikTok-style videos via json2video.com API.

Creates styled text-overlay videos with background images/colors.
600 seconds/month on free plan (with draft watermark).

API: POST https://api.json2video.com/v2/movies
Auth: x-api-key header
Docs: https://json2video.com/docs/v2/api-reference/
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

import requests

from _config import read_runtime_key

# NOTE on _post/_get_status: we use `requests` rather than urllib because
# urllib normalizes header keys (`x-api-key` → `X-api-key`), which json2video's
# parser does not match. The endpoint silently rejects the request with
# "API Key not available" — looks like a bad key, but is actually our HTTP
# client mangling the header. requests preserves case verbatim.

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

J2V_BASE = "https://api.json2video.com/v2"


def _headers() -> dict[str, str]:
    return {
        "x-api-key": read_runtime_key("json2video_key", env_override="JSON2VIDEO_KEY"),
        "Content-Type": "application/json",
    }

# Slot background colors (hex)
_SLOT_BG = {
    "morning": "#1a0a00",
    "midday":  "#080810",
    "evening": "#020008",
}

# Slot text colors
_SLOT_TEXT_COLOR = {
    "morning": "#FFD700",
    "midday":  "#C0C0C0",
    "evening": "#B0C4DE",
}


# ---------------------------------------------------------------------------
# Core API helpers
# ---------------------------------------------------------------------------


def _post(body: dict) -> dict:
    resp = requests.post(
        f"{J2V_BASE}/movies",
        headers=_headers(),
        data=json.dumps(body),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _get_status(project_id: str) -> dict:
    resp = requests.get(
        f"{J2V_BASE}/movies",
        headers=_headers(),
        params={"project": project_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _download(url: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)


# ---------------------------------------------------------------------------
# Build movie payload
# ---------------------------------------------------------------------------


def _build_movie(
    text: str,
    bg_color: str = "#0a051e",
    text_color: str = "#FFFFFF",
    bg_image_url: str | None = None,
    duration: int = 10,
    draft: bool = True,
) -> dict:
    """Build a json2video movie payload for a TikTok text-overlay video."""
    elements = []

    # Background: image element only when an actual URL is supplied.
    # json2video v2 rejects data:image/svg+xml URIs, so for solid-color
    # backgrounds we rely on the scene's `background-color` property below.
    if bg_image_url:
        elements.append({
            "type": "image",
            "src": bg_image_url,
            "resize": "cover",
            "duration": duration,
            "z-index": -1,
        })

    # Text overlay — centered, large, styled.
    # json2video v2 schema notes:
    # - x/y must be integer pixels; use `position` for keyword placement
    # - width is integer pixels (918 ≈ 85% of 1080-wide canvas)
    # - styling goes in `settings` (CSS-like), not legacy `style: "00X"` ids
    elements.append({
        "type": "text",
        "text": text,
        "position": "center-center",
        "width": 918,
        "duration": duration,
        "z-index": 1,
        "settings": {
            "font-family": "Roboto",
            "font-size": "72px",
            "font-weight": "700",
            "color": text_color,
            "text-align": "center",
        },
    })

    # Fade in/out on text
    elements[-1]["fade-in"] = 0.5
    elements[-1]["fade-out"] = 0.5

    return {
        "draft": draft,
        "resolution": "instagram-story",  # 1080x1920 = 9:16
        "quality": "high",
        "scenes": [
            {
                "duration": duration,
                "background-color": bg_color,
                "elements": elements,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_tiktok_video(
    text: str,
    output_path: str,
    slot: str = "morning",
    bg_image_url: str | None = None,
    duration: int = 10,
    draft: bool = True,
    poll_interval: int = 5,
    timeout: int = 180,
) -> dict:
    """Generate a TikTok text-overlay video via json2video.

    Returns {"status": "success", "path": output_path} or {"status": "error", "error": ...}
    """
    try:
        bg_color = _SLOT_BG.get(slot, "#0a051e")
        text_color = _SLOT_TEXT_COLOR.get(slot, "#FFFFFF")

        movie = _build_movie(
            text=text,
            bg_color=bg_color,
            text_color=text_color,
            bg_image_url=bg_image_url,
            duration=duration,
            draft=draft,
        )

        resp = _post(movie)
        if not resp.get("success", True) is False:
            # Check for project id
            project_id = resp.get("project") or resp.get("id") or resp.get("movie", {}).get("project")
            if not project_id:
                # Maybe success with project in response
                if "project" in resp:
                    project_id = resp["project"]
                else:
                    return {"status": "error", "error": f"No project ID in response: {resp}"}
        else:
            return {"status": "error", "error": resp.get("message", str(resp))}

        # Poll for completion
        deadline = time.time() + timeout
        while time.time() < deadline:
            status_resp = _get_status(project_id)
            movie_data = status_resp.get("movie") or {}
            status = movie_data.get("status", "")

            if status == "done":
                url = movie_data.get("url") or movie_data.get("download_url")
                if not url:
                    return {"status": "error", "error": "No download URL in completed movie"}
                _download(url, output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return {"status": "success", "path": output_path, "project": project_id}
                return {"status": "error", "error": "Downloaded file empty"}

            if status in ("error", "failed"):
                return {"status": "error", "error": f"Render failed: {movie_data.get('message', status)}"}

            time.sleep(poll_interval)

        return {"status": "error", "error": f"Timeout after {timeout}s (project={project_id})"}

    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return {"status": "error", "error": f"HTTP {exc.code}: {body}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="json2video TikTok video generator")
    parser.add_argument("--text", required=True, help="Text to display")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--slot", default="morning", choices=["morning", "midday", "evening"])
    parser.add_argument("--bg-image", default=None, help="Background image URL")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--no-draft", action="store_true", help="Disable watermark (requires paid plan)")
    args = parser.parse_args()

    result = generate_tiktok_video(
        text=args.text,
        output_path=args.output,
        slot=args.slot,
        bg_image_url=args.bg_image,
        duration=args.duration,
        draft=not args.no_draft,
    )
    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
