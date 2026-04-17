"""TikTok analytics — video-statistik for en given bruger.

Strategi:
  1. Hent profil-data via direkte HTTP scrape (UNIVERSAL_DATA)
  2. Brug Playwright til at generere msToken + ttwid cookies
  3. Kald TikTok's interne video-list API med de korrekte cookies
  4. Returnér video-stats: views, likes, comments, shares

Kør med:
    conda activate ai
    python /media/projects/jarvis-v2/scripts/pipelines/tiktok_analytics.py

Manuel ms_token (varer kun ~2 timer):
    python tiktok_analytics.py --ms-token <TOKEN>

--- HOWTO: Hent ms_token fra browser ---
1. Gå til https://www.tiktok.com og log ind
2. DevTools → Application → Cookies → https://www.tiktok.com
3. Find cookien "msToken" — kopier værdien
4. Kør: python tiktok_analytics.py --ms-token <værdien>
"""
from __future__ import annotations

import asyncio
import argparse
import json
import os
import pickle
import re
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

USERNAME = os.environ.get("USERNAME_OVERRIDE", "rotflmaodilligaf")
COOKIE_DIR = "/home/bs/.jarvis-v2/tiktok"
# Try new JSON cookie format first, fall back to old pickle format
COOKIE_FILE = os.path.join(COOKIE_DIR, f"TK_cookies_{USERNAME}.json")

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*",
}


# ---------------------------------------------------------------------------
# Profil scrape (ingen auth nødvendig)
# ---------------------------------------------------------------------------


def fetch_profile() -> tuple[dict, str, str]:
    """Hent profil-data + secUid + userId via UNIVERSAL_DATA."""
    req = urllib.request.Request(
        f"https://www.tiktok.com/@{USERNAME}",
        headers={**BASE_HEADERS, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    match = re.search(
        r'id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not match:
        raise RuntimeError("Kunne ikke finde UNIVERSAL_DATA i TikTok-profil HTML")

    data = json.loads(match.group(1))
    scope = data.get("__DEFAULT_SCOPE__", {})
    user_info = scope.get("webapp.user-detail", {}).get("userInfo", {})
    user = user_info.get("user", {})
    stats = user_info.get("stats", {})
    sec_uid = user.get("secUid", "")
    user_id = user.get("id", "")
    return stats, sec_uid, user_id


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------


def _load_saved_cookies() -> dict[str, str]:
    """Load sessionid m.fl. fra TikTok uploader pickle-fil."""
    try:
        with open(COOKIE_FILE, "rb") as f:
            raw = pickle.load(f)
        return {str(c["name"]): str(c["value"]) for c in raw if "name" in c and "value" in c}
    except Exception:
        return {}


def _cookies_to_header(cookie_dict: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items())


# ---------------------------------------------------------------------------
# Playwright: generer msToken + session-cookies
# ---------------------------------------------------------------------------


async def _get_tiktok_cookies(extra_cookies: dict[str, str]) -> dict[str, str]:
    """Kør headless Playwright, besøg TikTok, returner session-cookies."""
    from playwright.async_api import async_playwright

    print("[info] Starter Playwright for at generere msToken...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=BASE_HEADERS["User-Agent"],
            locale="en-US",
        )

        # Sæt eksisterende cookies (sessionid)
        if extra_cookies:
            await ctx.add_cookies([
                {"name": k, "value": v, "domain": ".tiktok.com", "path": "/"}
                for k, v in extra_cookies.items()
            ])

        page = await ctx.new_page()
        await page.goto("https://www.tiktok.com/", wait_until="domcontentloaded")
        await asyncio.sleep(6)  # Vent på at msToken genereres via JS

        # Udtræk alle cookies
        raw_cookies = await ctx.cookies("https://www.tiktok.com")
        result = {c["name"]: c["value"] for c in raw_cookies}

        await browser.close()

    names = list(result.keys())
    print(f"[info] Cookies hentet: {names}")
    return result


# ---------------------------------------------------------------------------
# Video-liste via TikTok intern API
# ---------------------------------------------------------------------------


def _fetch_video_list(sec_uid: str, cookies: dict[str, str], count: int = 30) -> list[dict]:
    """Hent video-liste via TikTok's interne API."""
    params = urllib.parse.urlencode({
        "aid": "1988",
        "secUid": sec_uid,
        "count": str(count),
        "cursor": "0",
        "coverFormat": "2",
    })
    req = urllib.request.Request(
        f"https://www.tiktok.com/api/post/item_list/?{params}",
        headers={
            **BASE_HEADERS,
            "Cookie": _cookies_to_header(cookies),
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()

    if not raw:
        return []

    data = json.loads(raw)
    return data.get("itemList", [])


# ---------------------------------------------------------------------------
# Hoved-funktion
# ---------------------------------------------------------------------------


async def run(manual_ms_token: str | None, max_videos: int) -> dict:
    # 1. Profil-data
    print(f"[info] Henter profil for @{USERNAME}...")
    profile_stats, sec_uid, user_id = fetch_profile()
    print(f"  Følgere: {profile_stats.get('followerCount', '?'):,}")
    print(f"  Videoer: {profile_stats.get('videoCount', '?')}")
    print(f"  Likes:   {profile_stats.get('heartCount', '?'):,}")
    print(f"  secUid:  {sec_uid[:40]}...")

    # 2. Cookies
    saved = _load_saved_cookies()
    if manual_ms_token:
        saved["msToken"] = manual_ms_token
        print(f"[info] Bruger manuel msToken: {manual_ms_token[:20]}...")
        all_cookies = saved
    else:
        # Generer msToken via Playwright
        all_cookies = await _get_tiktok_cookies(saved)
        # Berig med sessionid fra fil
        for k, v in saved.items():
            if k not in all_cookies:
                all_cookies[k] = v

    ms_token = all_cookies.get("msToken", "")
    print(f"[info] msToken: {'ja (' + ms_token[:20] + '...)' if ms_token else 'MANGLER'}")

    # 3. Video-liste
    print(f"\n[info] Henter op til {max_videos} videoer...")
    try:
        items = _fetch_video_list(sec_uid, all_cookies, count=max_videos)
    except Exception as e:
        print(f"  [warn] Video-API fejlede: {e}")
        items = []

    # 4. Parse og vis
    videos = []
    for v in items:
        s = v.get("stats", {}) or v.get("statsV2", {})
        ct = v.get("createTime", 0)
        entry = {
            "id": v.get("id", "?"),
            "desc": (v.get("desc", "") or "")[:80],
            "created": datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M") if ct else "?",
            "views":    int(s.get("playCount", 0) or s.get("vv", 0) or 0),
            "likes":    int(s.get("diggCount", 0) or 0),
            "comments": int(s.get("commentCount", 0) or 0),
            "shares":   int(s.get("shareCount", 0) or 0),
        }
        videos.append(entry)
        print(f"  [{entry['created']}] views {entry['views']:>7,}  likes {entry['likes']:>5,}  "
              f"comments {entry['comments']:>4,}  shares {entry['shares']:>4,}  — {entry['desc'][:50]}")

    output_file = f"/tmp/tiktok_stats_{USERNAME}.json"
    result = {
        "username": USERNAME,
        "fetched_at": datetime.utcnow().isoformat(),
        "profile_stats": profile_stats,
        "videos": videos,
    }

    Path(output_file).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[info] Gemt til {output_file}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ms-token", default=None)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()

    result = asyncio.run(run(args.ms_token, args.count))
    videos = result["videos"]
    if videos:
        print(f"\n{'='*55}")
        print(f"Total views ({len(videos)} videoer): {sum(v['views'] for v in videos):,}")
        print(f"Total likes:                    {sum(v['likes'] for v in videos):,}")
        best = max(videos, key=lambda v: v["views"])
        print(f"Bedste: {best['views']:,} views — {best['desc'][:50]}")
    else:
        print("\n[warn] Ingen video-data. Prøv med --ms-token <TOKEN> fra browser.")
        print("       Se instrukser øverst i scriptet.")


if __name__ == "__main__":
    main()
