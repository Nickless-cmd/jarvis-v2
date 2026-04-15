"""TikTok auto-uploader integration tools for Jarvis.

Wraps the TiktokAutoUploader CLI at /tmp/TiktokAutoUploader for native
tool access. Supports login, upload, and listing users/videos.

Tools:
  tiktok_upload — upload a video to TikTok
  tiktok_login  — open browser to capture TikTok session cookies
  tiktok_show   — list available cookie profiles or videos
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

TIKTOK_PROJECT_DIR = "/tmp/TiktokAutoUploader"
CLI_PATH = os.path.join(TIKTOK_PROJECT_DIR, "cli.py")
CONDA_PYTHON = "/opt/conda/envs/ai/bin/python"
_TIMEOUT_SECONDS = 120  # uploads can take a while


def _run_cli(*args: str, timeout: int = _TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run a TikTok CLI command and return structured result."""
    cmd = [CONDA_PYTHON, CLI_PATH, *args]

    # Inherit env and ensure DISPLAY is set for browser-based operations (login/upload)
    env = os.environ.copy()
    if not env.get("DISPLAY"):
        # Auto-detect X display from /tmp/.X11-unix
        x11_dir = "/tmp/.X11-unix"
        if os.path.isdir(x11_dir):
            sockets = [f for f in os.listdir(x11_dir) if f.startswith("X")]
            if sockets:
                display_num = sockets[0][1:]  # X1 -> 1
                env["DISPLAY"] = f":{display_num}"
                logger.info(f"Auto-detected DISPLAY=:{display_num} from X11 socket")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=TIKTOK_PROJECT_DIR,
            env=env,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            combined = (output + "\n" + error).strip() if output else error
            return {"status": "error", "error": combined or f"Exit code {result.returncode}"}
        return {
            "status": "ok",
            "output": output or "[no output]",
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError as exc:
        return {"status": "error", "error": f"CLI not found: {exc}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Executor functions
# ---------------------------------------------------------------------------

def _exec_tiktok_upload(args: dict[str, Any]) -> dict[str, Any]:
    """Upload a video to TikTok.

    Args:
        user: Cookie profile name (from tiktok_login).
        video: Video filename (relative to VideosDirPath) or absolute path.
        title: Video title/caption (max 2200 chars, supports #hashtags and @mentions).
        schedule: Schedule time in seconds from now (0 = immediate, 900–864000).
        allow_comment: 1 = allow comments (default), 0 = disable.
        allow_duet: 1 = allow duets (default 0), 0 = disable.
        allow_stitch: 1 = allow stitch (default 0), 0 = disable.
        visibility: 0 = public (default), 1 = private.
        proxy: Optional proxy URL.
    """
    user = args.get("user", "")
    video = args.get("video", "")
    title = args.get("title", "")
    schedule = args.get("schedule", 0)
    allow_comment = args.get("allow_comment", 1)
    allow_duet = args.get("allow_duet", 0)
    allow_stitch = args.get("allow_stitch", 0)
    visibility = args.get("visibility", 0)
    proxy = args.get("proxy", "")

    if not user:
        return {"status": "error", "error": "user (cookie profile name) is required"}
    if not video:
        return {"status": "error", "error": "video path is required"}
    if not title:
        return {"status": "error", "error": "title is required"}

    cli_args = [
        "upload",
        "-u", str(user),
        "-v", str(video),
        "-t", str(title),
        "-ct", str(allow_comment),
        "-d", str(allow_duet),
        "-st", str(allow_stitch),
        "-vi", str(visibility),
    ]

    if schedule and int(schedule) > 0:
        cli_args.extend(["-sc", str(schedule)])
    if proxy:
        cli_args.extend(["-p", str(proxy)])

    result = _run_cli(*cli_args, timeout=_TIMEOUT_SECONDS)

    # Parse output for success/failure indicators
    if result["status"] == "ok":
        output = result.get("output", "")
        if "Published successfully" in output:
            result["published"] = True
        elif "Could not upload" in output or "failed" in output.lower():
            result["published"] = False
        else:
            result["published"] = None  # unclear

    return result


def _exec_tiktok_login(args: dict[str, Any]) -> dict[str, Any]:
    """Open a browser to log into TikTok and save session cookies.

    This opens an interactive Chrome browser window — the user must
    manually log in. Once logged in, the session cookies are saved
    under the given profile name for future uploads.

    Args:
        name: Profile name to save cookies under (required).
    """
    name = args.get("name", "")
    if not name:
        return {"status": "error", "error": "name (profile name) is required"}

    return _run_cli("login", "-n", str(name), timeout=180)


def _exec_tiktok_show(args: dict[str, Any]) -> dict[str, Any]:
    """List available TikTok cookie profiles or video files.

    Args:
        show_users: If true, list saved cookie profiles.
        show_videos: If true, list available video files.
    """
    show_users = args.get("show_users", False)
    show_videos = args.get("show_videos", False)

    if not show_users and not show_videos:
        # Default: show both
        show_users = True
        show_videos = True

    cli_args = ["show"]
    if show_users:
        cli_args.append("-u")
    if show_videos:
        cli_args.append("-v")

    result = _run_cli(*cli_args, timeout=15)
    return result


# ---------------------------------------------------------------------------
# Tool definitions (Ollama-compatible JSON schemas)
# ---------------------------------------------------------------------------

TIKTOK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tiktok_upload",
            "description": (
                "Upload a video to TikTok using saved session cookies. "
                "The video must be in the TikTok uploader's VideosDirPath or an absolute path. "
                "Supports scheduling, privacy settings, hashtags, and @mentions in the title."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "Cookie profile name (from tiktok_login).",
                    },
                    "video": {
                        "type": "string",
                        "description": "Video filename (relative to VideosDirPath) or absolute path.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Video title/caption. Supports #hashtags and @mentions. Max 2200 chars.",
                    },
                    "schedule": {
                        "type": "integer",
                        "description": "Schedule time in seconds from now. 0 = immediate. Range: 900-864000 if set.",
                    },
                    "allow_comment": {
                        "type": "integer",
                        "description": "1 = allow comments (default), 0 = disable.",
                    },
                    "allow_duet": {
                        "type": "integer",
                        "description": "1 = allow duets, 0 = disable (default).",
                    },
                    "allow_stitch": {
                        "type": "integer",
                        "description": "1 = allow stitch, 0 = disable (default).",
                    },
                    "visibility": {
                        "type": "integer",
                        "description": "0 = public (default), 1 = private.",
                    },
                    "proxy": {
                        "type": "string",
                        "description": "Optional proxy URL (e.g. 'http://proxy:8080').",
                    },
                },
                "required": ["user", "video", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tiktok_login",
            "description": (
                "Open a Chrome browser to log into TikTok and save session cookies. "
                "The user must manually complete login in the browser window. "
                "Cookies are saved under the given profile name for future uploads."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Profile name to save cookies under (e.g. 'myaccount').",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tiktok_show",
            "description": (
                "List available TikTok cookie profiles or video files ready for upload. "
                "Call without arguments to see both users and videos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "show_users": {
                        "type": "boolean",
                        "description": "List saved cookie profiles (default true if nothing specified).",
                    },
                    "show_videos": {
                        "type": "boolean",
                        "description": "List available video files (default true if nothing specified).",
                    },
                },
            },
        },
    },
]