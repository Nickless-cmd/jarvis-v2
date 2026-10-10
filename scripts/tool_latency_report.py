#!/usr/bin/env python3
"""Read-only report for visible tool latency and prompt assembly cache behavior."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
KINDS = ("tool.execution_timing", "prompt.assembly_cache", "prompt.assembly_size")
WAIT_STAGES = (
    "bridge_or_spawn",
    "process",
    "result_surface",
    "shell_lock",
    "unattributed",
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 3)


def _stats(values: list[float]) -> dict[str, float | None]:
    return {
        "p50": _percentile(values, 0.50),
        "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95),
        "max": round(max(values), 3) if values else None,
    }


def _dominant_wait(payload: dict[str, Any]) -> str:
    candidates = {
        "shell_lock": _number(payload.get("dispatch_to_lock_ms")),
        "bridge_or_spawn": _number(payload.get("dispatch_to_spawn_ms")),
        "process": _number(payload.get("process_ms")),
        "result_surface": _number(payload.get("process_exit_to_result_emit_ms")),
    }
    measured = [(stage, value) for stage, value in candidates.items() if value is not None]
    if not measured:
        return "unattributed"
    return max(measured, key=lambda item: item[1])[0]


def aggregate(events: Iterable[dict], *, slow_ms: int = 500) -> dict[str, Any]:
    """Aggregate already-decoded event rows without changing runtime state."""
    durations: list[float] = []
    routes: Counter[str] = Counter()
    dominant: Counter[str] = Counter()
    cache_outcomes: Counter[str] = Counter()
    cache_phases: Counter[str] = Counter()
    process_roles: Counter[str] = Counter()
    cache_keys: Counter[str] = Counter()
    cache_processes: Counter[str] = Counter()
    cache_builds: list[float] = []
    assembly_builds: list[float] = []
    slow_calls = 0

    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("payload"), dict):
            continue
        kind = str(event.get("kind") or "")
        payload = event["payload"]
        if kind == "tool.execution_timing":
            total = _number(payload.get("total_visible_ms"))
            if total is None:
                continue
            durations.append(total)
            routes[str(payload.get("route") or "unknown")] += 1
            if total >= slow_ms:
                slow_calls += 1
                dominant[_dominant_wait(payload)] += 1
        elif kind == "prompt.assembly_cache":
            cache_outcomes[str(payload.get("cache_outcome") or "unknown")] += 1
            cache_phases[str(payload.get("caller_phase") or "unknown")] += 1
            role = str(payload.get("process_role") or "unknown")
            process_roles[role] += 1
            cache_keys[str(payload.get("key_hash") or "unknown")] += 1
            cache_processes[f"{role}:{payload.get('pid') or 'unknown'}"] += 1
            build = _number(payload.get("build_ms"))
            if build is not None:
                cache_builds.append(build)
        elif kind == "prompt.assembly_size":
            build = _number(payload.get("assembly_ms"))
            if build is not None:
                assembly_builds.append(build)

    return {
        "calls": len(durations),
        "slow_calls": slow_calls,
        "slow_ms": int(slow_ms),
        "duration_ms": _stats(durations),
        "routes": dict(sorted(routes.items())),
        "dominant_wait_stage": {
            stage: dominant.get(stage, 0) for stage in WAIT_STAGES
        },
        "prompt_cache": {
            "events": sum(cache_outcomes.values()),
            "outcomes": dict(sorted(cache_outcomes.items())),
            "phases": dict(sorted(cache_phases.items())),
            "process_roles": dict(sorted(process_roles.items())),
            "key_hashes": dict(sorted(cache_keys.items())),
            "processes": dict(sorted(cache_processes.items())),
            "build_ms": _stats(cache_builds),
        },
        "prompt_builds": {
            "events": len(assembly_builds),
            "assembly_ms": _stats(assembly_builds),
        },
    }


def load_events(*, days: int, db_path: Path = DB) -> list[dict[str, Any]]:
    """Read only the three report event kinds from a rolling UTC window."""
    if not db_path.exists():
        return []
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    placeholders = ",".join("?" for _ in KINDS)
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) AND created_at >= ? ORDER BY created_at",
            (*KINDS, since),
        ).fetchall()
    finally:
        connection.close()
    decoded: list[dict[str, Any]] = []
    for kind, payload_json, created_at in rows:
        try:
            payload = json.loads(payload_json or "{}")
        except (TypeError, ValueError):  # Historical malformed rows are omitted from this read-only report.
            continue
        if isinstance(payload, dict):
            decoded.append({"kind": str(kind), "payload": payload, "created_at": created_at})
    return decoded


def _fmt_stats(stats: dict[str, float | None]) -> str:
    return " ".join(
        f"{key}={('-' if value is None else f'{value:.1f}ms')}"
        for key, value in stats.items()
    )


def _print_text(report: dict[str, Any], *, days: int) -> None:
    print(f"window={days}d calls={report['calls']} slow>={report['slow_ms']}ms={report['slow_calls']}")
    print(f"tool total: {_fmt_stats(report['duration_ms'])}")
    print(f"routes: {report['routes']}")
    print(f"slow-call dominant wait: {report['dominant_wait_stage']}")
    cache = report["prompt_cache"]
    print(f"prompt cache: events={cache['events']} outcomes={cache['outcomes']} "
          f"phases={cache['phases']} roles={cache['process_roles']}")
    print(f"prompt cache keys/processes: keys={cache['key_hashes']} processes={cache['processes']}")
    print(f"prompt cache builds: {_fmt_stats(cache['build_ms'])}")
    builds = report["prompt_builds"]
    print(f"prompt assembly builds: events={builds['events']} {_fmt_stats(builds['assembly_ms'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--slow-ms", type=int, default=500)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--db", type=Path, default=DB, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.days < 1 or args.slow_ms < 0:
        parser.error("--days must be >= 1 and --slow-ms must be >= 0")
    report = aggregate(load_events(days=args.days, db_path=args.db), slow_ms=args.slow_ms)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(report, days=args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
