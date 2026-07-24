"""Shared scanner for multi-profile provider auth slots.

Auth profiles live at ``~/.jarvis-v2/auth/profiles/<profile>/providers/<provider>/``
(each provider dir holds credentials.json + state.json). Historically only the
"default" profile was used; this module discovers every profile whose
credentials are ready for a given provider, so each becomes its own provider slot.

Keyless providers (auth_kind == "none" or public proxies) get exactly one slot
regardless of how many profile directories exist — there is nothing per-profile
to authenticate.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from core.services.cheap_provider_runtime_adapters import (
    CHEAP_PROVIDER_DEFAULTS,
    provider_auth_ready,
)

try:  # public proxies are keyless regardless of CHEAP_PROVIDER_DEFAULTS
    from core.services.cheap_lane_balancer import _PUBLIC_PROXIES
except Exception:  # pragma: no cover - defensive fallback if import shape changes
    # Local mirror of the public-proxy set; membership alone marks keyless.
    _PUBLIC_PROXIES = frozenset({"ollamafreeapi", "arko", "opencode"})

# Extra keyless providers not necessarily in _PUBLIC_PROXIES.
_KEYLESS_EXTRA = frozenset({"pollinations", "ovhcloud"})

# Only REAL account profiles become extra slots: "default" + "account2"/"account3"/…
# Excludes backups (default.bak-*), single-provider/legacy profiles (groq, mistral,
# gemini, …) and OAuth profiles (codex, copilot). Multi-profile means multiple
# ACCOUNTS of the same providers — not per-provider or backup directories.
_ACCOUNT_PROFILE_RE = re.compile(r"^(default|account\d+)$")


def _is_account_profile(profile: str) -> bool:
    """True only for real account profiles (default, account2, account3, …)."""
    return bool(_ACCOUNT_PROFILE_RE.match(profile))

# Per-provider cache: {provider: (expiry_epoch, [profiles])}. Populated lazily;
# time.time() is only ever called inside functions, never at import.
_CACHE: dict[str, tuple[float, list[str]]] = {}
_TTL_SECONDS = 60.0


def clear_cache() -> None:
    """Drop all cached scan results (test helper / manual invalidation)."""
    _CACHE.clear()


def _profiles_root() -> Path:
    """Return the auth/profiles directory (honoring JARVIS_CONFIG_DIR)."""
    root = os.environ.get("JARVIS_CONFIG_DIR")
    base = Path(root) if root else Path.home() / ".jarvis-v2"
    return base / "auth" / "profiles"


def _is_keyless(provider: str) -> bool:
    """True if the provider needs no per-profile credentials.

    Keyless if its CHEAP_PROVIDER_DEFAULTS auth_kind is "none", OR it is a known
    public proxy / keyless extra. Public-proxy membership is sufficient on its
    own, so keyless providers don't require CHEAP_PROVIDER_DEFAULTS entries.
    """
    ak = str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("auth_kind") or "")
    if ak == "none":
        return True
    if ak in ("bearer", "api_key"):
        # Per-account API key required → NEVER keyless, even if listed as a public
        # proxy. opencode is in _PUBLIC_PROXIES but authenticates with real per-account
        # bearer keys (default + account2 on disk) — treating it keyless hid its
        # account2 key from the profile rotation. arko (runtime-key, shared) and the
        # auth_kind="none" proxies stay keyless.
        return False
    return provider in _PUBLIC_PROXIES or provider in _KEYLESS_EXTRA


def _sort_default_first(profiles: list[str]) -> list[str]:
    rest = sorted(p for p in profiles if p != "default")
    return (["default"] if "default" in profiles else []) + rest


def ready_profiles_for(provider: str) -> list[str]:
    """Return profiles with ready credentials for ``provider``.

    Result is sorted with "default" first, then the rest alphabetical. Cached
    per-provider for 60s. Keyless providers always return exactly ["default"].
    """
    now = time.time()
    cached = _CACHE.get(provider)
    if cached is not None and cached[0] > now:
        return list(cached[1])

    if _is_keyless(provider):
        result = ["default"]
        _CACHE[provider] = (now + _TTL_SECONDS, result)
        return list(result)

    ready: list[str] = []
    root = _profiles_root()
    try:
        profile_dirs = [p for p in root.iterdir() if p.is_dir()]
    except (FileNotFoundError, NotADirectoryError):
        profile_dirs = []

    for prof_dir in profile_dirs:
        profile = prof_dir.name
        if not _is_account_profile(profile):
            continue  # skip backups, single-provider, and OAuth profile dirs
        if not (prof_dir / "providers" / provider).is_dir():
            continue
        if provider_auth_ready(provider=provider, auth_profile=profile):
            ready.append(profile)

    result = _sort_default_first(ready)
    _CACHE[provider] = (now + _TTL_SECONDS, result)
    return list(result)
