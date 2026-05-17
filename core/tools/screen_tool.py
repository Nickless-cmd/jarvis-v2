"""Screen control tool — Jarvis can turn monitors on/off/standby.

Uses xset DPMS commands through the correct display session (DISPLAY=:1
with gdm Xauthority). Works because Jarvis runs on the same machine as
Bjørn's desktop (CheifOne), under the same X session.

States:
- off: DPMS force off (monitors go dark immediately)
- on: DPMS force on (wake up from standby/off)
- standby: DPMS force standby (power saving, slower wake)
- status: query current DPMS state ("Monitor is On/Off/Standby")
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# The X display and auth that actually work for Bjørn's session
_DISPLAY = ":1"
_XAUTHORITY = "/run/user/1000/gdm/Xauthority"
_USER = "bs"

_BASE_CMD = [
    "sudo", "-u", _USER,
    "DISPLAY=" + _DISPLAY,
    "XAUTHORITY=" + _XAUTHORITY,
    "xset",
]


def _xset_dpms(action: str) -> dict[str, Any]:
    """Run an xset dpms command and return structured result."""
    cmd = _BASE_CMD + ["dpms", "force", action]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        stderr = result.stderr.strip()
        if result.returncode != 0:
            return {
                "status": "error",
                "text": f"xset failed (exit {result.returncode}): {stderr or 'no stderr'}",
                "action": action,
            }
        if stderr and "kan ikke sende" not in stderr:
            return {
                "status": "ok",
                "text": f"Monitor action '{action}' sent. Stderr note: {stderr}",
                "action": action,
            }
        return {
            "status": "ok",
            "text": f"Monitor action '{action}' sent successfully.",
            "action": action,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "text": f"xset timed out after 10s for action '{action}'",
            "action": action,
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "text": "xset not found on this system — is x11-server-utils installed?",
        }
    except Exception as exc:
        logger.exception("screen_control failed")
        return {
            "status": "error",
            "text": f"Screen control failed: {exc}",
        }


def _xset_dpms_status() -> dict[str, Any]:
    """Query DPMS status and return structured result."""
    cmd = _BASE_CMD + ["q"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            return {
                "status": "error",
                "text": f"xset query failed (exit {result.returncode}): {stderr or 'no stderr'}",
            }
        # Parse DPMS state from output
        for line in output.splitlines():
            if "Monitor is" in line:
                state = line.strip()
                return {
                    "status": "ok",
                    "text": state,
                    "monitor_state": state.replace("Monitor is ", "").strip().lower(),
                }
        return {
            "status": "ok",
            "text": f"DPMS status queried. Raw:\n{output}",
        }
    except Exception as exc:
        return {
            "status": "error",
            "text": f"DPMS status query failed: {exc}",
        }


def _exec_screen_control(args: dict[str, Any]) -> dict[str, Any]:
    """Execute the screen control tool."""
    action = str(args.get("command") or args.get("action") or "").strip().lower()

    if not action:
        return {
            "status": "error",
            "text": "No action provided. Use 'on', 'off', 'standby', or 'status'.",
        }

    valid_actions = {"on", "off", "standby", "status"}
    if action not in valid_actions:
        return {
            "status": "error",
            "text": f"Invalid action: '{action}'. Valid: on, off, standby, status.",
        }

    if action == "status":
        return _xset_dpms_status()

    return _xset_dpms(action)


SCREEN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "screen_control",
            "description": (
                "Control the desktop monitors: turn them on, off, or "
                "standby via DPMS. Also supports 'status' to query "
                "current monitor state. "
                "Use 'screen_control action=off' to turn screens off, "
                "'screen_control action=on' to wake them. "
                "Virker på Bjørns maskine via xset DPMS."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["on", "off", "standby", "status"],
                        "description": (
                            "What to do: 'off' = sluk skærme (DPMS force off), "
                            "'on' = tænd skærme, 'standby' = power saving, "
                            "'status' = query current state"
                        ),
                    },
                },
                "required": ["action"],
            },
        },
    },
]
