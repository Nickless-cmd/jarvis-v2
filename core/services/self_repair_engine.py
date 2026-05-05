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

    return SelfRepairPattern(
        pattern_id=str(row.get("pattern_id") or ""),
        name=str(row.get("name") or ""),
        trigger_event_kind=str(row.get("trigger_event_kind") or ""),
        trigger_match=trigger_match if isinstance(trigger_match, dict) else {},
        action_type=str(row.get("action_type") or ""),
        action_params=action_params if isinstance(action_params, dict) else {},
        enabled=bool(int(row.get("enabled") or 0)),
        cooldown_seconds=int(row.get("cooldown_seconds") or 300),
        max_attempts_per_window=int(row.get("max_attempts_per_window") or 3),
        window_seconds=int(row.get("window_seconds") or 3600),
        auto_disable_after_escalations=int(row.get("auto_disable_after_escalations") or 3),
        auto_disable_window_hours=int(row.get("auto_disable_window_hours") or 24),
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
