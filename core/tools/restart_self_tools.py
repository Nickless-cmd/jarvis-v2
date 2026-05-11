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

    # Missing return on success path was crashing visible-run pipeline
    # (None returned to execute_tool_force which called .get() on it).
    # Fixed 2026-05-09 — Jarvis got stuck in a 6-call retry loop trying
    # to restart himself because each call crashed before returning.
    return {
        "status": "ok",
        "scheduled": True,
        "services": services,
        "pid": proc.pid,
        "delay_seconds": 3,
        "channel": channel,
    }


def _try_send_with_retry(base_msg: str, max_wait: float = 10.0, interval: float = 1.0) -> bool:
    """Forsøg at sende DM, med retry hvis gateway ikke er connected endnu.

    Gateway'en startes asynkront i en baggrundstråd under startup — vi ved
    ikke præcis hvornår den er connected. I stedet for at polle en stale
    status, prøver vi rent faktisk at sende og tjekker om fejlen er
    "discord-not-connected". Hvis ja: vent og prøv igen.
    """
    from core.services.discord_gateway import send_dm_to_owner
    from core.services.discord_config import load_discord_config

    cfg = load_discord_config()
    if not cfg:
        logger.info("restart confirmation (no discord config): %s", base_msg)
        return True  # ikke konfigureret = ikke en fejl

    start = time.monotonic()
    last_error = None
    while time.monotonic() - start < max_wait:
        result = send_dm_to_owner(base_msg)
        if isinstance(result, dict):
            status = result.get("status", "")
            if status == "ok":
                logger.info("restart confirmation: sent successfully")
                return True
            reason = result.get("reason", "ukendt")
            last_error = reason
            if "not-connected" in reason or "not connected" in reason:
                # Gateway er stadig ved at connecte — vent og prøv igen
                logger.info("restart confirmation: gateway not ready yet (%s), retrying...", reason)
                time.sleep(interval)
                continue
            # Anden fejl — ikke noget at vente på
            logger.warning("restart confirmation: send failed (non-retryable): %s", reason)
            return False
        # Ikke-dict svar = sandsynligvis gammel API der returnerer None
        return True

    logger.warning("restart confirmation: gateway not connected after %.1fs (last: %s)", max_wait, last_error)
    return False


def send_pending_restart_confirmation() -> None:
    """On startup, check for a pending restart confirmation file and send it.

    Problemet før: send_dm_to_owner blev kaldt før Discord gateway'en var
    færdig med at connecte (= silent failure — returværdi ignoreret).
    Nu:
    - Retry-loop: prøver at sende, og hvis gateway ikke er klar ventes der
    - Op til 10 sekunder med 1s interval
    - Hvis stadig ikke sendt: behold filen (op til 3 restarts)
    - Returværdi tjekkes altid — silent failure er væk
    """
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
    retries = data.get("retries", 0)

    base_msg = custom_message or f"Restart af {', '.join(services)} gennemført — jeg er tilbage."

    try:
        if channel == "telegram":
            from core.services.telegram_gateway import send_telegram_message
            result = send_telegram_message(base_msg)
            sent_ok = isinstance(result, dict) and result.get("status") == "ok"
            if sent_ok:
                PENDING_RESTART_FILE.unlink(missing_ok=True)
            else:
                logger.warning("restart confirmation: telegram send failed: %s", result)
        else:
            sent_ok = _try_send_with_retry(base_msg, max_wait=10.0, interval=1.0)
            if sent_ok:
                PENDING_RESTART_FILE.unlink(missing_ok=True)
            else:
                # Gem filen til næste startup (med retry-tæller)
                if retries < 3:
                    data["retries"] = retries + 1
                    PENDING_RESTART_FILE.write_text(json.dumps(data, indent=2))
                    logger.info(
                        "restart confirmation: kept file for retry %d/3",
                        retries + 1,
                    )
                else:
                    logger.error("restart confirmation: max retries (3) reached — deleting file")
                    PENDING_RESTART_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.warning("restart confirmation: unexpected error: %s", e)
