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
    # `--message` sender prosaen gennem SKALLEN, og enhver metategn i en
    # dobbelt-citeret streng bliver tolket. Maalt 11/9-2026: tre backtick-
    # citerede navne i én besked blev koert som kommando-substitution —
    # `permission_axes` og `--stat` forsvandt HELT, `4009d48c5` blev halveret.
    # Commit'en gik igennem med exit 0; fejlen stod kun paa stderr, og `--amend`
    # er blokeret af hookene, saa beskeden kan ikke rettes bagefter.
    #
    # `--message "$(cat fil)"` har vaeret vanen og har virket i 7.951 commits,
    # men det er en OMGAAELSE af et manglende interface, ikke en kur: prosaen
    # gaar stadig gennem skallen. `--message-file` lader den aldrig roere den.
    _besked = parser.add_mutually_exclusive_group(required=True)
    _besked.add_argument("--message")
    _besked.add_argument("--message-file",
                         help="sti til beskeden; laeses som UTF-8 og roerer aldrig skallen")
    parser.add_argument("--actor", required=True, choices=sorted(ACTOR_REGISTRY))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--session-id", default="none")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--author", default="")
    parser.add_argument("--amend", action="store_true")
    return parser


def _laes_besked(args) -> str:
    """Beskeden, uanset hvilken vej den kom ind."""
    if getattr(args, "message_file", None):
        from pathlib import Path
        return Path(args.message_file).read_text(encoding="utf-8")
    return args.message


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
        message=_laes_besked(args),
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
