"""Telegram gateway — bidirectional messaging via Telegram Bot API.

Outbound: send_message() — HTTP POST, no daemon needed.
Inbound:  start_telegram_gateway() — long-poll loop in background thread.
          Incoming messages trigger start_autonomous_run() and responses
          are routed back via the eventbus subscriber.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("uvicorn.error")

_CONFIG_KEYS = ("telegram_bot_token", "telegram_chat_id")

# Sessions: {session_id → chat_id}
_telegram_sessions: dict[str, int] = {}
_telegram_sessions_lock = threading.Lock()

_thread: threading.Thread | None = None
_sub_thread: threading.Thread | None = None
_sub_running: bool = False
_poll_running: bool = False

_status: dict[str, Any] = {
    "connected": False,
    "last_message_at": None,
    "message_count": 0,
    "error": None,
}


# ── Config ─────────────────────────────────────────────────────────────

def _load_config() -> dict | None:
    try:
        cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        if all(data.get(k) for k in _CONFIG_KEYS):
            return {
                "token": data["telegram_bot_token"],
                "chat_id": str(data["telegram_chat_id"]),
            }
    except Exception:
        pass
    return None


def is_configured() -> bool:
    return _load_config() is not None


def get_status() -> dict[str, Any]:
    return {**_status, "active_sessions": len(_telegram_sessions)}


# ── Outbound ───────────────────────────────────────────────────────────

def _api(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def send_message(text: str, chat_id: str | int | None = None, parse_mode: str = "") -> dict:
    """Send a message to owner (or specific chat_id). Returns status dict."""
    cfg = _load_config()
    if not cfg:
        return {"status": "error", "reason": "telegram-not-configured"}

    target = str(chat_id) if chat_id else cfg["chat_id"]
    payload: dict = {"chat_id": target, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        result = _api(cfg["token"], "sendMessage", payload)
        if result.get("ok"):
            return {"status": "sent", "message_id": result.get("result", {}).get("message_id")}
        return {"status": "error", "reason": str(result.get("description", "unknown"))}
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "reason": f"http-{exc.code}: {body_err[:200]}"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


# ── Session management ─────────────────────────────────────────────────

def _get_or_create_session(chat_id: int) -> str:
    from core.services.chat_sessions import create_chat_session, list_chat_sessions
    title = "Telegram DM"
    for s in list_chat_sessions():
        if s.get("title") == title:
            return str(s["id"])
    return str(create_chat_session(title=title)["id"])


# ── Inbound poll loop ──────────────────────────────────────────────────

def _poll_loop(token: str, owner_chat_id: str) -> None:
    global _poll_running
    offset = 0
    _status["connected"] = True
    _status["error"] = None
    logger.info("telegram_gateway: poll loop started")

    while _poll_running:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=25&offset={offset}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

            if not data.get("ok"):
                logger.warning("telegram_gateway: getUpdates not ok: %s", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or update.get("edited_message")
                if not msg:
                    continue

                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()

                # Only accept messages from owner
                if str(chat_id) != owner_chat_id or not text:
                    continue

                logger.info("telegram_gateway: inbound from owner: %r", text[:80])
                _status["message_count"] += 1
                _status["last_message_at"] = msg.get("date")

                session_id = _get_or_create_session(chat_id)
                with _telegram_sessions_lock:
                    _telegram_sessions[session_id] = chat_id

                from core.services.chat_sessions import append_chat_message
                append_chat_message(session_id=session_id, role="user", content=text)

                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("telegram.message_received", {
                        "chat_id": str(chat_id),
                        "text": text[:200],
                    })
                except Exception:
                    pass

                from core.services.visible_runs import start_autonomous_run
                threading.Thread(
                    target=start_autonomous_run,
                    args=(text,),
                    kwargs={"session_id": session_id},
                    daemon=True,
                    name=f"telegram-run-{session_id[-8:]}",
                ).start()

        except Exception as exc:
            if _poll_running:
                logger.warning("telegram_gateway: poll error: %s", exc)
                _status["error"] = str(exc)
                time.sleep(5)

    _status["connected"] = False
    logger.info("telegram_gateway: poll loop stopped")


# ── Eventbus subscriber — route responses back to Telegram ─────────────

def _eventbus_subscriber_loop() -> None:
    """Buffer assistant responses per session, flush when run completes."""
    import queue
    from core.eventbus.bus import event_bus
    sub = event_bus.subscribe()
    _pending: dict[str, tuple[int, str]] = {}
    try:
        while _sub_running:
            try:
                item = sub.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break
            if not isinstance(item, dict):
                continue
            kind = item.get("kind", "")
            payload = item.get("payload") or {}

            if kind == "channel.chat_message_appended":
                session_id = str(payload.get("session_id") or "")
                with _telegram_sessions_lock:
                    chat_id = _telegram_sessions.get(session_id)
                if chat_id is None:
                    continue
                source = str(payload.get("source") or "")
                if source and source != "visible-run":
                    continue
                msg = payload.get("message") or {}
                if str(msg.get("role") or "") != "assistant":
                    continue
                content = str(msg.get("content") or "").strip()
                if content:
                    logger.info("telegram_sub: buffering reply session=%s chat_id=%s len=%d", session_id[:12], chat_id, len(content))
                    _pending[session_id] = (chat_id, content)

            elif kind in ("runtime.autonomous_run_completed", "memory.visible_run_postprocess_completed"):
                session_id = str(payload.get("session_id") or "")
                pending = _pending.pop(session_id, None)
                if pending:
                    chat_id, content = pending
                    logger.info("telegram_sub: flushing to chat_id=%s len=%d (trigger=%s)", chat_id, len(content), kind)
                    try:
                        result = send_message(content, chat_id=chat_id)
                        logger.info("telegram_sub: send result=%s", result.get("status"))
                    except Exception as exc:
                        logger.error("telegram_sub: send error: %s", exc)
                else:
                    logger.debug("telegram_sub: %s sid=%s — no pending", kind.split(".")[-1], session_id[:12])
    finally:
        logger.warning("telegram_sub: subscriber loop exited")
        event_bus.unsubscribe(sub)


# ── Lifecycle ──────────────────────────────────────────────────────────

def start_telegram_gateway() -> None:
    global _thread, _sub_thread, _sub_running, _poll_running

    cfg = _load_config()
    if not cfg:
        logger.info("telegram_gateway: not configured, skipping")
        return

    if _thread and _thread.is_alive():
        logger.info("telegram_gateway: already running")
        return

    _sub_running = True
    _sub_thread = threading.Thread(
        target=_eventbus_subscriber_loop,
        daemon=True,
        name="telegram-sub",
    )
    _sub_thread.start()

    _poll_running = True
    _thread = threading.Thread(
        target=_poll_loop,
        args=(cfg["token"], cfg["chat_id"]),
        daemon=True,
        name="telegram-gateway",
    )
    _thread.start()
    logger.info("telegram_gateway: started (owner_chat_id=%s)", cfg["chat_id"])


def stop_telegram_gateway() -> None:
    global _poll_running, _sub_running
    _poll_running = False
    _sub_running = False
    logger.info("telegram_gateway: stopping")
