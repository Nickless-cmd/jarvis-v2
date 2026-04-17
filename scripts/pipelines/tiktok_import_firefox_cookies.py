"""Import TikTok cookies from Firefox profile → TK_cookies_{account}.json

Kør dette script, når session-cookies er udløbet eller efter et nyt Firefox-login.

Kør med:
    conda activate ai
    python scripts/pipelines/tiktok_import_firefox_cookies.py
    python scripts/pipelines/tiktok_import_firefox_cookies.py --account mitandetnavn
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

TIKTOK_DIR = Path("/home/bs/.jarvis-v2/tiktok")
FIREFOX_BASE = Path("/home/bs/snap/firefox/common/.mozilla/firefox")
FALLBACK_FIREFOX = Path("/home/bs/.mozilla/firefox")

SESSION_COOKIE_NAMES = {"sessionid", "sid_tt", "sessionid_ss", "passport_auth_status"}


def find_firefox_cookie_db() -> Path:
    for base in [FIREFOX_BASE, FALLBACK_FIREFOX]:
        hits = list(base.glob("*.default*/cookies.sqlite"))
        if hits:
            return hits[0]
    raise FileNotFoundError(
        "Ingen Firefox cookies.sqlite fundet. "
        "Prøv /home/bs/snap/firefox/... eller /home/bs/.mozilla/firefox/..."
    )


def extract_tiktok_cookies(db_path: Path) -> list[dict]:
    tmp = tempfile.mktemp(suffix=".sqlite")
    shutil.copy2(db_path, tmp)
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        cur.execute(
            "SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite "
            "FROM moz_cookies WHERE host LIKE '%tiktok.com'"
        )
        rows = cur.fetchall()
        con.close()
    finally:
        os.unlink(tmp)

    samesite_map = {0: "None", 1: "Lax", 2: "Strict"}
    cookies = []
    for name, value, host, path, expiry, secure, httponly, samesite_int in rows:
        cookies.append({
            "name": name,
            "value": value,
            "domain": host,
            "path": path,
            "expires": expiry,
            "secure": bool(secure),
            "httpOnly": bool(httponly),
            "sameSite": samesite_map.get(samesite_int, "Lax"),
        })
    return cookies


def main():
    parser = argparse.ArgumentParser(description="Import TikTok cookies fra Firefox")
    parser.add_argument("--account", default="rotflmaodilligaf", help="TikTok account name")
    parser.add_argument("--dry-run", action="store_true", help="Vis cookies uden at gemme")
    args = parser.parse_args()

    db_path = find_firefox_cookie_db()
    print(f"[info] Firefox cookie DB: {db_path}")

    cookies = extract_tiktok_cookies(db_path)
    print(f"[info] Fandt {len(cookies)} TikTok cookies")

    session_cookies = [c for c in cookies if c["name"] in SESSION_COOKIE_NAMES]
    if not session_cookies:
        print("[warn] Ingen session-cookies fundet — er du logget ind i Firefox på tiktok.com?")
        return

    for c in session_cookies:
        expiry = c.get("expires", 0)
        import time
        expires_in_days = (expiry - int(time.time())) // 86400 if expiry else -1
        print(f"  {c['name']:30s} udløber om ~{expires_in_days} dage")

    if args.dry_run:
        print("[info] Dry-run — gemmer ikke.")
        return

    TIKTOK_DIR.mkdir(parents=True, exist_ok=True)
    out = TIKTOK_DIR / f"TK_cookies_{args.account}.json"
    out.write_text(json.dumps(cookies, indent=2))
    print(f"[info] Gemt til {out}")


if __name__ == "__main__":
    main()
