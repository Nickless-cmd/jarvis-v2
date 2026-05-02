"""Process watcher — push-notification primitive for Jarvis.

Closes the gap noted by Bjørn: Jarvis already has wakeups (pull), but
no native "tell me when X happens" (push). This module adds it.

A `Watch` is a named set of conditions on a process or state-file.
A daemon thread evaluates every 10s. When a condition matches, the
watch fires its on_match action: push_initiative, self_wakeup,
notify_owner, or eventbus_publish.

Conditions (discriminated by `kind`):
  process_died          — process_name's status flips to exited/lost
  log_pattern           — process log tail matches regex
  state_field_threshold — JSON state-file's nested field crosses op/value
  state_field_change    — JSON state-file's field flips between values
  state_stale           — state file hasn't been written for max_age_seconds
  state_list_grew       — JSON state-file's array grew (e.g. recent_trades)

Actions (`on_match`):
  push_initiative       — Jarvis sees it on next prompt assembly
  self_wakeup           — schedule a wakeup that pings Jarvis directly
  notify_owner          — Discord DM to owner via owner_resolver
  eventbus_publish      — publish event for any subscriber

Cooldown + one-shot prevent action storms. `enabled=False` pauses
without losing the watch. Watches persist to disk so they survive
jarvis-api restarts.

Tool wrappers in core/tools/process_watcher_tools.py expose this to
the LLM as `add_process_watch`, `list_process_watches`,
`remove_process_watch`.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import STATE_DIR

logger = logging.getLogger(__name__)

_STORE = Path(STATE_DIR) / "process_watches.json"
_LOCK = threading.Lock()
_DAEMON_THREAD: threading.Thread | None = None
_DAEMON_STOP = threading.Event()
_POLL_INTERVAL_S = 10
_MAX_WATCHES = 32  # bound resource use


VALID_KINDS = {
    "process_died",
    "log_pattern",
    "state_field_threshold",
    "state_field_change",
    "state_stale",
    "state_list_grew",
}
VALID_ACTIONS = {
    "push_initiative",
    "self_wakeup",
    "notify_owner",
    "eventbus_publish",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _state_path(state_file: str) -> Path:
    """Resolve a state file path. Accepts absolute, ~ expansion, or
    bare filename (resolved under STATE_DIR)."""
    p = state_file.strip()
    if not p:
        return Path()
    expanded = Path(p).expanduser()
    if expanded.is_absolute():
        return expanded
    return Path(STATE_DIR) / expanded


def _walk_field(obj: Any, path: str) -> Any:
    """Walk a dotted path through nested dicts. Returns None if any
    segment is missing. e.g. _walk_field({'a': {'b': 1}}, 'a.b') == 1."""
    cur = obj
    for seg in (path or "").split("."):
        if not seg:
            continue
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None
    return cur


@dataclass
class Watch:
    watch_id: str
    label: str  # human-readable — used in notify text
    conditions: list[dict[str, Any]]  # list of condition dicts
    on_match: str
    notify_text: str = ""
    cooldown_seconds: int = 300  # 5 min default
    one_shot: bool = False
    enabled: bool = True
    created_at: str = field(default_factory=_now_iso)
    last_fired_at: str | None = None
    fire_count: int = 0
    # Per-condition mutable state (last_value seen, last_list_len, last_log_pos)
    runtime_state: dict[str, Any] = field(default_factory=dict)


def _load_all() -> dict[str, Watch]:
    if not _STORE.is_file():
        return {}
    try:
        with _STORE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        logger.warning("process_watcher: load failed: %s", exc)
        return {}
    out: dict[str, Watch] = {}
    if isinstance(data, dict) and isinstance(data.get("watches"), list):
        for entry in data["watches"]:
            if not isinstance(entry, dict):
                continue
            try:
                # Tolerate missing fields for forward-compat
                w = Watch(
                    watch_id=str(entry.get("watch_id") or ""),
                    label=str(entry.get("label") or ""),
                    conditions=list(entry.get("conditions") or []),
                    on_match=str(entry.get("on_match") or "push_initiative"),
                    notify_text=str(entry.get("notify_text") or ""),
                    cooldown_seconds=int(entry.get("cooldown_seconds") or 300),
                    one_shot=bool(entry.get("one_shot") or False),
                    enabled=bool(entry.get("enabled", True)),
                    created_at=str(entry.get("created_at") or _now_iso()),
                    last_fired_at=entry.get("last_fired_at"),
                    fire_count=int(entry.get("fire_count") or 0),
                    runtime_state=dict(entry.get("runtime_state") or {}),
                )
                if w.watch_id:
                    out[w.watch_id] = w
            except Exception as exc:
                logger.warning("process_watcher: skip bad watch: %s", exc)
    return out


def _save_all(watches: dict[str, Watch]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "watches": [asdict(w) for w in watches.values()],
        "updated_at": _now_iso(),
    }
    tmp = _STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_STORE)


# ── Public API ────────────────────────────────────────────────────


def add_watch(
    *,
    label: str,
    conditions: list[dict[str, Any]],
    on_match: str,
    notify_text: str = "",
    cooldown_seconds: int = 300,
    one_shot: bool = False,
) -> dict[str, Any]:
    """Register a new watch. Returns the created Watch as dict, or error."""
    label = (label or "").strip()[:120]
    if not label:
        return {"status": "error", "error": "label required"}
    if on_match not in VALID_ACTIONS:
        return {
            "status": "error",
            "error": f"invalid on_match — must be one of {sorted(VALID_ACTIONS)}",
        }
    if not conditions or not isinstance(conditions, list):
        return {"status": "error", "error": "conditions must be a non-empty list"}
    # Validate every condition has a recognized kind
    for c in conditions:
        if not isinstance(c, dict):
            return {"status": "error", "error": "each condition must be a dict"}
        if c.get("kind") not in VALID_KINDS:
            return {
                "status": "error",
                "error": f"unknown condition kind '{c.get('kind')}' — must be one of {sorted(VALID_KINDS)}",
            }
    with _LOCK:
        watches = _load_all()
        if len(watches) >= _MAX_WATCHES:
            return {
                "status": "error",
                "error": f"watch limit reached ({_MAX_WATCHES}). Remove an old watch first.",
            }
        watch_id = f"watch-{uuid.uuid4().hex[:10]}"
        w = Watch(
            watch_id=watch_id,
            label=label,
            conditions=conditions,
            on_match=on_match,
            notify_text=(notify_text or label).strip()[:400],
            cooldown_seconds=max(0, int(cooldown_seconds)),
            one_shot=bool(one_shot),
        )
        watches[watch_id] = w
        _save_all(watches)
    logger.info("process_watcher: added %s '%s'", watch_id, label)
    return {"status": "ok", "watch": asdict(w)}


def remove_watch(watch_id: str) -> dict[str, Any]:
    with _LOCK:
        watches = _load_all()
        if watch_id not in watches:
            return {"status": "error", "error": "watch not found"}
        watches.pop(watch_id, None)
        _save_all(watches)
    return {"status": "ok", "removed": watch_id}


def list_watches() -> list[dict[str, Any]]:
    with _LOCK:
        return [asdict(w) for w in _load_all().values()]


def set_watch_enabled(watch_id: str, enabled: bool) -> dict[str, Any]:
    with _LOCK:
        watches = _load_all()
        if watch_id not in watches:
            return {"status": "error", "error": "watch not found"}
        watches[watch_id].enabled = bool(enabled)
        _save_all(watches)
    return {"status": "ok", "watch_id": watch_id, "enabled": enabled}


# ── Condition evaluation ──────────────────────────────────────────


def _eval_condition(cond: dict[str, Any], runtime_state: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a single condition. Returns (matched, reason).

    runtime_state is per-watch mutable state used for change-detection
    conditions. We update it in-place for caller to persist.
    """
    kind = cond.get("kind")

    if kind == "process_died":
        name = str(cond.get("process_name") or "").strip()
        if not name:
            return False, "process_died: missing process_name"
        try:
            from core.services.process_supervisor import list_processes
            procs = list_processes(include_stopped=True).get("processes", []) or []
        except Exception as exc:
            return False, f"process_died: list failed: {exc}"
        for p in procs:
            if p.get("name") == name:
                status = str(p.get("status") or "")
                if status in {"exited", "lost"}:
                    return True, f"process '{name}' status={status} (exit_code={p.get('exit_code')})"
                return False, ""
        # Process not in registry — could mean it was removed; treat as died
        return True, f"process '{name}' not in supervisor registry"

    if kind == "log_pattern":
        name = str(cond.get("process_name") or "").strip()
        regex_str = str(cond.get("regex") or "").strip()
        lines_to_check = int(cond.get("lines") or 60)
        if not name or not regex_str:
            return False, "log_pattern: needs process_name + regex"
        try:
            pattern = re.compile(regex_str, re.IGNORECASE)
        except re.error as exc:
            return False, f"log_pattern: invalid regex: {exc}"
        try:
            from core.services.process_supervisor import tail_process_log
            tail = tail_process_log(name, lines=lines_to_check)
            if tail.get("status") == "error":
                return False, f"log_pattern: tail failed: {tail.get('error')}"
            log_text = str(tail.get("lines") or "")
        except Exception as exc:
            return False, f"log_pattern: tail raised: {exc}"
        # Only fire on NEW lines since last evaluation. Use byte_size as
        # a cheap "have we advanced" marker. If not advanced, no new info.
        last_size = int(runtime_state.get("last_log_byte_size") or 0)
        cur_size = int(tail.get("byte_size") or 0)
        if cur_size <= last_size:
            return False, ""
        runtime_state["last_log_byte_size"] = cur_size
        # Look for matches in the tail. For simplicity we match against
        # the whole tail block — finer line-by-line could come later.
        m = pattern.search(log_text)
        if m:
            snippet = log_text[max(0, m.start() - 40): m.end() + 80]
            return True, f"log pattern matched in '{name}': …{snippet}…"
        return False, ""

    if kind == "state_field_threshold":
        state_file = str(cond.get("state_file") or "trading_state.json")
        field_path = str(cond.get("field") or "").strip()
        op = str(cond.get("op") or "above").strip().lower()
        target = float(cond.get("value") or 0)
        if not field_path:
            return False, "state_field_threshold: missing field"
        sp = _state_path(state_file)
        if not sp.is_file():
            return False, f"state_field_threshold: {sp} missing"
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"state_field_threshold: parse failed: {exc}"
        v = _walk_field(data, field_path)
        try:
            current = float(v) if v is not None else None
        except Exception:
            current = None
        if current is None:
            return False, f"state_field_threshold: field '{field_path}' not numeric"
        if op == "above" and current > target:
            return True, f"{field_path}={current:.4f} > {target:.4f}"
        if op == "below" and current < target:
            return True, f"{field_path}={current:.4f} < {target:.4f}"
        if op == "equals" and current == target:
            return True, f"{field_path}={current:.4f} == {target:.4f}"
        return False, ""

    if kind == "state_field_change":
        state_file = str(cond.get("state_file") or "trading_state.json")
        field_path = str(cond.get("field") or "").strip()
        if not field_path:
            return False, "state_field_change: missing field"
        sp = _state_path(state_file)
        if not sp.is_file():
            return False, f"state_field_change: {sp} missing"
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"state_field_change: parse failed: {exc}"
        v = _walk_field(data, field_path)
        cur_str = json.dumps(v, sort_keys=True, default=str)
        last_str = runtime_state.get("last_field_value")
        runtime_state["last_field_value"] = cur_str
        if last_str is None:
            # First evaluation — no baseline yet, don't fire
            return False, ""
        if cur_str != last_str:
            # Optional filter: only fire if matches `to` value
            target_to = cond.get("to")
            if target_to is not None:
                target_str = json.dumps(target_to, sort_keys=True, default=str)
                if cur_str != target_str:
                    return False, ""
            return True, f"{field_path} changed: {last_str} → {cur_str}"
        return False, ""

    if kind == "state_stale":
        state_file = str(cond.get("state_file") or "trading_state.json")
        max_age = int(cond.get("max_age_seconds") or 120)
        sp = _state_path(state_file)
        if not sp.is_file():
            return True, f"state file {sp} missing entirely"
        try:
            mtime = sp.stat().st_mtime
        except Exception as exc:
            return False, f"state_stale: stat failed: {exc}"
        age = time.time() - mtime
        if age > max_age:
            return True, f"state file age {int(age)}s > {max_age}s"
        return False, ""

    if kind == "state_list_grew":
        state_file = str(cond.get("state_file") or "trading_state.json")
        field_path = str(cond.get("field") or "recent_trades").strip()
        sp = _state_path(state_file)
        if not sp.is_file():
            return False, f"state_list_grew: {sp} missing"
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"state_list_grew: parse failed: {exc}"
        v = _walk_field(data, field_path)
        if not isinstance(v, list):
            return False, f"state_list_grew: {field_path} is not a list"
        cur_len = len(v)
        last_len = int(runtime_state.get("last_list_len") or -1)
        runtime_state["last_list_len"] = cur_len
        if last_len < 0:
            # First evaluation — establish baseline
            return False, ""
        if cur_len > last_len:
            # Capture the most recent entry for the notify message
            most_recent = v[-1] if v else None
            return True, f"{field_path} grew {last_len} → {cur_len}: {most_recent}"
        return False, ""

    return False, f"unknown condition kind: {kind}"


# ── Action dispatch ───────────────────────────────────────────────


def _fire_action(watch: Watch, reason: str) -> None:
    """Execute the watch's on_match action. Errors are logged, not raised."""
    text = (watch.notify_text or watch.label).strip()
    body = f"{text}\n[{reason}]"

    if watch.on_match == "push_initiative":
        try:
            from core.services.initiative_queue import push_initiative
            push_initiative(
                focus=body[:500],
                source="process_watcher",
                source_id=watch.watch_id,
            )
        except Exception as exc:
            logger.warning("process_watcher: push_initiative failed: %s", exc)
        return

    if watch.on_match == "self_wakeup":
        try:
            # Schedule a wakeup ~5 seconds out so it surfaces immediately
            # but doesn't fire inside the watcher loop's lock.
            from core.services.scheduled_tasks import schedule_self_wakeup
            schedule_self_wakeup(
                prompt=body[:1000],
                fire_at_seconds_from_now=5,
                reason=f"process_watcher:{watch.label}",
            )
        except Exception as exc:
            # Fallback: many codebases don't have schedule_self_wakeup with
            # that signature. Try the wakeup_dispatcher direct path.
            try:
                from core.services.wakeup_dispatcher import register_self_wakeup
                register_self_wakeup(
                    prompt=body[:1000],
                    fire_in_seconds=5,
                    reason=f"process_watcher:{watch.label}",
                )
            except Exception as exc2:
                logger.warning(
                    "process_watcher: self_wakeup failed (both paths): %s | %s",
                    exc, exc2,
                )
                # Last resort: degrade to push_initiative
                try:
                    from core.services.initiative_queue import push_initiative
                    push_initiative(
                        focus=body[:500],
                        source="process_watcher_fallback",
                        source_id=watch.watch_id,
                    )
                except Exception:
                    pass
        return

    if watch.on_match == "notify_owner":
        try:
            from core.services.discord_gateway import send_dm_to_owner
            send_dm_to_owner(body[:1500])
        except Exception as exc:
            logger.warning("process_watcher: notify_owner failed: %s", exc)
        return

    if watch.on_match == "eventbus_publish":
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "process_watcher.match",
                {
                    "watch_id": watch.watch_id,
                    "label": watch.label,
                    "reason": reason,
                    "fire_count": watch.fire_count,
                },
            )
        except Exception as exc:
            logger.warning("process_watcher: eventbus_publish failed: %s", exc)
        return

    logger.warning("process_watcher: unknown on_match action: %s", watch.on_match)


# ── Daemon loop ───────────────────────────────────────────────────


def _evaluate_watches_once() -> None:
    """One pass: evaluate every enabled watch; fire matched ones."""
    with _LOCK:
        watches = _load_all()
    if not watches:
        return

    now = time.time()
    dirty = False

    for watch_id, watch in list(watches.items()):
        if not watch.enabled:
            continue

        # Cooldown check
        if watch.last_fired_at and watch.cooldown_seconds > 0:
            try:
                last_t = datetime.fromisoformat(
                    str(watch.last_fired_at).replace("Z", "+00:00")
                ).timestamp()
                if (now - last_t) < watch.cooldown_seconds:
                    continue
            except Exception:
                pass

        # Evaluate every condition. Watch fires if ANY matches (OR semantics).
        # Per-condition runtime state is keyed by index for stability.
        matched = False
        match_reason = ""
        any_state_change = False

        for idx, cond in enumerate(watch.conditions):
            cond_state_key = f"cond_{idx}"
            cond_state = dict(watch.runtime_state.get(cond_state_key) or {})
            try:
                ok, reason = _eval_condition(cond, cond_state)
            except Exception as exc:
                logger.warning(
                    "process_watcher: condition eval crashed: %s — %s",
                    cond.get("kind"), exc,
                )
                ok, reason = False, str(exc)
            # Persist runtime_state changes regardless of match
            if cond_state != (watch.runtime_state.get(cond_state_key) or {}):
                watch.runtime_state[cond_state_key] = cond_state
                any_state_change = True
            if ok:
                matched = True
                match_reason = f"[{cond.get('kind')}] {reason}"
                break

        if matched:
            logger.info(
                "process_watcher: '%s' matched (%s) — firing %s",
                watch.label, match_reason, watch.on_match,
            )
            _fire_action(watch, match_reason)
            watch.last_fired_at = _now_iso()
            watch.fire_count += 1
            if watch.one_shot:
                watches.pop(watch_id, None)
            dirty = True
        elif any_state_change:
            dirty = True

    if dirty:
        with _LOCK:
            _save_all(watches)


def _watcher_loop() -> None:
    logger.info("process_watcher: daemon thread started, interval=%ds", _POLL_INTERVAL_S)
    while not _DAEMON_STOP.is_set():
        try:
            _evaluate_watches_once()
        except Exception as exc:
            logger.warning("process_watcher: evaluate pass failed: %s", exc)
        # Sleep with cancel-awareness so stop() returns promptly
        _DAEMON_STOP.wait(_POLL_INTERVAL_S)
    logger.info("process_watcher: daemon thread stopped")


def start_watcher_daemon() -> None:
    """Start the daemon if not already running. Called once at jarvis-api boot."""
    global _DAEMON_THREAD
    if _DAEMON_THREAD is not None and _DAEMON_THREAD.is_alive():
        return
    _DAEMON_STOP.clear()
    _DAEMON_THREAD = threading.Thread(
        target=_watcher_loop, name="process-watcher", daemon=True,
    )
    _DAEMON_THREAD.start()


def stop_watcher_daemon() -> None:
    """Signal the daemon to exit. For tests / shutdown hooks."""
    _DAEMON_STOP.set()
    if _DAEMON_THREAD is not None:
        _DAEMON_THREAD.join(timeout=5)
