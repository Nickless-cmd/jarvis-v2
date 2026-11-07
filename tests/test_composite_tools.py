"""Surface-test (dark-edges batch 1) — se tests/test_tool_infra_surfaces.py for moensteret."""
from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    """Frisk sqlite-DB som ALLE de steder surface'erne henter `connect` fra peger paa."""
    path = tmp_path / "jarvis.db"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    import core.runtime.db as dbmod
    import core.runtime.db_composites as dbc
    import core.runtime.db_core as dbcore
    import core.runtime.db_runtime_tasks as dbt
    import core.services.causal_inference_daemon as cid
    monkeypatch.setattr(dbmod, "connect", _connect)
    monkeypatch.setattr(dbcore, "connect", _connect)
    monkeypatch.setattr(dbc, "connect", _connect)
    monkeypatch.setattr(dbt, "connect", _connect)
    monkeypatch.setattr(cid, "connect", _connect)
    return _connect


def _ok(s, mode):
    assert s["mode"] == mode
    assert isinstance(s["signals"], dict)
    assert isinstance(s["summary"], str) and s["summary"]
    return s


def _inactive(s, mode, why):
    _ok(s, mode)
    assert s["active"] is False
    assert why in s["reason"], s["reason"]
    return s



# ── 9. composite_tools ───────────────────────────────────────────────────────

def test_composite_tools_surface(db):
    from core.runtime import db_composites as dbc
    from core.services import composite_tools as ct
    s = _inactive(ct.build_composite_tools_surface(), "composite-tools", "findes ikke endnu")
    assert s["signals"] == {}
    for n in ("alpha_tool", "beta_tool"):
        dbc.propose_composite(name=n, description="d", input_schema={}, steps=[{"tool": "x"}])
    s = _ok(ct.build_composite_tools_surface(), "composite-tools")
    assert (s["signals"]["total"], s["signals"]["proposed"], s["signals"]["approved"]) == (2, 2, 0)
    ct.approve("alpha_tool", approved_by="bjorn")
    dbc.record_invocation("alpha_tool")
    dbc.record_invocation("alpha_tool")
    ct.revoke("beta_tool")
    sig = ct.build_composite_tools_surface()["signals"]
    assert (sig["proposed"], sig["approved"], sig["revoked"], sig["invocations"]) == (0, 1, 1, 2)
    assert sig["top_invoked"] == [{"name": "alpha_tool", "count": 2}] and sig["last_invoked_at"]
    ct.delete("beta_tool")
    assert ct.build_composite_tools_surface()["signals"]["total"] == 1
