"""R2 verification gate telemetry — track whether warnings get heeded.

The verification gate (R2) is observational only — it surfaces
"⚠ N mutations, M verifies" and lets the model decide. We've never
known whether the model actually ACTS on these warnings.

This module records two streams of evidence:

1. **Surfaces** — every time verification_gate_section returns non-None,
   we log a snapshot (warning kind, mutation_count, failed_verify_count,
   timestamp).

2. **Reactions** — for each surfaced warning, we observe the next
   60 seconds for verify_* tool calls. If a verify follows, the warning
   was "heeded". If not, it was "ignored". Recorded with provenance.

Aggregate:
- `surfaced_total`, `heeded_total`, `ignored_total`
- `heed_rate` (last 24h, last 7d)
- per-warning-kind breakdown

Promotion path: when `heed_rate < 0.4` over a meaningful window AND
unverified mutations are still flowing, we have data to flip R2 → R2.5
(conditional blocking). That decision is left to the user; this module
just provides the numbers.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TELEMETRY_KEY = "r2_verification_gate_telemetry"
_REACTION_WINDOW_SECONDS = 60
_MAX_RECORDS = 500


def _load() -> dict[str, Any]:
    try:
        data = load_json(_TELEMETRY_KEY, {}) or {}
        if not isinstance(data, dict):
            return {}
        data.setdefault("surfaces", [])
        data.setdefault("reactions", [])
        return data
    except Exception:
        return {"surfaces": [], "reactions": []}


def _save(data: dict[str, Any]) -> None:
    try:
        # Keep bounded
        data["surfaces"] = list(data.get("surfaces", []))[-_MAX_RECORDS:]
        data["reactions"] = list(data.get("reactions", []))[-_MAX_RECORDS:]
        save_json(_TELEMETRY_KEY, data)
    except Exception as exc:
        logger.debug("r2_telemetry: persist failed: %s", exc)


_lock = threading.Lock()


def record_surface(
    *,
    failed_verify_count: int,
    unverified_count: int,
    mutation_count: int,
    verify_count: int,
) -> None:
    """Called by verification_gate_section when it returns a non-None section."""
    if failed_verify_count <= 0 and unverified_count <= 0:
        return
    now = datetime.now(UTC)
    record = {
        "at": now.isoformat(),
        "kind": "failed_verify" if failed_verify_count > 0 else "unverified",
        "failed_verify_count": failed_verify_count,
        "unverified_count": unverified_count,
        "mutation_count": mutation_count,
        "verify_count": verify_count,
        "resolved": False,  # set True once a verify_* arrives within window
    }
    with _lock:
        data = _load()
        # Suppress duplicate if we just recorded the same warning <60s ago
        existing = data.get("surfaces", [])
        if existing:
            last = existing[-1]
            try:
                last_ts = datetime.fromisoformat(str(last.get("at", "")))
                if (now - last_ts).total_seconds() < 30:
                    return
            except ValueError:
                pass
        existing.append(record)
        data["surfaces"] = existing
        _save(data)


def record_verify_event(*, tool: str, status: str, at: datetime | None = None) -> None:
    """Called by an eventbus listener for tool.completed events. If a recent
    surface is unresolved and within the reaction window, mark it heeded."""
    now = at or datetime.now(UTC)
    if status != "ok":
        return  # only successful verifies count as heeding
    with _lock:
        data = _load()
        surfaces = data.get("surfaces", [])
        cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS)
        changed = False
        for s in reversed(surfaces):
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                break  # past window — older surfaces also out
            s["resolved"] = True
            s["heeded_by"] = tool
            s["heeded_at"] = now.isoformat()
            changed = True
            # Record the reaction
            data.setdefault("reactions", []).append({
                "at": now.isoformat(),
                "verdict": "heeded",
                "tool": tool,
                "surface_at": s.get("at"),
                "kind": s.get("kind"),
            })
            break  # only resolve the most recent unresolved surface
        if changed:
            _save(data)


def sweep_expired_surfaces() -> int:
    """Mark surfaces as 'ignored' once they're past the reaction window with
    no matching verify_*. Run periodically."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS)
    ignored = 0
    with _lock:
        data = _load()
        surfaces = data.get("surfaces", [])
        for s in surfaces:
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                s["resolved"] = True
                s["ignored_at"] = now.isoformat()
                ignored += 1
                data.setdefault("reactions", []).append({
                    "at": now.isoformat(),
                    "verdict": "ignored",
                    "surface_at": s.get("at"),
                    "kind": s.get("kind"),
                })
        if ignored:
            _save(data)
    return ignored


def get_telemetry_summary(*, hours: int = 24) -> dict[str, Any]:
    """Aggregate counts + heed_rate over the lookback window."""
    sweep_expired_surfaces()
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    data = _load()
    in_window = 0
    heeded = 0
    ignored = 0
    by_kind: dict[str, dict[str, int]] = {}
    for s in data.get("surfaces", []):
        try:
            s_at = datetime.fromisoformat(str(s.get("at", "")))
        except ValueError:
            continue
        if s_at < cutoff:
            continue
        in_window += 1
        kind = str(s.get("kind") or "unknown")
        by_kind.setdefault(kind, {"surfaced": 0, "heeded": 0, "ignored": 0})
        by_kind[kind]["surfaced"] += 1
        if s.get("heeded_by"):
            heeded += 1
            by_kind[kind]["heeded"] += 1
        elif s.get("ignored_at"):
            ignored += 1
            by_kind[kind]["ignored"] += 1
    rate = round(heeded / in_window, 3) if in_window > 0 else None
    return {
        "window_hours": hours,
        "surfaced_total": in_window,
        "heeded_total": heeded,
        "ignored_total": ignored,
        "heed_rate": rate,
        "by_kind": by_kind,
    }


def telemetry_section() -> str | None:
    """Render telemetry as a prompt-awareness section. Only shows when there's
    a meaningful pattern (>= 5 surfaces in the last 24h)."""
    s = get_telemetry_summary(hours=24)
    if s.get("surfaced_total", 0) < 5:
        return None
    rate = s.get("heed_rate")
    rate_str = f"{int(rate * 100)}%" if rate is not None else "n/a"
    flag = ""
    if rate is not None and rate < 0.4:
        flag = " ⚠ under 40% — du ignorerer for ofte advarslerne"
    return (
        f"R2-gate telemetry (24t): surfaced={s['surfaced_total']} "
        f"heeded={s['heeded_total']} ignored={s['ignored_total']} "
        f"heed_rate={rate_str}{flag}"
    )


# ── Eventbus subscription ──────────────────────────────────────────────────


_subscribed = False


def _poll_loop() -> None:
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return
    queue = event_bus.subscribe()
    while True:
        item = queue.get()
        if item is None:
            return
        try:
            kind = str(item.get("kind") or "")
            if kind != "tool.completed":
                continue
            payload = item.get("payload") or {}
            tool = str(payload.get("tool") or "")
            status = str(payload.get("status") or "")
            if tool.startswith("verify_") and status == "ok":
                record_verify_event(tool=tool, status=status)
        except Exception:
            continue


def subscribe() -> None:
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(target=_poll_loop, name="r2-telemetry", daemon=True).start()
