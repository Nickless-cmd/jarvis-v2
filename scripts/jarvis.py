#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db


def cmd_bootstrap(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    workspace = ensure_default_workspace()
    event_bus.publish("cli.bootstrap", {"workspace": str(workspace)})
    print(f"Bootstrapped workspace: {workspace}")


def cmd_events(args: argparse.Namespace) -> None:
    items = event_bus.recent(limit=args.limit)
    print(json.dumps(items, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.set_defaults(func=cmd_bootstrap)

    events = sub.add_parser("events")
    events.add_argument("--limit", type=int, default=20)
    events.set_defaults(func=cmd_events)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
