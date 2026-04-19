"""Telegram gateway — send messages to owner via Telegram Bot API."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_KEYS = ("telegram_bot_token", "telegram_chat_id")


def _load_config() -> dict | None:
    try:
        cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        if all(data.get(k) for k in _CONFIG_KEYS):
            return {"token": data["telegram_bot_token"], "chat_id": str(data["telegram_chat_id"])}
    except Exception:
        pass
    return None


def is_configured() -> bool:
    return _load_config() is not None


def send_message(text: str, parse_mode: str = "") -> dict:
    """Send a message to the owner via Telegram. Returns status dict."""
    cfg = _load_config()
    if not cfg:
        return {"status": "error", "reason": "telegram-not-configured"}

    token = cfg["token"]
    chat_id = cfg["chat_id"]
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                msg_id = result.get("result", {}).get("message_id")
                return {"status": "sent", "message_id": msg_id}
            return {"status": "error", "reason": str(result.get("description", "unknown"))}
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        logger.warning("telegram_gateway: HTTP %s — %s", exc.code, body_err)
        return {"status": "error", "reason": f"http-{exc.code}: {body_err[:200]}"}
    except Exception as exc:
        logger.warning("telegram_gateway: send failed: %s", exc)
        return {"status": "error", "reason": str(exc)}
