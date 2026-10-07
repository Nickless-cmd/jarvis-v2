"""Screen control — turn Bjørn's monitors on/off/standby, or read their state.

The command runs on the OPERATOR's desktop (CheifOne) through the JarvisX
bridge. Jarvis' runtime lives in a container on the server (10.0.0.39) and
has no display of its own, so nothing here runs locally.

Two paths, both measured on CheifOne 5/10-2026:

* **primary — sysfs DRM.** ``/sys/class/drm/card*-DP-*/dpms`` takes
  On/Off/Standby. Passwordless ``sudo -n`` works, and it does NOT touch the
  session lock.
* **fallback — GNOME D-Bus.** ``org.gnome.ScreenSaver.SetActive(true)``.
  NOTE: this LOCKS the session, so it is only tried for off/standby, and only
  when no connected DP output could be reached at all.

``xset dpms`` is NOT a path. The session is Wayland, and XWayland answers
"Server does not have the DPMS Extension". The previous implementation shelled
out to ``xset`` on a hardcoded ``DISPLAY=:1`` — dead code twice over: it
assumed Jarvis ran on the desktop, and the extension does not exist there
anyway.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Bridge round-trip: command timeout + the 25s approval slack operator_bash adds.
_COMMAND_TIMEOUT_S = 20.0
_BRIDGE_TIMEOUT_S = 50.0

#: sysfs DRM loop. Shared by every action; the action is substituted in.
#: Exits 3 when no connected DP output was found, so the caller can tell
#: "nothing to act on" apart from "the command failed".
_DPMS_SHELL = r"""
set -u
found=0
for d in /sys/class/drm/card*-DP-*/; do
  [ -e "$d/dpms" ] || continue
  [ "$(cat "$d/status" 2>/dev/null)" = "connected" ] || continue
  found=1
  echo "{action}" | sudo -n tee "$d/dpms" >/dev/null
  echo "$(basename "$d"): $(cat "$d/dpms")"
done
if [ "$found" = "0" ]; then
  echo "ingen tilsluttede DP-udgange fundet under /sys/class/drm" >&2
  exit 3
fi
"""

_STATUS_SHELL = r"""
found=0
for d in /sys/class/drm/card*-DP-*/; do
  [ -e "$d/dpms" ] || continue
  st="$(cat "$d/status" 2>/dev/null)"
  [ "$st" = "connected" ] || continue
  found=1
  echo "$(basename "$d"): status=$st dpms=$(cat "$d/dpms")"
done
if [ "$found" = "0" ]; then
  echo "ingen tilsluttede DP-udgange fundet under /sys/class/drm" >&2
  exit 3
fi
"""

#: Fallback for off/standby. Locks the session — see module docstring.
_DBUS_FALLBACK = (
    "XDG_RUNTIME_DIR=/run/user/1000 "
    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
    "gdbus call --session --dest org.gnome.ScreenSaver "
    "--object-path /org/gnome/ScreenSaver "
    "--method org.gnome.ScreenSaver.SetActive true"
)


def _dpms_command(action: str) -> str:
    """Shell command that sets (or reads) DPMS on every connected DP output."""
    if action == "status":
        return _STATUS_SHELL
    return _DPMS_SHELL.format(action=action)


def _run_on_operator(command: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run `command` on the operator's desktop via the bridge.

    Returns the bridge payload ({stdout, stderr, exit_code, …}) on success, or
    ``{"error": …}`` with an honest reason when the bridge cannot be reached.
    """
    # Lazy imports: simple_tools imports this module at module level, and the
    # canonical (patchable) helpers live there — see the §4 monkeypatch seam.
    from core.tools.simple_tools import _operator_user_id, _run_operator_async

    user_id = _operator_user_id(args)

    async def _do() -> dict[str, Any]:
        from core.tools.operator_tools import operator_bash_async

        return await operator_bash_async(
            command=command,
            user_id=user_id,
            timeout_s=_COMMAND_TIMEOUT_S,
            # No approval dialog: the action is a screen power state, and a
            # prompt would have to be answered on the very screen being turned
            # off. The bridge auto-rejects after 20s anyway, so a dialog would
            # make "off" fail whenever Bjørn is away from the desk.
            skip_approval=True,
        )

    result = _run_operator_async(_do, tool_name="screen_control", timeout_s=_BRIDGE_TIMEOUT_S)
    if result.get("status") != "ok":
        return {"error": str(result.get("error") or "ukendt bro-fejl")}
    return result.get("result") or {}


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

    payload = _run_on_operator(_dpms_command(action), args)

    if payload.get("error"):
        return {
            "status": "error",
            "action": action,
            "text": (
                f"Kunne ikke nå Bjørns maskine: {payload['error']}. "
                "screen_control kører via JarvisX-broen — den skal være forbundet. "
                "(xset er ikke en vej: sessionen er Wayland uden DPMS-extension.)"
            ),
        }

    exit_code = payload.get("exit_code")
    stdout = str(payload.get("stdout") or "").strip()
    stderr = str(payload.get("stderr") or "").strip()

    if exit_code == 3:
        # sysfs found nothing to act on. For off/standby, try the D-Bus path.
        if action in ("off", "standby"):
            fallback = _run_on_operator(_DBUS_FALLBACK, args)
            if not fallback.get("error") and fallback.get("exit_code") == 0:
                return {
                    "status": "ok",
                    "action": action,
                    "text": (
                        "Ingen tilsluttede DP-udgange fundet — brugte GNOME D-Bus i stedet. "
                        "BEMÆRK: den låser sessionen."
                    ),
                }
        return {
            "status": "error",
            "action": action,
            "text": stderr or "Ingen tilsluttede DP-udgange fundet under /sys/class/drm.",
        }

    if exit_code != 0:
        return {
            "status": "error",
            "action": action,
            "text": f"DPMS-kommando fejlede (exit {exit_code}): {stderr or stdout or 'ingen output'}",
        }

    if action == "status":
        text = stdout or "Ingen tilsluttede DP-udgange fundet."
    else:
        text = f"Skærm-handling '{action}' udført.\n{stdout}" if stdout else f"Skærm-handling '{action}' udført."

    result: dict[str, Any] = {"status": "ok", "action": action, "text": text}

    # Egress-fri Central-observation (§24.4): Jarvis HANDLER på den fysiske verden
    # (tænder/slukker Bjørns skærme). Kun handlings-label + ok-flag. Self-safe.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "channel", "screen_control",
            value=1.0,
            meta={"action": str(action), "ok": result.get("status") == "ok"},
            reason="physical action",
        )
    except Exception:
        pass
    return result


SCREEN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "screen_control",
            "description": (
                "Control the desktop monitors: turn them on, off, or "
                "standby, or query their current state with 'status'. "
                "Use 'screen_control action=off' to turn screens off, "
                "'screen_control action=on' to wake them. "
                "Kører på Bjørns maskine via JarvisX-broen (sysfs-DPMS). "
                "Kræver at broen er forbundet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["on", "off", "standby", "status"],
                        "description": (
                            "What to do: 'off' = sluk skærme (DPMS off), "
                            "'on' = tænd, 'standby' = strømspare, "
                            "'status' = læs nuværende tilstand."
                        ),
                    },
                },
                "required": ["action"],
            },
        },
    },
]
