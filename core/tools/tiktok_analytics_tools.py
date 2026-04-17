"""TikTok analytics tools for Jarvis.

Fetches video statistics and profile data for TikTok accounts.
Uses direct HTTP scraping for profile data and Playwright for
generating msToken to access the video list API.

Tools:
  tiktok_analytics — fetch video stats (views, likes, comments, shares)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pickle
import re
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

COOKIE_DIR = "/home/bs/.jarvis-v2/tiktok"
CONDA_PYTHON = "/opt/conda/envs/ai/bin/python"

_BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_saved_cookies(username: str) -> dict[str, str]:
    """Load session cookies from TK_cookies_{username}.json (tiktokautouploader format)."""
    # Try new JSON format first (tiktokautouploader)
    json_file = os.path.join(COOKIE_DIR, f"TK_cookies_{username}.json")
    try:
        with open(json_file) as f:
            raw = json.load(f)
        return {str(c["name"]): str(c["value"]) for c in raw if "name" in c and "value" in c}
    except Exception:
        pass
    # Fallback: old pickle format
    cookie_file = os.path.join(COOKIE_DIR, f"tiktok_session-{username}.cookie")
    try:
        with open(cookie_file, "rb") as f:
            raw = pickle.load(f)
        return {str(c["name"]): str(c["value"]) for c in raw if "name" in c and "value" in c}
    except Exception:
        return {}


def _fetch_profile(username: str) -> tuple[dict, str, str]:
    """Scrape profile stats + secUid + userId from UNIVERSAL_DATA."""
    req = urllib.request.Request(
        f"https://www.tiktok.com/@{username}",
        headers={**_BASE_HEADERS, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    match = re.search(
        r'id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    if not match:
        raise RuntimeError("UNIVERSAL_DATA not found in TikTok profile HTML")

    data = json.loads(match.group(1))
    scope = data.get("__DEFAULT_SCOPE__", {})
    user_info = scope.get("webapp.user-detail", {}).get("userInfo", {})
    user = user_info.get("user", {})
    stats = user_info.get("stats", {})
    return stats, user.get("secUid", ""), user.get("id", "")


async def _get_tiktok_cookies(seed_cookies: dict[str, str]) -> dict[str, str]:
    """Run headless Playwright to generate msToken and session cookies."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=_BASE_HEADERS["User-Agent"],
            locale="en-US",
        )
        if seed_cookies:
            await ctx.add_cookies([
                {"name": k, "value": v, "domain": ".tiktok.com", "path": "/"}
                for k, v in seed_cookies.items()
            ])
        page = await ctx.new_page()
        await page.goto("https://www.tiktok.com/", wait_until="domcontentloaded")
        await asyncio.sleep(6)
        raw = await ctx.cookies("https://www.tiktok.com")
        await browser.close()

    return {c["name"]: c["value"] for c in raw}


def _fetch_video_list(sec_uid: str, cookies: dict[str, str], count: int) -> list[dict]:
    """Call TikTok's internal video list API."""
    params = urllib.parse.urlencode({
        "aid": "1988",
        "secUid": sec_uid,
        "count": str(count),
        "cursor": "0",
        "coverFormat": "2",
    })
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = urllib.request.Request(
        f"https://www.tiktok.com/api/post/item_list/?{params}",
        headers={**_BASE_HEADERS, "Cookie": cookie_header},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    if not raw:
        return []
    return json.loads(raw).get("itemList", [])


def _parse_video(v: dict) -> dict:
    s = v.get("stats", {}) or v.get("statsV2", {})
    ct = v.get("createTime", 0)
    return {
        "id": v.get("id", ""),
        "desc": (v.get("desc", "") or "")[:120],
        "created": datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M") if ct else "",
        "views":    int(s.get("playCount", 0) or s.get("vv", 0) or 0),
        "likes":    int(s.get("diggCount", 0) or 0),
        "comments": int(s.get("commentCount", 0) or 0),
        "shares":   int(s.get("shareCount", 0) or 0),
    }


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def _exec_tiktok_analytics(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch TikTok video statistics for a user.

    Uses the standalone script as subprocess because Playwright's async
    event loop conflicts with Jarvis's running loop.

    Args:
        username:  TikTok username to fetch stats for (default: rotflmaodilligaf).
        count:     Max number of videos to fetch (default: 30, max: 100).
        ms_token:  Optional msToken cookie value from browser (auto-generated if omitted).
    """
    username = args.get("username", "rotflmaodilligaf")
    count = min(int(args.get("count", 30)), 100)
    ms_token = args.get("ms_token") or None

    script_path = "/media/projects/jarvis-v2/scripts/pipelines/tiktok_analytics.py"

    try:
        # Use the standalone script as subprocess (avoids asyncio.run() conflict)
        cmd = [CONDA_PYTHON, script_path, "--count", str(count)]
        if ms_token:
            cmd.extend(["--ms-token", ms_token])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "USERNAME_OVERRIDE": username},
        )

        if result.returncode != 0:
            return {"status": "error", "error": result.stderr[-500:] or "Script failed"}

        # The script writes JSON to /tmp/tiktok_stats_{username}.json
        output_file = f"/tmp/tiktok_stats_{username}.json"
        if not Path(output_file).exists():
            return {"status": "error", "error": "Script ran but no output file produced"}

        data = json.loads(Path(output_file).read_text())

        # Transform to our standard format
        profile_stats = data.get("profile_stats", {})
        videos_raw = data.get("videos", [])

        videos = []
        for v in videos_raw:
            videos.append({
                "id": v.get("id", ""),
                "desc": v.get("desc", "")[:120],
                "created": v.get("created", ""),
                "views": v.get("views", 0),
                "likes": v.get("likes", 0),
                "comments": v.get("comments", 0),
                "shares": v.get("shares", 0),
            })

        total_views = sum(v["views"] for v in videos)
        total_likes = sum(v["likes"] for v in videos)
        best = max(videos, key=lambda v: v["views"]) if videos else None

        return {
            "status": "ok",
            "username": username,
            "fetched_at": data.get("fetched_at", datetime.utcnow().isoformat()),
            "profile": {
                "followers": profile_stats.get("followerCount", 0),
                "following": profile_stats.get("followingCount", 0),
                "likes": profile_stats.get("heartCount", 0),
                "video_count": profile_stats.get("videoCount", 0),
            },
            "videos": videos,
            "summary": {
                "total_views": total_views,
                "total_likes": total_likes,
                "video_count": len(videos),
                "best_video": best,
            },
            "cached_at": output_file,
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Script timed out after 120s"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TIKTOK_ANALYTICS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tiktok_analytics",
            "description": (
                "Fetch TikTok video statistics for a user account. "
                "Returns profile stats (followers, likes, video count) and per-video stats "
                "(views, likes, comments, shares) for the most recent videos. "
                "Uses saved session cookies automatically — no manual login needed. "
                "Provide ms_token from browser cookies if the auto-generated token fails."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "TikTok username to fetch stats for (without @). Default: rotflmaodilligaf.",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of recent videos to fetch. Default: 30, max: 100.",
                    },
                    "ms_token": {
                        "type": "string",
                        "description": (
                            "Optional msToken cookie from browser. Auto-generated if not provided. "
                            "To get manually: TikTok.com → DevTools → Application → Cookies → msToken."
                        ),
                    },
                },
            },
        },
    },
]
