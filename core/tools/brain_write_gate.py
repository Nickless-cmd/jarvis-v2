"""HARD gate for user-initiated writes to Jarvis' brain.

Writing to Jarvis' mind is an identity/security boundary that must not rely on
the model obeying a prompt. Enforced at the user-facing forward endpoint
(POST /v1/tools/execute). Jarvis' own autonomous path never crosses that
boundary, so his agency is unaffected.
"""
from __future__ import annotations

BRAIN_WRITE_TOOLS: tuple[str, ...] = ("remember_this", "archive_brain_entry")


def check_brain_write_allowed(name: str, *, role: str) -> bool:
    """True if a user-initiated call to `name` is permitted for `role`.
    Non-brain-write tools: always True. Brain-write: owner/unbound only."""
    if name not in BRAIN_WRITE_TOOLS:
        return True
    return str(role or "").strip().lower() in ("", "owner")
