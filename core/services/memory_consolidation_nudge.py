"""Memory consolidation nudge — unconditional prompt section.

This is the "prompt half" of the double-nudge system. It injects a short
reminder into every visible prompt asking Jarvis to check whether the current
turn contains something worth saving, and if so, to call a save tool.

The "daemon half" lives in daemon_memory_safeguard.py and runs post-hoc
to catch anything that slipped through.
"""
from __future__ import annotations


def memory_consolidation_nudge_section() -> str:
    """Return a short prompt section that fires every turn unconditionally."""
    return (
        "💾 Inden du afslutter: Skal noget fra denne tur gemmes? "
        "→ Hvis ja: MEMORY.md eller private brain? → Kald tool'et. "
        "Aldrig bare skrive \"jeg husker det\"."
    )


