from __future__ import annotations
from central_cli import __version__
from central_cli.main import build_arg_parser


def test_version_present():
    assert isinstance(__version__, str) and __version__


def test_arg_parser_has_core_flags():
    p = build_arg_parser()
    ns = p.parse_args(["--script", "status", "--json"])
    assert ns.script is True
    assert ns.command == "status"
    assert ns.json is True
    ns2 = p.parse_args([])
    assert ns2.command is None  # ingen kommando → TUI-mode
