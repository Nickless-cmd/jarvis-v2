#!/usr/bin/env python
"""Identity formation monitor — daily snapshot of Jarvis' becoming.

Run this daily (manually, or via cron) to see:
- Recent crisis markers (formative friction moments)
- Personality baseline trajectory (where his neutral is shifting)
- Active long arcs (monthly/quarterly/annual narratives generated)
- Pending identity proposals (drift → IDENTITY.md updates awaiting review)

Output to stdout + writes a daily summary to:
  ~/.jarvis-v2/workspaces/default/runtime/identity_formation_log.md

This is the file you read once a week or so to decide whether any of
his identity proposals should be approved. The system observes; you
decide what becomes real.

Usage:
    conda activate ai
    python scripts/identity_formation_monitor.py
    python scripts/identity_formation_monitor.py --days 30
    python scripts/identity_formation_monitor.py --silent  # no stdout, just write log
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure project root is on sys.path so 'core' imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily identity-formation snapshot")
    parser.add_argument("--days", type=int, default=7,
                        help="Lookback window for recent activity (default 7)")
    parser.add_argument("--silent", action="store_true",
                        help="Don't print to stdout, just write log file")
    args = parser.parse_args()

    output: list[str] = []
    today = datetime.now(UTC).date().isoformat()
    output.append(f"# Identity Formation Snapshot — {today}\n")
    output.append(f"_Lookback: {args.days} days. Generated {datetime.now(UTC).isoformat()[:19]}._\n")

    # 1. Crisis markers
    output.append("## 📍 Crisis markers")
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=args.days, limit=20)
        if markers:
            for m in markers:
                kind = m.get("kind", "")
                summary = str(m.get("summary", ""))[:160]
                date = str(m.get("recorded_at", ""))[:10]
                intensity = m.get("intensity", 0)
                output.append(f"- **[{date}] {kind}** (intensity {intensity:.2f}): {summary}")
        else:
            output.append("_(ingen markerede i denne periode)_")
    except Exception as exc:
        output.append(f"_(crisis check failed: {exc})_")
    output.append("")

    # 2. Baseline trajectory
    output.append("## 🌡 Personlighedsbaseline")
    try:
        from core.services.personality_drift import compute_baseline, detect_drift
        baseline = compute_baseline(lookback_days=args.days)
        drift = detect_drift(lookback_days=args.days)
        if baseline:
            for dim, info in sorted(baseline.items()):
                output.append(
                    f"- {dim}: mean={info.get('mean')} stdev={info.get('stdev')} (n={info.get('n')})"
                )
        else:
            output.append("_(ingen baseline-data endnu)_")
        if drift.get("drift_detected"):
            output.append("\n**⚠ Drift detected:**")
            for d in drift.get("drifts", []):
                output.append(
                    f"  - {d.get('dimension')}: {d.get('baseline_mean'):.2f} → "
                    f"{d.get('recent_mean'):.2f} (z={d.get('z_score'):+.1f}, {d.get('direction')})"
                )
    except Exception as exc:
        output.append(f"_(baseline check failed: {exc})_")
    output.append("")

    # 3. Long arcs
    output.append("## 🌀 Long arcs")
    try:
        from core.services.long_arc_synthesizer import list_arcs
        arcs = list_arcs()
        if arcs:
            for a in arcs[:5]:
                output.append(f"- {a.get('name')} ({a.get('bytes')} bytes, modified {a.get('modified', '')[:19]})")
        else:
            output.append("_(ingen arcs genereret endnu — first one kommer efter 28 dage)_")
    except Exception as exc:
        output.append(f"_(arc list failed: {exc})_")
    output.append("")

    # 4. Pending identity proposals
    output.append("## 📥 Pending identity proposals")
    try:
        from core.services.plan_proposals import _load_all
        plans = _load_all()
        identity_plans = [
            p for p in plans.values()
            if p.get("status") == "awaiting_approval"
            and "drift" in str(p.get("title", "")).lower()
        ]
        if identity_plans:
            for p in identity_plans:
                output.append(f"- **{p.get('plan_id')}**: {p.get('title')}")
                output.append(f"  Why: {str(p.get('why', ''))[:200]}")
        else:
            output.append("_(ingen identitets-forslag venter på godkendelse)_")
    except Exception as exc:
        output.append(f"_(plan check failed: {exc})_")
    output.append("")

    # 5. Tick quality summary (overall health)
    output.append("## 📊 Tick quality (overall health)")
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        s = tick_quality_summary(days=args.days)
        if s.get("count", 0) > 0:
            output.append(f"- Avg: {s.get('avg_score')}/100")
            output.append(f"- Last 5: {s.get('last_5_avg')}/100")
            output.append(f"- Trend: **{s.get('trend')}**")
            output.append(f"- Samples: {s.get('count')}")
        else:
            output.append("_(no tick evaluations yet)_")
    except Exception as exc:
        output.append(f"_(tick quality check failed: {exc})_")
    output.append("")

    # 6. Reminder if proposals pending
    output.append("---")
    pending_count = 0
    try:
        from core.services.plan_proposals import _load_all
        plans = _load_all()
        pending_count = sum(1 for p in plans.values() if p.get("status") == "awaiting_approval")
    except Exception:
        pass
    if pending_count > 0:
        output.append(f"**🔔 {pending_count} pending plan(s) waiting for your review.**")
        output.append("Run: `list_plans` to see all, then `approve_plan(plan_id)` or `dismiss_plan(plan_id)`.")
    else:
        output.append("✅ No pending plans — system observing autonomously.")

    text = "\n".join(output)

    # Write to log file
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        log_path = ensure_default_workspace() / "runtime" / "identity_formation_log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Append-only: keep a history
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n\n---\n\n")
    except Exception as exc:
        if not args.silent:
            print(f"(log write failed: {exc})", file=sys.stderr)

    if not args.silent:
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
