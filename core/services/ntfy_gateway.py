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


def _default_title() -> str:
    # Lazy import so callers can pass a custom title without dragging
    # identity_composer in. Mutable default ("Jarvis") would never update
    # if the entity renames itself, so we resolve at call time.
    try:
        from core.services.identity_composer import get_entity_name
        return get_entity_name()
    except Exception:
        return "Jarvis"


def send_notification(
    message: str,
    title: str | None = None,
    priority: str = "default",
    tags: list[str] | None = None,
) -> dict:
    """Send a push notification via ntfy. Returns status dict.

    priority: min / low / default / high / urgent
    tags: ntfy emoji tags e.g. ["robot", "bell"]
    """
    # ── Notification-hook ────────────────────────────────────────────────
    # Foer beskeden sendes: `block` betyder send den ikke. Bagefter er den ude
    # af huset og kan ikke kaldes tilbage — det er her dommen kan gaelde.
    # `inject` haefter tekst paa, saa en hook kan tilfoeje kontekst til det der
    # naar telefonen.
    try:
        from core.services import lifecycle_hooks as _lh_n
        if "Notification" in _lh_n.WIRED_EVENTS and _lh_n.hooks_for("Notification"):
            _d = _lh_n.fire("Notification", {
                "message": str(message or "")[:2000],
                "title": str(title or ""), "priority": str(priority or "")})
            if _d.get("action") == "block":
                return {"status": "blocked",
                        "reason": str(_d.get("message") or "blokeret af hook")}
            if _d.get("action") == "inject" and _d.get("message"):
                message = f"{message}\n\n{_d['message']}"
    except Exception:
        pass

    cfg = _load_config()
    if not cfg:
        return {"status": "error", "reason": "ntfy-not-configured"}

    url = f"{cfg['server']}/{cfg['topic']}"
    resolved_title = title if title is not None else _default_title()
    headers = {
        "Title": resolved_title,
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
