"""Reversible prompt-layout policy for the visible chat and code lanes.

V2 moves stable, mode-specific contracts into the cacheable prefix and leaves
only current-turn material in the dynamic tail.  The switch is deliberately
centralised so an operator can restore the legacy layout without a code
rollback.
"""
from __future__ import annotations

import os


_ENV_NAME = "JARVIS_PROMPT_MODE_LAYOUT_V2"
_CONFIG_NAME = "prompt_mode_layout_v2_enabled"
_V3_ENV_NAME = "JARVIS_PROMPT_SCOPE_STABLE_BLOCKS_V3"
_V3_CONFIG_NAME = "prompt_scope_stable_blocks_v3_enabled"
_TRUTHY = frozenset(("1", "true", "yes", "on"))
_FALSY = frozenset(("0", "false", "no", "off"))


def mode_layout_v2_enabled() -> bool:
    """Return whether the cache-first mode layout is active.

    Environment wins over runtime config.  An unreadable config keeps the new
    default, while an explicitly malformed environment value falls through to
    config.  Setting either source to false is the operational kill switch.
    """
    raw = os.environ.get(_ENV_NAME)
    if raw is not None:
        value = raw.strip().lower()
        if value in _TRUTHY:
            return True
        if value in _FALSY:
            return False
    try:
        from core.runtime.settings import load_settings

        return bool(load_settings().extra.get(_CONFIG_NAME, True))
    except Exception:  # Config failure keeps the V2 default; the env kill switch still works.
        return True


def scope_stable_blocks_v3_enabled(*, scope: str | None = None) -> bool:
    """Route proven-stable blocks into the warmed chat/code prefix.

    V3 is independent and defaults off until an operator has measured and
    prewarmed both scope variants.  It cannot activate when V2 is disabled,
    so the existing kill switch still restores the complete legacy layout.
    """
    if not mode_layout_v2_enabled():
        return False
    if scope is None:
        try:
            from core.tools.tool_scoping import current_tool_scope

            scope = str(current_tool_scope() or "").strip().lower()
        except Exception:  # Unknown scope is never safe to move cache-late blocks from.
            return False
    if str(scope or "").strip().lower() not in {"chat", "code"}:
        return False
    raw = os.environ.get(_V3_ENV_NAME)
    if raw is not None:
        value = raw.strip().lower()
        if value in _TRUTHY:
            return True
        if value in _FALSY:
            return False
    try:
        from core.runtime.settings import load_settings

        return bool(load_settings().extra.get(_V3_CONFIG_NAME, False))
    except Exception:  # A new optimization stays off if its config cannot be proven.
        return False


def filter_visible_rules(text: str | None, *, scope: str) -> str | None:
    """Keep universal rules in code mode and conversational rules in chat.

    This is routing, not deletion: the source file remains unchanged and the
    kill switch restores the exact legacy block.
    """
    if not text or not mode_layout_v2_enabled() or scope != "code":
        return text
    chat_only_prefixes = (
        "**I don't end the conversation:**",
        "**Format:**",
        "**Silence and authenticity:**",
    )
    def _chat_only(line: str) -> bool:
        normalized = line.lstrip()
        if normalized.startswith("- "):
            normalized = normalized[2:].lstrip()
        return normalized.startswith(chat_only_prefixes)

    kept = [line for line in text.splitlines() if not _chat_only(line)]
    return "\n".join(kept).strip() or None


def recency_anchor(*, scope: str) -> str | None:
    """A short cache-late reminder; stable contracts live cache-first in V2."""
    if not mode_layout_v2_enabled():
        return None
    if scope == "chat":
        return (
            "[CHAT MODE — current turn] Read the user's intent and emotional "
            "temperature in this turn; apply the chat hierarchy and current style "
            "settings naturally without mentioning them."
        )
    if scope == "code":
        return (
            "[CODE MODE — current turn] Continue the requested work through a "
            "verified result; the cache-first code contract remains in force."
        )
    return None


__all__ = [
    "filter_visible_rules",
    "mode_layout_v2_enabled",
    "recency_anchor",
    "scope_stable_blocks_v3_enabled",
]
