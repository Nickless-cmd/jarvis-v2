"""Causal inference daemon — three-tier matching against event allowlist.

Tier 1 (kind-rule, conf=0.9): hardcoded parent-kind → child-kind par,
  kræver shared_id eller ≤30s temporal proximity.
Tier 2 (shared-id, conf=0.8): match på tool_call_id/run_id/decision_id
  i payload, ≤60s.
Tier 3 (temporal-only, conf=0.4): samme session_id ≤30s, intet andet match.

Cap 500 nye edges/tick. Retention 30 dage (60 for explicit).
Emitter causal.inference_stats event efter hvert tick.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

from core.runtime.db import _ensure_causal_edges_table, connect

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

_CADENCE_SECONDS = 15 * 60
_MAX_EDGES_PER_TICK = 500
_RETENTION_DAYS_INFERRED = 30
_RETENTION_DAYS_EXPLICIT = 60
_MAX_PRUNE_PER_TICK = 5000
_DEFAULT_LOOKBACK_MINUTES = 30

_ALLOWLIST = frozenset({
    "tool.completed", "tool.error", "tool.invoked", "tool.force_invoked",
    "decision.created", "decision.deduped", "decision.revoked",
    "behavioral_decision_review.kept",
    "behavioral_decision_review.partial",
    "behavioral_decision_review.broken",
    "self_review.completed", "conflict.detected", "conflict.resolved",
    "counterfactual.detected", "counterfactual.regret",
    "contradiction.detected",
    "runtime.executive_action_outcome_recorded",
    "runtime.cheap_lane_provider_failed",
    "channel.message_inbound",
    "memory.seed_triggered", "memory.seed_fulfilled",
    "identity.drift_detected", "heartbeat.conflict_resolved",
})

_KIND_RULES: dict[str, set[str]] = {
    "tool.invoked":      {"tool.completed", "tool.error"},
    "tool.force_invoked": {"tool.completed", "tool.error"},
    "decision.created":   {"behavioral_decision_review.kept",
                           "behavioral_decision_review.partial",
                           "behavioral_decision_review.broken"},
    "conflict.detected":  {"conflict.resolved"},
    "channel.message_inbound": {"tool.invoked", "tool.force_invoked"},
}

# Tier-2 strict-ID keys. session_id LIVES ONLY in tier-3 (temporal session
# correlation) so the two tiers don't collide — spec-revision 2026-05-08:
# without this split, tier-2 always wins for same-session events and tier-3
# becomes unreachable for the case it was designed for.
_SHARED_ID_KEYS = ("tool_call_id", "decision_id", "run_id")

_KIND_RULE_WINDOW_S = 30
_SHARED_ID_WINDOW_S = 60
_TEMPORAL_FALLBACK_WINDOW_S = 30

_last_tick_at: datetime | None = None


def _ensure_table_ready() -> None:
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.commit()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def _record_edge(
    *, child: int, parent: int, edge_kind: str,
    confidence: float, source: str, reasoning: str,
) -> str:
    """INSERT or UPGRADE an edge. Returns 'created'|'upgraded'|'skipped'."""
    now_iso = _now_iso()
    with connect() as c:
        existing = c.execute(
            "SELECT confidence FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ? "
            "AND edge_kind = ?",
            (child, parent, edge_kind),
        ).fetchone()
        if existing is not None:
            cur_conf = float(existing["confidence"])
            if confidence > cur_conf:
                c.execute(
                    "UPDATE causal_edges SET confidence = ?, source = ?, "
                    "reasoning = ?, created_at = ? "
                    "WHERE child_event_id = ? AND parent_event_id = ? "
                    "AND edge_kind = ?",
                    (confidence, source, reasoning, now_iso,
                     child, parent, edge_kind),
                )
                c.commit()
                return "upgraded"
            return "skipped"
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at, reasoning) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (child, parent, edge_kind, confidence, source, now_iso, reasoning),
        )
        c.commit()
        return "created"


def _payload(event: dict) -> dict:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:
        return {}


def _try_tier1_kind_rule(child: dict, candidates_by_kind: dict[str, list[dict]]) -> tuple[int | None, str]:
    """Match against hardcoded kind-rule with shared-id-preferred fallback.

    Two-pass: first scan ALL candidates for shared-id match. Only if none
    found do we fall back to temporal-only (closest within KIND_RULE_WINDOW).
    Without two-pass, an unrelated candidate at -2s would beat the real
    shared-id parent at -3s.
    """
    child_kind = str(child["kind"])
    child_payload = _payload(child)
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""

    for parent_kind, child_set in _KIND_RULES.items():
        if child_kind not in child_set:
            continue
        candidates = candidates_by_kind.get(parent_kind, [])

        # Pass 1: prefer shared-id match. When multiple candidates share an
        # id (test reruns, retried tool calls), pick the CLOSEST in time —
        # closest match is most likely the true cause.
        best_id_match: tuple[dict, str] | None = None
        best_id_dt: float = (_KIND_RULE_WINDOW_S * 4) + 1
        for cand in candidates:
            cand_ts = _parse_iso(cand["created_at"])
            if cand_ts is None or cand_ts >= child_ts:
                continue
            dt = (child_ts - cand_ts).total_seconds()
            if dt > _KIND_RULE_WINDOW_S * 4:
                continue
            cand_payload = _payload(cand)
            for key in _SHARED_ID_KEYS:
                if (child_payload.get(key)
                        and cand_payload.get(key) == child_payload.get(key)):
                    if dt < best_id_dt:
                        best_id_dt = dt
                        best_id_match = (cand, key)
                    break
        if best_id_match is not None:
            cand, key = best_id_match
            return int(cand["id"]), f"kind-rule:{parent_kind}->{child_kind}+id:{key}"

        # Pass 2: fallback temporal-only within tight KIND_RULE_WINDOW_S
        # Pick the CLOSEST candidate (smallest dt) — most likely the true cause.
        best: dict | None = None
        best_dt: float = _KIND_RULE_WINDOW_S + 1
        for cand in candidates:
            cand_ts = _parse_iso(cand["created_at"])
            if cand_ts is None or cand_ts >= child_ts:
                continue
            dt = (child_ts - cand_ts).total_seconds()
            if dt > _KIND_RULE_WINDOW_S:
                continue
            if dt < best_dt:
                best_dt = dt
                best = cand
        if best is not None:
            return int(best["id"]), f"kind-rule:{parent_kind}->{child_kind}+time"
    return None, ""


def _try_tier2_shared_id(child: dict, candidates: list[dict]) -> tuple[int | None, str]:
    child_payload = _payload(child)
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""
    for key in _SHARED_ID_KEYS:
        cv = child_payload.get(key)
        if not cv:
            continue
        for cand in candidates:
            if int(cand["id"]) == int(child["id"]):
                continue
            cand_ts = _parse_iso(cand["created_at"])
            if cand_ts is None or cand_ts >= child_ts:
                continue
            if (child_ts - cand_ts).total_seconds() > _SHARED_ID_WINDOW_S:
                continue
            cp = _payload(cand)
            if cp.get(key) == cv:
                return int(cand["id"]), f"shared-id:{key}"
    return None, ""


def _try_tier3_temporal(child: dict, candidates: list[dict]) -> tuple[int | None, str]:
    child_payload = _payload(child)
    sess = child_payload.get("session_id")
    if not sess:
        return None, ""
    child_ts = _parse_iso(child["created_at"])
    if child_ts is None:
        return None, ""
    best_cand: dict | None = None
    best_dt: float = _TEMPORAL_FALLBACK_WINDOW_S + 1
    for cand in candidates:
        if int(cand["id"]) == int(child["id"]):
            continue
        cp = _payload(cand)
        if cp.get("session_id") != sess:
            continue
        cand_ts = _parse_iso(cand["created_at"])
        if cand_ts is None or cand_ts >= child_ts:
            continue
        dt = (child_ts - cand_ts).total_seconds()
        if dt > _TEMPORAL_FALLBACK_WINDOW_S:
            continue
        if dt < best_dt:
            best_dt = dt
            best_cand = cand
    if best_cand is not None:
        return int(best_cand["id"]), f"temporal:session+{int(best_dt)}s"
    return None, ""


def _fetch_allowlist_events(
    *,
    since_minutes: int | None = None,
    limit: int = 1000,
) -> list[dict]:
    """Fetch allowlist events for inference.

    since_minutes=None disables the time-window filter — used by tests
    that need to operate on synthetic timestamps. Production calls pass
    _DEFAULT_LOOKBACK_MINUTES (30).
    """
    placeholders = ",".join("?" * len(_ALLOWLIST))
    if since_minutes is None:
        sql = (
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) "
            f"ORDER BY created_at ASC LIMIT ?"
        )
        params = (*list(_ALLOWLIST), limit)
    else:
        cutoff = (datetime.now(UTC) - timedelta(minutes=since_minutes)).isoformat()
        sql = (
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE created_at >= ? AND kind IN ({placeholders}) "
            f"ORDER BY created_at ASC LIMIT ?"
        )
        params = (cutoff, *list(_ALLOWLIST), limit)
    with connect() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _prune_old_edges() -> int:
    cutoff_inferred = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS_INFERRED)).isoformat()
    cutoff_explicit = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS_EXPLICIT)).isoformat()
    with connect() as c:
        cur = c.execute(
            "DELETE FROM causal_edges WHERE id IN ("
            "  SELECT id FROM causal_edges "
            "  WHERE (source != 'explicit' AND created_at < ?) "
            "     OR (source = 'explicit' AND created_at < ?) "
            "  LIMIT ?"
            ")",
            (cutoff_inferred, cutoff_explicit, _MAX_PRUNE_PER_TICK),
        )
        deleted = cur.rowcount or 0
        c.commit()
    return deleted


def run_inference_cycle(
    *, since_minutes: int | None = None,
) -> dict[str, int]:
    """Run one inference tick. Returns stats dict.

    since_minutes=None means "all allowlist events" (used by tests).
    Production tick passes _DEFAULT_LOOKBACK_MINUTES via tick_*().
    """
    _ensure_table_ready()
    started = time.monotonic()

    events = _fetch_allowlist_events(since_minutes=since_minutes)
    candidates_by_kind: dict[str, list[dict]] = {}
    for ev in events:
        candidates_by_kind.setdefault(str(ev["kind"]), []).append(ev)

    edges_created = 0
    edges_upgraded = 0
    tier1 = tier2 = tier3 = 0

    for child in events:
        if edges_created >= _MAX_EDGES_PER_TICK:
            break
        # Tier 1
        pid, reason = _try_tier1_kind_rule(child, candidates_by_kind)
        if pid is not None and pid != int(child["id"]):
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="triggered", confidence=0.9,
                source="inferred-kind", reasoning=reason,
            )
            if res == "created":
                edges_created += 1
                tier1 += 1
            elif res == "upgraded":
                edges_upgraded += 1
            continue
        # Tier 2
        pid, reason = _try_tier2_shared_id(child, events)
        if pid is not None:
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="caused", confidence=0.8,
                source="inferred-id", reasoning=reason,
            )
            if res == "created":
                edges_created += 1
                tier2 += 1
            elif res == "upgraded":
                edges_upgraded += 1
            continue
        # Tier 3
        pid, reason = _try_tier3_temporal(child, events)
        if pid is not None:
            res = _record_edge(
                child=int(child["id"]), parent=pid,
                edge_kind="caused", confidence=0.4,
                source="inferred-temporal", reasoning=reason,
            )
            if res == "created":
                edges_created += 1
                tier3 += 1
            elif res == "upgraded":
                edges_upgraded += 1

    pruned = 0
    try:
        pruned = _prune_old_edges()
    except Exception as exc:
        logger.warning("causal_inference: prune failed: %s", exc)

    duration_ms = int((time.monotonic() - started) * 1000)
    stats = {
        "events_scanned": len(events),
        "edges_created": edges_created,
        "edges_upgraded": edges_upgraded,
        "tier1_kind_rule_hits": tier1,
        "tier2_shared_id_hits": tier2,
        "tier3_temporal_hits": tier3,
        "edges_pruned": pruned,
        "duration_ms": duration_ms,
    }
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("causal.inference_stats", {**stats, "completed_at": _now_iso()})
    except Exception as exc:
        logger.debug("causal_inference: publish stats failed: %s", exc)

    return stats


def tick_causal_inference_daemon() -> dict[str, object]:
    """Daemon-manager entry: run one cycle if cadence elapsed."""
    global _last_tick_at
    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at).total_seconds() < _CADENCE_SECONDS:
            return {"ran": False}
    try:
        stats = run_inference_cycle(since_minutes=_DEFAULT_LOOKBACK_MINUTES)
        _last_tick_at = now
        return {"ran": True, **stats}
    except Exception as exc:
        logger.warning("causal_inference: cycle failed: %s", exc, exc_info=True)
        _last_tick_at = now
        return {"ran": False, "error": str(exc)}
