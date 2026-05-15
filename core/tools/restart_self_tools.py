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
import os
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


def _wait_for_gateway_connected(max_wait: float = 40.0, interval: float = 2.0) -> bool:
    """Vent på at Discord gateway er connected efter restart.

    Gateway'en startes i en baggrundstråd under lifespan startup og tager
    typisk 5-20s at connecte (on_ready). I stedet for at prøve at sende
    og tjekke fejl, venter vi på at get_discord_status() rapporterer
    connected=True. Dette er mere robust fordi:
    - Ingen afhængighed af runtime process (som måske genstartes)
    - Læser direkte fra gateway-thread'ens _status dict i samme proces
    - 40s timeout giver god margin til Discord rate limits
    """
    from core.services.discord_gateway import get_discord_status

    start = time.monotonic()
    while time.monotonic() - start < max_wait:
        status = get_discord_status()
        if status.get("connected") and not status.get("stale"):
            elapsed = time.monotonic() - start
            logger.info("restart confirmation: discord connected after %.1fs", elapsed)
            return True
        time.sleep(interval)

    logger.warning("restart confirmation: discord NOT connected after %.1fs", max_wait)
    return False


def _send_discord_restart_msg(base_msg: str) -> bool:
    """Send restart-bekræftelse til Bjørn via Discord DM.

    Discord gateway skal være connected før kald — _wait_for_gateway_connected
    skal returnere True først.
    """
    from core.services.discord_gateway import send_dm_to_owner

    try:
        result = send_dm_to_owner(base_msg, timeout=15.0)
        if isinstance(result, dict) and result.get("status") in ("ok", "sent"):
            logger.info("restart confirmation: discord DM sent successfully")
            return True
        reason = result.get("reason", "ukendt") if isinstance(result, dict) else str(result)
        logger.warning("restart confirmation: discord DM failed: %s", reason)
        return False
    except Exception as exc:
        logger.warning("restart confirmation: discord DM exception: %s", exc)
        return False


def _try_fallback_channels(base_msg: str) -> bool:
    """Forsøg at sende restart-bekræftelse via Telegram eller ntfy som fallback.

    Kaldes når Discord gateway ikke kunne connecte eller sende.
    """
    # Forsøg Telegram
    try:
        from core.services.telegram_gateway import send_message as tg_send
        result = tg_send(base_msg)
        if isinstance(result, dict) and result.get("status") == "sent":
            logger.info("restart confirmation: sent via Telegram fallback")
            return True
        logger.info("restart confirmation: Telegram fallback failed: %s", result)
    except Exception as exc:
        logger.info("restart confirmation: Telegram fallback exception: %s", exc)

    # Forsøg ntfy push notifikation
    try:
        from core.services.ntfy_gateway import send_notification as ntfy_send
        result = ntfy_send(
            message=base_msg,
            title="Jarvis genstartet",
            priority="high",
            tags=["white_check_mark", "robot"],
        )
        if isinstance(result, dict) and result.get("status") == "ok":
            logger.info("restart confirmation: sent via ntfy fallback")
            return True
        reason = result.get("reason", "ukendt") if isinstance(result, dict) else str(result)
        logger.info("restart confirmation: ntfy fallback failed: %s", reason)
    except Exception as exc:
        logger.info("restart confirmation: ntfy fallback exception: %s", exc)

    return False


def _claim_restart_file() -> Path | None:
    """Atomic claim af restart-confirmation-fil — kun én uvicorn worker vinder.

    Brug: når jarvis-api kører med --workers 4, vil 4 worker-processer hver
    kalde send_pending_restart_confirmation ved startup. Uden en claim-mekanisme
    sender alle 4 beskeden uafhængigt (= duplikater).

    Løsning: atomisk rename via os.rename(). Den worker der først får lov at
    omdøbe filen til .claimed, vinder. Resten ser den ikke længere på den
    oprindelige sti og afbryder stille.

    Returns: stien til den claimede fil (skal slettes af kaldende worker),
    eller None hvis en anden worker allerede har claimet.
    """
    if not PENDING_RESTART_FILE.exists():
        return None

    claimed_path = PENDING_RESTART_FILE.with_name(
        f"pending_restart_confirmation.{os.getpid()}.claimed.json"
    )
    try:
        os.rename(str(PENDING_RESTART_FILE), str(claimed_path))
    except FileNotFoundError:
        return None  # En anden worker nåede først
    except OSError:
        return None  # Race tabt

    logger.info("restart confirmation: claimed file as pid=%s", os.getpid())
    return claimed_path


def send_pending_restart_confirmation() -> None:
    """On startup, check for a pending restart confirmation file and send it.

    Flow:
    0. Atomisk claim af filen (kun én uvicorn worker vinder)
    1. Discord: vent på gateway connected (op til 40s) → send DM
    2. Hvis Discord fejler: prøv Telegram fallback
    3. Hvis Telegram også fejler: prøv ntfy push notifikation
    4. Hvis alt fejler: behold filen med retry-tæller (max 3)
    5. Filen slettes KUN når en kanal har sendt succesfuldt

    Problemet før: send_dm_to_owner blev kaldt før Discord gateway'en var
    færdig med at connecte (= silent failure). Nu venter vi på connected
    status før vi prøver at sende, med op til 40s margin.
    """
    # Step 0: Atomic claim — kun én worker fortsætter
    claimed_path = _claim_restart_file()
    if claimed_path is None:
        return  # En anden worker klarer det

    try:
        data = json.loads(claimed_path.read_text())
    except Exception as e:
        logger.warning("restart confirmation: failed to read claimed file: %s", e)
        claimed_path.unlink(missing_ok=True)
        return

    channel = data.get("channel", "discord")
    custom_message = data.get("custom_message", "")
    services = data.get("services", [])
    retries = data.get("retries", 0)

    base_msg = custom_message or f"Restart af {', '.join(services)} gennemført — jeg er tilbage."

    sent_ok = False

    try:
        if channel == "telegram":
            from core.services.telegram_gateway import send_message as tg_send
            result = tg_send(base_msg)
            sent_ok = isinstance(result, dict) and result.get("status") == "sent"
            if not sent_ok:
                logger.warning("restart confirmation: telegram failed: %s", result)
        else:
            if _wait_for_gateway_connected(max_wait=40.0, interval=2.0):
                sent_ok = _send_discord_restart_msg(base_msg)
            else:
                logger.warning("restart confirmation: discord gateway not ready, trying fallbacks")

            if not sent_ok:
                logger.info("restart confirmation: trying fallback channels...")
                sent_ok = _try_fallback_channels(base_msg)

        if sent_ok:
            claimed_path.unlink(missing_ok=True)
            logger.info("restart confirmation: claimed file deleted — confirmation sent")
        else:
            if retries < 3:
                data["retries"] = retries + 1
                # Genopret filen på den oprindelige sti til næste startup
                try:
                    PENDING_RESTART_FILE.write_text(json.dumps(data, indent=2))
                    logger.info(
                        "restart confirmation: recreated file for retry %d/3",
                        retries + 1,
                    )
                except Exception as _write_err:
                    logger.warning("restart confirmation: failed to recreate retry file: %s", _write_err)
                claimed_path.unlink(missing_ok=True)
            else:
                logger.error(
                    "restart confirmation: max retries (3) reached — "
                    "confirmation never sent. Deleting file."
                )
                claimed_path.unlink(missing_ok=True)

    except Exception as e:
        logger.warning("restart confirmation: unexpected error: %s", e)
        claimed_path.unlink(missing_ok=True)
