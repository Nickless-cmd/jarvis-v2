"""Central HUD palette, status-maps and the ``_esc`` markup guard.

Extracted verbatim from ``hud.py`` (behaviour-preserving split). Every colour,
status/decision/severity map and the ``_esc`` helper live here so the mixins and
the app shell can all import them from one place. ``hud`` re-exports every symbol
so ``from central_cli.hud import BG, _STATE, _esc, ...`` keeps working unchanged.
"""

from __future__ import annotations

from typing import Any

from rich.markup import escape as _rescape


def _esc(value: Any) -> str:
    """Escape live/user data before it goes into a Rich-markup string, so a
    value containing '[...]' (asyncio tasks, paths, log lines) can never be
    mis-parsed as a style tag and crash the render."""
    return _rescape(str(value if value is not None else ""))


# --- palette (mockup :root — exact) --------------------------------------
BG = "#0a0e14"
PANEL = "#0d1420"
LINE = "#16324a"
CYAN = "#00d4ff"
AMBER = "#ffb000"
RED = "#ff4a4a"
GREEN = "#00ff88"
BLUE = "#4488ff"
DIM = "#4a5568"
FG = "#c7d3e0"
FGDIM = "#7b8a9c"
BAR = "#080c12"       # tabs/cmd background
SPARK = "#4a5568"     # dim spark

# state -> (color, glyph label)
_STATE = {
    "aktiv": (GREEN, "● aktiv"),
    "idle": (DIM, "○ idle"),
    "degraded": (AMBER, "◆ degraded"),
    "død": (RED, "✖ død"),
}

# feed decision -> color
_DECISION = {
    "error": RED, "critical": RED, "red": RED, "deny": RED, "block": RED,
    "warn": AMBER, "warning": AMBER, "yellow": AMBER,
    "success": GREEN, "observe": GREEN, "green": GREEN, "allow": GREEN, "ok": GREEN,
}

# anomaly importance -> color
_IMPORTANCE = {
    "high": RED, "critical": RED, "severe": RED,
    "medium": AMBER, "low": DIM, "info": CYAN,
}

# status-word -> (color, label)
_STATUS = {
    "green": (GREEN, "GRØN"),
    "yellow": (AMBER, "GUL"),
    "red": (RED, "RØD"),
}
_CLUSTER_STATUS = {"green": GREEN, "yellow": AMBER, "red": RED, "idle": DIM}
_SEVERITY = {
    "severe": RED, "critical": RED, "error": RED,
    "warn": AMBER, "warning": AMBER, "info": CYAN,
}
# Rådets #4: affekt-farver. uro=rød, tryk=gul, varme=grøn, ro=dæmpet blå-grå.
_AFFECT = {
    "uro": (RED, "●"),
    "tryk": (AMBER, "▲"),
    "varme": (GREEN, "♥"),
    "ro": (BLUE, "●"),
}

# agent status -> color
_AGENT_STATUS = {
    "running": GREEN, "active": GREEN, "live": GREEN,
    "idle": DIM, "pending": DIM, "queued": DIM,
    "done": BLUE, "completed": BLUE, "finished": BLUE,
    "error": RED, "failed": RED, "dead": RED,
}

# run status -> color
_RUN_STATUS = {
    "completed": GREEN, "failed": RED, "cancelled": AMBER,
    "active": BLUE, "running": BLUE,
}
