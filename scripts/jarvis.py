#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from core.costing.ledger import telemetry_summary
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.config import SETTINGS_FILE
from core.runtime.db import connect, init_db
from core.runtime.settings import load_settings


def cmd_bootstrap(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    workspace = ensure_default_workspace()
    event_bus.publish("runtime.bootstrap", {"workspace": str(workspace)})
    print(f"Bootstrapped workspace: {workspace}")


def cmd_events(args: argparse.Namespace) -> None:
    items = event_bus.recent(limit=args.limit)
    print(json.dumps(items, indent=2, ensure_ascii=False))


def cmd_health(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    settings = load_settings()
    print(
        json.dumps(
            {
                "ok": True,
                "app": settings.app_name,
                "environment": settings.environment,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_overview(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    costs = telemetry_summary()
    items = event_bus.recent(limit=1)
    print(
        json.dumps(
            {
                "ok": True,
                "events": _event_count(),
                "cost_rows": costs["cost_rows"],
                "input_tokens": costs["input_tokens"],
                "output_tokens": costs["output_tokens"],
                "total_cost_usd": costs["total_cost_usd"],
                "visible_execution": visible_execution_readiness(),
                "latest_event": items[0] if items else None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_config(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    settings = load_settings()
    print(
        json.dumps(
            {
                "path": str(SETTINGS_FILE),
                "settings": settings.to_dict(),
                "visible_execution": visible_execution_readiness(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_workspace(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    workspace = ensure_default_workspace(name=args.name)
    files = sorted(path.name for path in workspace.iterdir() if path.is_file())
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "exists": workspace.exists(),
                "files": files,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.set_defaults(func=cmd_bootstrap)

    events = sub.add_parser("events")
    events.add_argument("--limit", type=int, default=20)
    events.set_defaults(func=cmd_events)

    health = sub.add_parser("health")
    health.set_defaults(func=cmd_health)

    overview = sub.add_parser("overview")
    overview.set_defaults(func=cmd_overview)

    config = sub.add_parser("config")
    config.set_defaults(func=cmd_config)

    workspace = sub.add_parser("workspace")
    workspace.add_argument("--name", default="default")
    workspace.set_defaults(func=cmd_workspace)

    return parser


def _event_count() -> int:
    with connect() as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"])


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
