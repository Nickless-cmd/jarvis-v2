# core/services/docs_drift_watchdog.py
"""SP5 docs-drift watchdog — surface docs/drift_report.json to the Central as a docs:drift nerve.

Reads the committed report (never re-runs AST in the hot path), checks whether the report looks
stale relative to the generated docs, and emits a docs:drift timeseries sample + observe trace.
Self-safe: every function returns sensible defaults and never throws."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs" / "drift_report.json"
_REPORT_STALE_AFTER_DAYS = 7  # the drift audit is "stale" if it hasn't been re-run in this long


def read_report(report_path: Path = REPORT) -> dict[str, Any]:
    try:
        if not Path(report_path).exists():
            return {}
        data = json.loads(Path(report_path).read_text(errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _report_stale(report_path: Path = REPORT, repo: Path = REPO) -> bool:
    """True if the drift audit itself is old — the report is missing, or its own
    ``generated_at`` timestamp is more than ``_REPORT_STALE_AFTER_DAYS`` ago (nobody has
    re-run ``docs_drift_check.py`` recently). Uses the report's embedded timestamp, NOT
    filesystem mtimes, so a ``git pull`` that rewrites file mtimes on deploy does not
    falsely flag the audit as stale."""
    try:
        rep = read_report(report_path)
        gen = rep.get("generated_at")
        if not gen:
            return True
        ts = datetime.fromisoformat(str(gen))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0
        return age_days > _REPORT_STALE_AFTER_DAYS
    except Exception:
        return False


def check_docs_drift(report_path: Path = REPORT, repo: Path = REPO) -> dict[str, Any]:
    rep = read_report(report_path)
    counts = rep.get("counts") or {}
    try:
        hard = int(counts.get("hard", 0) or 0)
    except Exception:
        hard = 0
    try:
        soft = int(counts.get("soft", 0) or 0)
    except Exception:
        soft = 0
    return {
        "hard_count": hard,
        "soft_count": soft,
        "report_present": bool(rep),
        "report_stale": _report_stale(report_path, repo),
        "generated_at": str(rep.get("generated_at", "")),
    }


def observe_docs_drift() -> dict[str, Any]:
    """Emit the docs:drift signal to Central (timeseries + observe trace). Self-safe."""
    state = check_docs_drift()
    try:
        from core.services.central_timeseries import record
        record("docs", "drift", value=float(state["hard_count"]),
               meta={"soft": state["soft_count"], "report_stale": state["report_stale"],
                     "present": state["report_present"]})
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "docs", "nerve": "drift", "kind": "observe", **state})
    except Exception:
        pass
    return state


def build_docs_drift_surface() -> dict[str, Any]:
    """Read-only surface for /central/docs-drift. Never throws."""
    try:
        rep = read_report()
        state = check_docs_drift()
        state["status"] = "ok"
        state["top_hard"] = (rep.get("hard") or [])[:5]
        state["top_soft"] = (rep.get("soft") or [])[:5]
        return state
    except Exception:
        return {"status": "unavailable", "hard_count": 0, "soft_count": 0,
                "report_present": False, "report_stale": False, "generated_at": ""}


def _run_producer_tick(**_: Any) -> dict[str, object]:
    state = observe_docs_drift()
    return {"status": "ok", "hard": state["hard_count"], "soft": state["soft_count"]}


def register_docs_drift_producer() -> None:
    """Register the docs-drift observation as a ~5-min cadence producer."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="docs_drift_watchdog",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=_run_producer_tick,
        priority=10,
    ))
