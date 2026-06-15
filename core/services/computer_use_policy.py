"""Computer-use-politik (§4.7) — per-bruger on/off for operator/computer-tools.

Sikkerhedsmodel: dette er en RESTRIKTION oven på permission_engine. Når en bruger
slår computer-use fra, fjernes operator_*-tools (skærm/mus/bash-på-maskinen) fra
det tilladte sæt i tool_scoping.allowed_tool_names — modellen får dem slet ikke
tilbudt. Default er TIL (uændret adfærd). Persisteres i state_store.

Prefix-fjernelse ("operator_") er bevidst tilladt HER fordi det kun INDSKRÆNKER
adgang (fail-safe retning) — modsat permission_engine's allowlists der er
eksplicitte for ikke at give utilsigtet adgang.
"""
from __future__ import annotations

from core.runtime.state_store import load_json, save_json

_STATE_KEY = "computer_use_policy"

# Eksplicitte computer-use-tools ud over operator_*-prefikset.
_EXPLICIT_COMPUTER_USE_TOOLS = frozenset({
    "clipboard_read", "clipboard_write", "screenshot", "screenshot_window",
    "find_image", "ocr_region", "record_audio", "speak", "watch_folder",
})


def is_computer_use_tool(name: str) -> bool:
    n = str(name or "")
    return n.startswith("operator_") or n in _EXPLICIT_COMPUTER_USE_TOOLS


def _load() -> dict[str, bool]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def computer_use_enabled(user_id: str | None) -> bool:
    """Default TIL — kun eksplicit fravalg slår fra."""
    return _load().get(str(user_id or ""), True)


def set_computer_use(user_id: str | None, enabled: bool) -> dict[str, object]:
    data = _load()
    data[str(user_id or "")] = bool(enabled)
    save_json(_STATE_KEY, data)
    return {"status": "ok", "user_id": str(user_id or ""), "enabled": bool(enabled)}
