"""Self-repair engine — runtime-instigated repair actions for known patterns.

Push-style eventbus subscriber matches events against DB-backed patterns
and executes allowlisted repair actions (v1: daemon_manager.control_daemon
only) directly without going through the LLM/approval layer.

See docs/superpowers/specs/2026-05-05-self-repair-engine-design.md
for the full design.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern dataclass
# ---------------------------------------------------------------------------


@dataclass
class SelfRepairPattern:
    pattern_id: str
    name: str
    trigger_event_kind: str
    trigger_match: dict[str, object]
    action_type: str
    action_params: dict[str, object]
    enabled: bool
    cooldown_seconds: int
    max_attempts_per_window: int
    window_seconds: int
    auto_disable_after_escalations: int
    auto_disable_window_hours: int
    source: str
    source_evidence: dict[str, object] | None


def _decode_pattern(row: dict) -> SelfRepairPattern:
    """Build a SelfRepairPattern from a DB row dict. May raise on malformed JSON."""
    try:
        trigger_match = json.loads(str(row.get("trigger_match_json") or "{}"))
    except Exception:
        trigger_match = {}
    try:
        action_params = json.loads(str(row.get("action_params_json") or "{}"))
    except Exception:
        action_params = {}
    source_evidence_raw = row.get("source_evidence_json")
    if source_evidence_raw:
        try:
            source_evidence = json.loads(str(source_evidence_raw))
        except Exception:
            source_evidence = None
    else:
        source_evidence = None

    def _int_or(default: int, key: str) -> int:
        # is-None check, NOT `or` — value 0 is valid and must not fall through
        v = row.get(key)
        return int(v) if v is not None else default

    return SelfRepairPattern(
        pattern_id=str(row.get("pattern_id") or ""),
        name=str(row.get("name") or ""),
        trigger_event_kind=str(row.get("trigger_event_kind") or ""),
        trigger_match=trigger_match if isinstance(trigger_match, dict) else {},
        action_type=str(row.get("action_type") or ""),
        action_params=action_params if isinstance(action_params, dict) else {},
        enabled=bool(_int_or(0, "enabled")),
        cooldown_seconds=_int_or(300, "cooldown_seconds"),
        max_attempts_per_window=_int_or(3, "max_attempts_per_window"),
        window_seconds=_int_or(3600, "window_seconds"),
        auto_disable_after_escalations=_int_or(3, "auto_disable_after_escalations"),
        auto_disable_window_hours=_int_or(24, "auto_disable_window_hours"),
        source=str(row.get("source") or ""),
        source_evidence=source_evidence,
    )


# ---------------------------------------------------------------------------
# Match logic
# ---------------------------------------------------------------------------


def _pattern_matches_event(pattern: SelfRepairPattern, event: dict) -> bool:
    """True if event matches pattern's trigger_event_kind + trigger_match predicates."""
    if str(event.get("kind") or "") != pattern.trigger_event_kind:
        return False
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    for key, expected in pattern.trigger_match.items():
        actual = payload.get(key)
        if not _payload_predicate_matches(expected, actual):
            return False
    return True


def _payload_predicate_matches(expected, actual) -> bool:
    """Predicate forms supported in trigger_match values:
    - scalar (str/int/bool): exact match
    - dict {"op": "gt", "value": N}: numeric comparison
    - dict {"op": "lt", "value": N}: numeric comparison
    - dict {"op": "in", "values": [...]}: membership
    - dict {"op": "regex", "pattern": "..."}: regex on str(actual)
    """
    if isinstance(expected, dict) and "op" in expected:
        op = expected["op"]
        try:
            if op == "gt":
                return float(actual) > float(expected["value"])
            if op == "lt":
                return float(actual) < float(expected["value"])
            if op == "in":
                return actual in (expected.get("values") or [])
            if op == "regex":
                return bool(re.search(str(expected["pattern"]), str(actual)))
        except Exception:
            return False
        return False
    return expected == actual


def _now() -> datetime:
    """Indirected for monkeypatching in tests."""
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


# ---------------------------------------------------------------------------
# Action allowlist + handlers
# ---------------------------------------------------------------------------


def _action_control_daemon(params: dict) -> dict:
    """Allowlisted handler for control_daemon. Validates params then delegates."""
    from core.services.daemon_manager import control_daemon

    name = str(params.get("name") or "")
    action = str(params.get("action") or "")
    if not name or action not in {"enable", "disable", "restart", "set_interval"}:
        raise ValueError(f"invalid control_daemon params: {params!r}")
    interval = params.get("interval_minutes")
    if interval is not None:
        interval = int(interval)
    return control_daemon(name, action, interval_minutes=interval)


_ACTION_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "control_daemon": _action_control_daemon,
    # v1: only this. Adding new actions requires explicit PR + governance review.
}


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


from core.runtime.db import count_recent_attempts


def _check_cooldown(pattern: SelfRepairPattern) -> str:
    """Return 'ok' if attempt allowed, else reason string explaining why blocked."""
    try:
        now = _now()

        if pattern.cooldown_seconds > 0:
            cooldown_since = (now - timedelta(seconds=pattern.cooldown_seconds)).isoformat()
            recent_executed = count_recent_attempts(
                pattern_id=pattern.pattern_id,
                since_iso=cooldown_since,
                outcome="executed",
            )
            if recent_executed > 0:
                return f"cooldown ({pattern.cooldown_seconds}s since last execution)"

        window_since = (now - timedelta(seconds=pattern.window_seconds)).isoformat()
        recent = count_recent_attempts(
            pattern_id=pattern.pattern_id,
            since_iso=window_since,
            outcome=None,
        )
        if recent >= pattern.max_attempts_per_window:
            return (
                f"window-cap-reached ({recent}/{pattern.max_attempts_per_window} "
                f"in {pattern.window_seconds}s)"
            )
        return "ok"
    except Exception as exc:
        logger.warning(
            "self_repair: cooldown check failed for %s: %s",
            pattern.pattern_id, exc,
        )
        return "db-error"


# ---------------------------------------------------------------------------
# Public CRUD API
# ---------------------------------------------------------------------------


from core.runtime.db import (
    insert_self_repair_pattern,
    get_self_repair_pattern,
    list_self_repair_patterns,
    update_self_repair_pattern,
    delete_self_repair_pattern,
    list_recent_self_repair_attempts,
)


def register_pattern(
    *,
    pattern_id: str,
    name: str,
    trigger_event_kind: str,
    trigger_match: dict[str, object] | None = None,
    action_type: str,
    action_params: dict[str, object] | None = None,
    enabled: bool = True,
    cooldown_seconds: int | None = None,
    max_attempts_per_window: int | None = None,
    window_seconds: int | None = None,
    auto_disable_after_escalations: int | None = None,
    auto_disable_window_hours: int | None = None,
    source: str = "manual",
    source_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    """Register a self-repair pattern. Validates action_type against allowlist."""
    if action_type not in _ACTION_HANDLERS:
        raise ValueError(
            f"action_type {action_type!r} not in allowlist: {sorted(_ACTION_HANDLERS)}"
        )
    if not pattern_id or not name or not trigger_event_kind:
        raise ValueError(
            "pattern_id, name, trigger_event_kind required (non-empty strings)"
        )

    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        cd = cooldown_seconds if cooldown_seconds is not None else int(getattr(s, "self_repair_default_cooldown_seconds", 300))
        max_w = max_attempts_per_window if max_attempts_per_window is not None else int(getattr(s, "self_repair_default_max_attempts_per_window", 3))
        win_s = window_seconds if window_seconds is not None else int(getattr(s, "self_repair_default_window_seconds", 3600))
        auto_n = auto_disable_after_escalations if auto_disable_after_escalations is not None else int(getattr(s, "self_repair_default_auto_disable_after_escalations", 3))
        auto_h = auto_disable_window_hours if auto_disable_window_hours is not None else int(getattr(s, "self_repair_default_auto_disable_window_hours", 24))
    except Exception:
        cd = cooldown_seconds if cooldown_seconds is not None else 300
        max_w = max_attempts_per_window if max_attempts_per_window is not None else 3
        win_s = window_seconds if window_seconds is not None else 3600
        auto_n = auto_disable_after_escalations if auto_disable_after_escalations is not None else 3
        auto_h = auto_disable_window_hours if auto_disable_window_hours is not None else 24

    insert_self_repair_pattern(
        pattern_id=pattern_id,
        name=name,
        trigger_event_kind=trigger_event_kind,
        trigger_match_json=json.dumps(trigger_match or {}, ensure_ascii=False),
        action_type=action_type,
        action_params_json=json.dumps(action_params or {}, ensure_ascii=False),
        enabled=enabled,
        cooldown_seconds=cd,
        max_attempts_per_window=max_w,
        window_seconds=win_s,
        auto_disable_after_escalations=auto_n,
        auto_disable_window_hours=auto_h,
        source=source,
        source_evidence_json=(
            json.dumps(source_evidence, ensure_ascii=False) if source_evidence else None
        ),
    )
    return get_self_repair_pattern(pattern_id) or {}


def list_patterns(
    *,
    enabled: bool | None = None,
    trigger_event_kind: str | None = None,
) -> list[dict[str, object]]:
    return list_self_repair_patterns(
        enabled=enabled, trigger_event_kind=trigger_event_kind,
    )


def enable_pattern(pattern_id: str) -> bool:
    return update_self_repair_pattern(pattern_id, enabled=True)


def disable_pattern(pattern_id: str) -> bool:
    return update_self_repair_pattern(pattern_id, enabled=False)


def delete_pattern(pattern_id: str) -> bool:
    return delete_self_repair_pattern(pattern_id)


def list_recent_attempts(
    *, pattern_id: str | None = None, limit: int = 50,
) -> list[dict[str, object]]:
    return list_recent_self_repair_attempts(pattern_id=pattern_id, limit=limit)


def build_self_repair_surface() -> dict[str, object]:
    """Compact surface for Mission Control consumption."""
    patterns = list_self_repair_patterns()
    enabled_count = sum(1 for p in patterns if p["enabled"])
    return {
        "engine_enabled": _engine_enabled(),
        "pattern_count": len(patterns),
        "enabled_pattern_count": enabled_count,
        "patterns": patterns,
        "recent_attempts": list_recent_self_repair_attempts(limit=20),
    }


def _engine_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "self_repair_engine_enabled", True))
    except Exception:
        return True
