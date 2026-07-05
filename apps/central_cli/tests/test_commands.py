from __future__ import annotations
from central_cli.commands import resolve_command, CommandSpec


def test_read_verb_maps_to_get_endpoint():
    spec = resolve_command("status", [])
    assert spec == CommandSpec(method="GET", path="/central/realtime", body=None, write=False)


def test_timeseries_and_diag():
    assert resolve_command("series", []).path == "/central/timeseries"
    assert resolve_command("diag", []).path == "/central/diagnostics"


def test_nerve_toggle_is_write_post():
    spec = resolve_command("toggle", ["network/health", "off"])
    assert spec.method == "POST"
    assert spec.path == "/central/nerve/network/health/toggle"
    assert spec.write is True
    assert spec.body == {"enabled": False}


def test_central_command_backed_verb():
    spec = resolve_command("incidents", ["--filter", "network"])
    assert spec.method == "POST"
    assert spec.path == "/central/command"
    assert spec.body == {"line": "incidents --filter network"}


def test_approval_write():
    spec = resolve_command("approve", ["tool", "abc123"])
    assert spec.method == "POST"
    assert spec.path == "/mc/tool-intent/approve"
    assert spec.write is True
    assert spec.body == {"id": "abc123"}
