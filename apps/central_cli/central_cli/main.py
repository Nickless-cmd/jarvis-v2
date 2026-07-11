from __future__ import annotations

import argparse

from central_cli import __version__


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="central", description="Central CLI")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--remote", metavar="URL", default=None, help="API base-url (override)")
    p.add_argument("--script", action="store_true", help="Ingen TUI — kør én kommando + exit")
    p.add_argument("--json", action="store_true", help="Rå JSON-output")
    p.add_argument("--no-boot", action="store_true", help="Skip boot-animation")
    p.add_argument("command", nargs="?", default=None, help="Kommando (kun i --script)")
    p.add_argument("args", nargs="*", help="Kommando-argumenter")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    ns = parser.parse_args(argv)
    if ns.script or ns.command:
        from central_cli.script_runner import run_script
        return run_script(ns)
    from central_cli.hud import run_hud
    return run_hud(ns)


if __name__ == "__main__":
    raise SystemExit(main())
