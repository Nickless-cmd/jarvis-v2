#!/usr/bin/env python
"""Mint a JarvisX bearer token for a user.

Usage:
    python scripts/mint_jarvisx_token.py --user-id <id> [--role member|owner|guest] [--ttl-days N] [--name "Mikkel laptop"]

Prints the token + summary. Token is a JWT signed with the auth secret in
~/.jarvis-v2/config/runtime.json — same secret the API uses to verify.

Tokens are SELF-CONTAINED (JWT) — there's no DB lookup on verify, so we
also write a registry entry to ~/.jarvis-v2/state/jarvisx_tokens.json so
the owner can list/audit who's been issued tokens. The registry doesn't
participate in verification (yet) — it's a paper trail.

For revocation: rotate the jarvisx_auth_secret in runtime.json. That
invalidates EVERY issued token at once (panic-button behaviour). A
future per-token revocation list could be added if the user base grows.

Example:
    # Mint Bjørn's owner token, 365 days
    python scripts/mint_jarvisx_token.py --user-id bjorn --role owner --ttl-days 365 --name "Bjorn desktop"

    # Mint Mikkel's member token, 30 days
    python scripts/mint_jarvisx_token.py --user-id mikkel --role member --name "Mikkel Windows"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _registry_path() -> Path:
    from core.runtime.config import STATE_DIR
    return Path(STATE_DIR) / "jarvisx_tokens.json"


def _append_registry(entry: dict) -> None:
    """Append a token-issue entry to the audit registry. Best-effort."""
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    except Exception:
        existing = []
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mint a JarvisX bearer token for a user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Example:")[-1] if "Example:" in (__doc__ or "") else "",
    )
    parser.add_argument("--user-id", required=True,
                        help="Unique user identifier (e.g. 'bjorn', 'mikkel')")
    parser.add_argument("--role", default="member", choices=["owner", "member", "guest"],
                        help="Authorization role (default: member)")
    parser.add_argument("--ttl-days", type=int, default=30,
                        help="Token validity in days (default: 30, max: 365)")
    parser.add_argument("--name", default="",
                        help="Human-readable device/user description for the audit log")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of human-readable summary")
    parser.add_argument("--no-registry", action="store_true",
                        help="Don't write to audit registry (one-off testing)")
    args = parser.parse_args()

    from core.runtime.jarvisx_auth import issue_token

    result = issue_token(
        user_id=args.user_id,
        role=args.role,
        ttl_days=args.ttl_days,
    )

    # Append to registry
    if not args.no_registry:
        try:
            _append_registry({
                "user_id": result["user_id"],
                "role": result["role"],
                "name": args.name,
                "issued_at": result["issued_at"],
                "expires_at": result["expires_at"],
                "ttl_days": result["ttl_days"],
                "token_preview": result["token"][:24] + "...",  # never store full token
            })
        except Exception as exc:
            print(f"⚠ registry write failed (token still valid): {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("─" * 64)
        print(f" Token issued for: {result['user_id']}")
        print(f" Role:             {result['role']}")
        if args.name:
            print(f" Name:             {args.name}")
        print(f" Issued at:        {result['issued_at']}")
        print(f" Expires at:       {result['expires_at']} ({result['ttl_days']} days)")
        print("─" * 64)
        print(" Token (copy this — it won't be shown again):")
        print()
        print(f"   {result['token']}")
        print()
        print(" Usage in JarvisX-app config (~/.config/jarvisx/config.json):")
        print(json.dumps({
            "apiBaseUrl": "https://api.srvlab.dk",
            "userId": result["user_id"],
            "apiToken": result["token"],
        }, indent=2))
        print("─" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
