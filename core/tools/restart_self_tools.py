"""restart_self tool — fire-and-forget service restart that survives process death.

Design:
1. Write a pending confirmation file with channel/context info
2. Schedule the restart via a detached subprocess (sleep + systemctl restart)
3. On next boot, the startup hook in app.py reads the file and sends a confirmation

The tool returns immediately after scheduling — it does NOT wait for the restart.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

PENDING_RESTART_FILE = Path(JARVIS_HOME) / "state" / "pending_restart_confirmation.json"

ALLOWED_SERVICES = {"jarvis-api", "jarvis-runtime"}

RESTART_SELF_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "restart_self",
            "description": (
                "Restart Jarvis' own backend services (api + runtime) in a way that "
                "survives the process death. Writes a pending confirmation, schedules "
                "the restart via a detached subprocess, and returns immediately. "
                "After reboot, a startup hook sends a confirmation message. "
                "USE WITH CARE — this kills your current session."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "services": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Service names to restart. Default: ['jarvis-api', 'jarvis-runtime']",
                        "default": ["jarvis-api", "jarvis-runtime"],
                    },
                    "channel": {
                        "type": "string",
                        "description": "Channel for confirmation after restart (discord, telegram, webchat). Default: discord",
                        "default": "discord",
                    },
                    "message": {
                        "type": "string",
                        "description": "Custom confirmation message. Default: auto-generated.",
                        "default": "",
                    },
                },
                "required": [],
            },
        },
    }
]


def _exec_restart_self(args: dict[str, Any]) -> dict[str, Any]:
    services = args.get("services") or ["jarvis-api", "jarvis-runtime"]
    channel = args.get("channel") or "discord"
    custom_message = args.get("message") or ""

    # Validate — only allow known Jarvis services
    services = [s for s in services if s in ALLOWED_SERVICES]
    if not services:
        return {
            "status": "error",
            "error": "No valid services. Allowed: jarvis-api, jarvis-runtime",
        }

    # 1. Write pending confirmation file
    confirmation = {
        "timestamp": time.time(),
        "services": services,
        "channel": channel,
        "custom_message": custom_message,
    }
    PENDING_RESTART_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_RESTART_FILE.write_text(json.dumps(confirmation, indent=2))
    logger.info("restart_self: wrote confirmation to %s", PENDING_RESTART_FILE)

    # 2. Build restart command with a short delay so response can reach user first
    restart_cmds = " && ".join(f"sudo systemctl restart {svc}" for svc in services)
    full_cmd = f"sleep 3 && {restart_cmds}"

    # 3. Fire-and-forget via detached subprocess
    try:
        proc = subprocess.Popen(
            ["bash", "-c", full_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from current process group
        )
        logger.info("restart_self: scheduled restart via detached process pid=%s", proc.pid)
    except Exception as e:
        PENDING_RESTART_FILE.unlink(missing_ok=True)
        return {"status": "error", "error": f"Failed to schedule restart: {e}"}



def send_pending_restart_confirmation() -> None:
    """On startup, check for a pending restart confirmation file and send it."""
    if not PENDING_RESTART_FILE.exists():
        return

    try:
        data = json.loads(PENDING_RESTART_FILE.read_text())
    except Exception as e:
        logger.warning("restart confirmation: failed to read file: %s", e)
        PENDING_RESTART_FILE.unlink(missing_ok=True)
        return

    channel = data.get("channel", "discord")
    custom_message = data.get("custom_message", "")
    services = data.get("services", [])

    base_msg = custom_message or f"Restart af {', '.join(services)} gennemført — jeg er tilbage."

    try:
        if channel == "telegram":
            from core.services.telegram_gateway import send_telegram_message
            send_telegram_message(base_msg)
        else:
            from core.services.discord_gateway import send_discord_message
            from core.services.discord_config import load_discord_config
            cfg = load_discord_config()
            ch_id = cfg.get("owner_discord_id") if cfg else None
            if ch_id:
                send_discord_message(int(ch_id), base_msg)
            else:
                logger.info("restart confirmation (no channel configured): %s", base_msg)
    except Exception as e:
        logger.warning("restart confirmation: failed to send: %s", e)
    finally:
        PENDING_RESTART_FILE.unlink(missing_ok=True)
