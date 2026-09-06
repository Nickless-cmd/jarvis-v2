"""Drain the two dead nudge wells (redesign 2026-09-04). Dry-run by default.

* outbound_nudges (DB): every pending/inspected row whose source is telemetry
  ("autonomous_run") is dismissed; other pending rows are re-routed into
  proactive_candidates so the bridge can still deliver them; mid-run user
  messages older than 1 day are dismissed (the run they belonged to is gone).
* nudge_broend.json: pending autonomous_run entries are dropped.

Usage:
    python scripts/nudge_well_cleanup.py            # report only
    python scripts/nudge_well_cleanup.py --apply
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.runtime.db import connect


def clean_outbound(apply: bool) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    day_ago = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    out: dict[str, Any] = {}
    with connect() as conn:
        exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outbound_nudges'").fetchone()
        if not exists:
            return {"skipped": "no table"}
        tele = conn.execute(
            "SELECT count(*) FROM outbound_nudges WHERE status IN ('pending','inspected') AND source='autonomous_run'"
        ).fetchone()[0]
        stale_midway = conn.execute(
            "SELECT count(*) FROM outbound_nudges WHERE status IN ('pending','inspected') "
            "AND source='user_midway_followup' AND created_at < ?", (day_ago,)
        ).fetchone()[0]
        reroute = conn.execute(
            "SELECT nudge_id, source, kind, message, importance FROM outbound_nudges WHERE status='pending' "
            "AND source NOT IN ('autonomous_run','user_midway_followup')"
        ).fetchall()
        out.update({"telemetry_to_dismiss": int(tele), "stale_midway_to_dismiss": int(stale_midway),
                    "pending_to_reroute": len(reroute)})
        if not apply:
            return out
        conn.execute("UPDATE outbound_nudges SET status='dismissed', dismissed_at=? WHERE status IN ('pending','inspected') AND source='autonomous_run'", (now,))
        conn.execute("UPDATE outbound_nudges SET status='dismissed', dismissed_at=? WHERE status IN ('pending','inspected') AND source='user_midway_followup' AND created_at < ?", (now, day_ago))
        conn.commit()
    rerouted = 0
    from core.services.proactive_candidates import add_candidate
    for r in reroute:
        res = add_candidate(source=str(r[1]), kind=str(r[2] or ""), text=str(r[3] or ""),
                            priority="high" if str(r[4]) in ("high", "critical") else "medium")
        if res.get("status") == "added":
            rerouted += 1
    with connect() as conn:
        conn.execute("UPDATE outbound_nudges SET status='dismissed', dismissed_at=? WHERE status='pending' AND source NOT IN ('autonomous_run','user_midway_followup')", (now,))
        conn.commit()
    out.update({"dismissed_telemetry": int(tele), "dismissed_stale_midway": int(stale_midway), "rerouted": rerouted})
    return out


def clean_broend(apply: bool, path: Path | None = None) -> dict[str, Any]:
    p = path or (Path.home() / ".jarvis-v2" / "state" / "nudge_broend.json")
    if not p.exists():
        return {"skipped": f"missing {p}"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)[:120]}
    if not isinstance(data, list):
        return {"error": "not a list"}
    doomed = [n for n in data if n.get("status") == "pending" and str(n.get("source") or "") == "autonomous_run"]
    out = {"total": len(data), "would_drop": len(doomed)}
    if apply and doomed:
        keep = [n for n in data if n not in doomed]
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        out["dropped"] = len(doomed)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    report = {"apply": args.apply, "outbound_nudges": clean_outbound(args.apply), "nudge_broend": clean_broend(args.apply)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
