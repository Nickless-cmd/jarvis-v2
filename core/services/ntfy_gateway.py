"""Ntfy gateway — send push notifications via ntfy.sh or self-hosted server."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_config() -> dict | None:
    try:
        cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        topic = data.get("ntfy_topic")
        server = data.get("ntfy_server", "https://ntfy.sh").rstrip("/")
        if topic:
            return {"server": server, "topic": topic}
    except Exception:
        pass
    return None


def is_configured() -> bool:
    return _load_config() is not None


def send_notification(
    message: str,
    title: str = "Jarvis",
    priority: str = "default",
    tags: list[str] | None = None,
) -> dict:
    """Send a push notification via ntfy. Returns status dict.

    priority: min / low / default / high / urgent
    tags: ntfy emoji tags e.g. ["robot", "bell"]
    """
    cfg = _load_config()
    if not cfg:
        return {"status": "error", "reason": "ntfy-not-configured"}

    url = f"{cfg['server']}/{cfg['topic']}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)

    body = message.encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return {"status": "sent", "topic": cfg["topic"]}
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        logger.warning("ntfy_gateway: HTTP %s — %s", exc.code, body_err)
        return {"status": "error", "reason": f"http-{exc.code}: {body_err[:200]}"}
    except Exception as exc:
        logger.warning("ntfy_gateway: send failed: %s", exc)
        return {"status": "error", "reason": str(exc)}
