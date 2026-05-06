"""x-api-key resolution + workspace binding for Anthropic-compat endpoint."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STATE_DIR = Path(os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state"))
_KEYS_PATH = _STATE_DIR / "anthropic_api_keys.json"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_REPO_KEYS_PATH = _REPO_ROOT / "state" / "anthropic_api_keys.json"

_cache: dict[str, dict] = {}
_loaded = False


def _load() -> dict:
    global _loaded
    if _loaded:
        return _cache
    raw = {}
    for path in (_KEYS_PATH, _REPO_KEYS_PATH):
        if path.exists():
            try:
                raw = json.loads(path.read_text()).get("keys", {}) or {}
                break
            except Exception as exc:
                logger.warning("anthropic_auth: failed to read %s: %s", path, exc)
    _cache.clear()
    _cache.update(raw or {})
    _loaded = True
    return _cache


def invalidate_cache() -> None:
    global _loaded
    _cache.clear()
    _loaded = False


def resolve_api_key(api_key: Optional[str], *, dev_mode_open: bool = False) -> Optional[dict]:
    """Return {'user': str, 'workspace': str} or None for invalid keys."""
    if dev_mode_open:
        return {"user": "dev", "workspace": "default"}
    if not api_key:
        return None
    normalized = str(api_key).strip()
    if not normalized:
        return None
    keys = _load()
    return keys.get(normalized)


def short_key_for_log(api_key: Optional[str]) -> str:
    """Return first 4 chars + length suffix; never log full key."""
    if not api_key:
        return "<none>"
    n = str(api_key).strip()
    if len(n) <= 4:
        return f"<{len(n)}-char-key>"
    return f"{n[:4]}<{len(n)}>"
