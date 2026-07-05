from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_BASE = "https://api.srvlab.dk"          # jc's tunnel-base (Cloudflare → container)
_JC_TOKEN_PATH = Path.home() / ".config" / "jarvis-owner-token"   # genbrug jc's token-fil


def resolve_base_url(*, remote: str | None) -> str:
    """--remote > env CENTRAL_CLI_API_URL > default (jc-tunnel). Remote-først."""
    if remote:
        return remote.rstrip("/")
    env = os.environ.get("CENTRAL_CLI_API_URL", "").strip()
    if env:
        return env.rstrip("/")
    return _DEFAULT_BASE


def resolve_token() -> str | None:
    """env CENTRAL_CLI_TOKEN > jc's ~/.config/jarvis-owner-token. None hvis ingen."""
    env = os.environ.get("CENTRAL_CLI_TOKEN", "").strip()
    if env:
        return env
    try:
        tok = _JC_TOKEN_PATH.read_text(encoding="utf-8").strip()
        return tok or None
    except OSError:
        return None
