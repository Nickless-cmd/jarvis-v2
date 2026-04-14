"""Desktop orb phase — writes current Jarvis pipeline state to a temp file.

The orb widget polls /tmp/jarvis-voice-phase.json every ~800ms and updates its
animation accordingly. Valid phases: idle | user | think | speak
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PHASE_FILE = Path("/tmp/jarvis-voice-phase.json")


def set_phase(phase: str) -> None:
    """Write orb phase. Silently ignores any I/O errors."""
    try:
        _PHASE_FILE.write_text(json.dumps({"phase": phase}))
    except Exception as exc:
        logger.debug("orb_phase: could not write phase %r: %s", phase, exc)
