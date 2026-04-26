"""Pinned monitors — Jarvis' equivalent of Claude Code's Monitor tool.

Claude Code's Monitor streams stdout lines from a long-running script and
fires a notification per line. Jarvis can't be interrupted between turns
the same way, but he can do the closest equivalent: pin a watcher on a
source (eventbus family or log file), and at next prompt build, surface
any new lines that matched since the previous turn.

Sources supported:
- ``eventbus:<family>``  — event whose kind starts with <family>.
- ``file:<absolute-path>``  — new lines appended since the last check
                              (tail-style; respects log rotation by
                              re-opening if size shrunk).

State per monitor:
- monitor_id, source, pattern (optional regex), label, session_id,
  last_event_id (for eventbus), last_size (for file), created_at.

Per session so they don't bleed. Persisted via state_store.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "monitor_streams"
_MAX_PER_SESSION = 5
_MAX_MATCHES_PER_DIGEST = 6
_MAX_LINE_LENGTH = 240


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(monitors: dict[str, dict[str, Any]]) -> None:
    save_json(_STATE_KEY, monitors)


def _session_monitors(session_id: str | None) -> list[dict[str, Any]]:
    sid = str(session_id or "_default")
    return [m for m in _load().values() if m.get("session_id") == sid]


def open_monitor(
    *, session_id: str | None, source: str, label: str = "", pattern: str = ""
) -> dict[str, Any]:
    sid = str(session_id or "_default")
    source = (source or "").strip()
    if not source or ":" not in source:
        return {"status": "error", "error": "source must be 'eventbus:<family>' or 'file:<path>'"}
    kind = source.split(":", 1)[0]
    if kind not in {"eventbus", "file"}:
        return {"status": "error", "error": f"unsupported source kind: {kind}"}
    if kind == "file":
        path = source[len("file:"):]
        if not os.path.isabs(path):
            return {"status": "error", "error": "file path must be absolute"}
    if pattern:
        try:
            re.compile(pattern)
        except re.error as exc:
            return {"status": "error", "error": f"invalid regex: {exc}"}

    existing = _session_monitors(sid)
    if len(existing) >= _MAX_PER_SESSION:
        return {
            "status": "error",
            "error": f"max {_MAX_PER_SESSION} monitors per session — close one first",
        }

    monitor_id = f"mon-{uuid4().hex[:10]}"
    rec: dict[str, Any] = {
        "monitor_id": monitor_id,
        "session_id": sid,
        "source": source,
        "label": label or source,
        "pattern": pattern,
        "created_at": datetime.now(UTC).isoformat(),
        "last_event_id": 0,
        "last_size": 0,
    }
    if source.startswith("file:"):
        path = source[len("file:"):]
        try:
            rec["last_size"] = os.path.getsize(path) if os.path.exists(path) else 0
        except OSError:
            rec["last_size"] = 0
    elif source.startswith("eventbus:"):
        try:
            from core.eventbus.bus import event_bus
            recent = event_bus.recent(limit=1)
            if recent:
                rec["last_event_id"] = int(recent[0].get("id") or 0)
        except Exception:
            pass

    monitors = _load()
    monitors[monitor_id] = rec
    _save(monitors)
    return {"status": "ok", "monitor_id": monitor_id, "source": source, "label": rec["label"]}


def close_monitor(monitor_id: str) -> dict[str, Any]:
    monitors = _load()
    if monitor_id not in monitors:
        return {"status": "error", "error": f"unknown monitor_id {monitor_id}"}
    rec = monitors.pop(monitor_id)
    _save(monitors)
    return {"status": "ok", "closed": monitor_id, "source": rec.get("source")}


def list_monitors(session_id: str | None) -> list[dict[str, Any]]:
    return _session_monitors(session_id)


def _drain_eventbus(rec: dict[str, Any]) -> list[str]:
    family = rec["source"].split(":", 1)[1].strip()
    pat = re.compile(rec.get("pattern") or ".*")
    try:
        from core.eventbus.bus import event_bus
        last_id = int(rec.get("last_event_id") or 0)
        recent = (
            event_bus.recent_since_id(last_id, limit=200) if last_id > 0
            else event_bus.recent(limit=50)
        )
    except Exception as exc:
        logger.debug("monitor: eventbus fetch failed: %s", exc)
        return []
    out: list[str] = []
    newest = last_id
    for ev in recent:
        kind = str(ev.get("kind", ""))
        if family and not kind.startswith(family):
            continue
        ev_id = int(ev.get("id") or 0)
        if ev_id > newest:
            newest = ev_id
        payload = ev.get("payload") or {}
        detail = ""
        if isinstance(payload, dict):
            for key in ("message", "summary", "error", "tool", "kind"):
                v = payload.get(key)
                if v:
                    detail = str(v)[:120]
                    break
        line = f"{kind} {detail}".strip()
        if pat.search(line):
            ts = str(ev.get("created_at", ""))[11:19]
            out.append(f"[{ts}] {line[:_MAX_LINE_LENGTH]}")
    rec["last_event_id"] = newest
    return out


def _drain_file(rec: dict[str, Any]) -> list[str]:
    path = rec["source"][len("file:"):]
    pat = re.compile(rec.get("pattern") or ".*")
    if not os.path.exists(path):
        return []
    try:
        size_now = os.path.getsize(path)
    except OSError:
        return []
    last_size = int(rec.get("last_size") or 0)
    if size_now < last_size:
        # File rotated/truncated — start over from the top.
        last_size = 0
    if size_now == last_size:
        return []
    out: list[str] = []
    try:
        with open(path, "rb") as fh:
            fh.seek(last_size)
            new_data = fh.read(64 * 1024)  # cap per drain
    except OSError:
        return []
    rec["last_size"] = last_size + len(new_data)
    text = new_data.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if pat.search(line):
            out.append(line[:_MAX_LINE_LENGTH])
    return out


def monitor_digest_section(session_id: str | None) -> str | None:
    """Format new matches across all this session's monitors. Side effect:
    advances last_event_id / last_size so each match is shown once."""
    monitors_by_id = _load()
    sid = str(session_id or "_default")
    blocks: list[str] = []
    dirty = False
    for mid, rec in list(monitors_by_id.items()):
        if rec.get("session_id") != sid:
            continue
        try:
            if rec.get("source", "").startswith("eventbus:"):
                matches = _drain_eventbus(rec)
            elif rec.get("source", "").startswith("file:"):
                matches = _drain_file(rec)
            else:
                matches = []
        except Exception as exc:
            logger.debug("monitor %s drain failed: %s", mid, exc)
            matches = []
        dirty = True  # last_event_id / last_size may have been touched
        if not matches:
            continue
        capped = matches[:_MAX_MATCHES_PER_DIGEST]
        label = str(rec.get("label") or rec.get("source") or "monitor")
        bullets = "\n".join(f"- {m}" for m in capped)
        blocks.append(f"📡 {label} ({len(matches)} match{'es' if len(matches) != 1 else ''}):\n{bullets}")
    if dirty:
        _save(monitors_by_id)
    if not blocks:
        return None
    return "Pinnede monitor-fund (siden sidste tur):\n" + "\n\n".join(blocks)
