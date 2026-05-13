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


def build_memory_consolidation_nudge_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "memory_consolidation_nudge",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_memory_consolidation_nudge_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"memory_consolidation_nudge.{kind}",
            payload or {},
        )
    except Exception:
        pass

