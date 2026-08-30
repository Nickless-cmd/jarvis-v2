#!/usr/bin/env python3
"""CLI for creating a Git commit with canonical actor attribution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.services.attributed_git_commit import commit_with_attribution
from core.services.commit_attribution import (
    ACTOR_REGISTRY,
    CommitAttribution,
    new_manual_run_id,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--message", required=True)
    parser.add_argument("--actor", required=True, choices=sorted(ACTOR_REGISTRY))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--session-id", default="none")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--author", default="")
    parser.add_argument("--amend", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    rule = ACTOR_REGISTRY[args.actor]
    attribution = CommitAttribution(
        actor=args.actor,
        actor_type=rule.actor_type,
        run_id=args.run_id or new_manual_run_id(),
        session_id=args.session_id or "none",
        origin=args.origin,
        approved_by=args.approved_by,
    )
    result = commit_with_attribution(
        repo=Path(args.repo),
        message=args.message,
        attribution=attribution,
        paths=tuple(args.path),
        author=args.author,
        amend=args.amend,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode == 0 and result.sha:
        print(f"commit={result.sha}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
