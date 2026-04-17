"""TikTok auto-uploader integration tools for Jarvis.

Uses the tiktokautouploader pip package (installed in conda 'ai' env).
Cookies are stored permanently at TIKTOK_DIR/TK_cookies_{accountname}.json.
Upload runs in a subprocess so cwd changes are isolated.

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
import textwrap
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Permanent home for cookies and videos — survives reboots
TIKTOK_DIR = Path("/home/bs/.jarvis-v2/tiktok")
TIKTOK_DIR.mkdir(parents=True, exist_ok=True)

CONDA_PYTHON = "/opt/conda/envs/ai/bin/python"
_UPLOAD_TIMEOUT = 180
_LOGIN_TIMEOUT = 300


# ---------------------------------------------------------------------------
# Executor functions
# ---------------------------------------------------------------------------

def _exec_tiktok_upload(args: dict[str, Any]) -> dict[str, Any]:
    """Upload a video to TikTok using tiktokautouploader.

    Args:
        user: Account name (must have TK_cookies_{user}.json in TIKTOK_DIR).
        video: Absolute path to the video file.
        title: Caption / description (supports #hashtags).
        schedule: Optional "HH:MM" string for scheduling.
        headless: bool, default True.
    """
    user = str(args.get("user") or "").strip()
    video = str(args.get("video") or "").strip()
    title = str(args.get("title") or "").strip()
    schedule = args.get("schedule") or None
    headless = bool(args.get("headless", True))

    if not user:
        return {"status": "error", "error": "user (account name) is required"}
    if not video:
        return {"status": "error", "error": "video path is required"}
    if not title:
        return {"status": "error", "error": "title is required"}
    if not os.path.isfile(video):
        return {"status": "error", "error": f"video file not found: {video}"}

    cookie_file = TIKTOK_DIR / f"TK_cookies_{user}.json"
    if not cookie_file.exists():
        return {
            "status": "error",
            "error": (
                f"No cookie file found for account '{user}'. "
                f"Run tiktok_login first or place TK_cookies_{user}.json in {TIKTOK_DIR}"
            ),
        }

    # Build inline Python to run upload_tiktok() with TIKTOK_DIR as cwd
    schedule_arg = f'"{schedule}"' if schedule else "None"
    script = textwrap.dedent(f"""
        import os, sys
        os.chdir({str(TIKTOK_DIR)!r})
        from tiktokautouploader import upload_tiktok
        result = upload_tiktok(
            video={video!r},
            description={title!r},
            accountname={user!r},
            schedule={schedule_arg},
            headless={headless!r},
            suppressprint=False,
        )
        print("UPLOAD_RESULT:", result)
    """)

    try:
        proc = subprocess.run(
            [CONDA_PYTHON, "-c", script],
            capture_output=True,
            text=True,
            timeout=_UPLOAD_TIMEOUT,
            env={**os.environ, "DISPLAY": _get_display()},
        )
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            return {"status": "error", "error": output or f"Exit {proc.returncode}"}
        published = "Published successfully" in output or "UPLOAD_RESULT: True" in output
        failed = "Could not upload" in output or "ERROR" in output.upper()
        return {
            "status": "ok",
            "output": output,
            "published": True if published else (False if failed else None),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Upload timed out after {_UPLOAD_TIMEOUT}s"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_tiktok_login(args: dict[str, Any]) -> dict[str, Any]:
    """Log into TikTok via headless browser using username + password.

    Uses 'tiktok-auth' (from tiktok_uploader package) to capture session
    cookies and converts them to the TK_cookies_{name}.json format that
    tiktokautouploader expects.

    Args:
        name: Profile name / account name to save under.
        username: TikTok email or username.
        password: TikTok password.
    """
    name = str(args.get("name") or "").strip()
    username = str(args.get("username") or "").strip()
    password = str(args.get("password") or "").strip()

    if not name:
        return {"status": "error", "error": "name (account name) is required"}
    if not username or not password:
        return {
            "status": "error",
            "error": "username and password are required for headless login",
        }

    # tiktok-auth saves cookies in playwright format to --output dir.
    # We then convert to TK_cookies_{name}.json format.
    auth_out = TIKTOK_DIR / "auth_tmp"
    auth_out.mkdir(exist_ok=True)

    tiktok_auth_bin = "/opt/conda/envs/ai/bin/tiktok-auth"
    try:
        proc = subprocess.run(
            [
                tiktok_auth_bin,
                "-u", username,
                "-p", password,
                "-o", str(auth_out),
            ],
            capture_output=True,
            text=True,
            timeout=_LOGIN_TIMEOUT,
            env={**os.environ, "DISPLAY": _get_display()},
        )
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            return {"status": "error", "error": output or f"Exit {proc.returncode}"}

        # Look for any .json cookie file saved by tiktok-auth
        cookie_files = list(auth_out.glob("*.json"))
        if not cookie_files:
            return {"status": "error", "error": f"Login ran but no cookie file found.\n{output}"}

        # Convert playwright cookies → TK_cookies format (same structure, just rename/move)
        dest = TIKTOK_DIR / f"TK_cookies_{name}.json"
        cookie_data = json.loads(cookie_files[0].read_text())
        dest.write_text(json.dumps(cookie_data, indent=2))
        # Clean up tmp
        for f in cookie_files:
            f.unlink(missing_ok=True)

        return {
            "status": "ok",
            "output": f"Cookies saved as TK_cookies_{name}.json\n{output}",
            "cookie_file": str(dest),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Login timed out after {_LOGIN_TIMEOUT}s"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_tiktok_show(args: dict[str, Any]) -> dict[str, Any]:
    """List saved TikTok cookie profiles and available videos."""
    show_users = args.get("show_users", True)
    show_videos = args.get("show_videos", True)

    lines: list[str] = []

    if show_users:
        cookies = sorted(TIKTOK_DIR.glob("TK_cookies_*.json"))
        if cookies:
            lines.append("Cookie profiles:")
            for c in cookies:
                account = c.stem.replace("TK_cookies_", "")
                lines.append(f"  {account} → {c}")
        else:
            lines.append(f"No cookie profiles found in {TIKTOK_DIR}")

    if show_videos:
        videos = sorted(
            f for f in TIKTOK_DIR.rglob("*.mp4")
        )
        if videos:
            lines.append(f"\nVideos in {TIKTOK_DIR}:")
            for v in videos[:20]:
                size_mb = v.stat().st_size / 1_048_576
                lines.append(f"  {v.name} ({size_mb:.1f}MB) → {v}")
        else:
            lines.append(f"\nNo .mp4 files found in {TIKTOK_DIR}")

    return {"status": "ok", "output": "\n".join(lines)}


def _get_display() -> str:
    """Return a DISPLAY value for browser operations."""
    display = os.environ.get("DISPLAY", "")
    if display:
        return display
    x11_dir = "/tmp/.X11-unix"
    if os.path.isdir(x11_dir):
        sockets = [f for f in os.listdir(x11_dir) if f.startswith("X")]
        if sockets:
            return f":{sockets[0][1:]}"
    return ":0"


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TIKTOK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tiktok_upload",
            "description": (
                "Upload a video to TikTok using saved session cookies. "
                f"Cookies must exist at {TIKTOK_DIR}/TK_cookies_{{user}}.json. "
                "Run tiktok_login first if not logged in."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "Account name (matches saved cookie profile).",
                    },
                    "video": {
                        "type": "string",
                        "description": "Absolute path to the .mp4 video file.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Caption/description. Supports #hashtags. Max 2200 chars.",
                    },
                    "schedule": {
                        "type": "string",
                        "description": "Optional schedule time as HH:MM (local time). Omit for immediate upload.",
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Run browser headlessly (default true).",
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
                "Log into TikTok with username and password to save session cookies. "
                "Only needs to be done once per account; cookies are stored permanently."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Profile name to save cookies under (e.g. 'myaccount').",
                    },
                    "username": {
                        "type": "string",
                        "description": "TikTok email or username.",
                    },
                    "password": {
                        "type": "string",
                        "description": "TikTok password.",
                    },
                },
                "required": ["name", "username", "password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tiktok_show",
            "description": (
                f"List saved TikTok cookie profiles and .mp4 videos in {TIKTOK_DIR}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "show_users": {
                        "type": "boolean",
                        "description": "List saved cookie profiles (default true).",
                    },
                    "show_videos": {
                        "type": "boolean",
                        "description": "List available video files (default true).",
                    },
                },
            },
        },
    },
]
