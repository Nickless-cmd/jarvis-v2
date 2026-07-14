"""Tests for the Fase 5 Task 9 audit trail: apps/api/jarvis_api/routes/
agent_audit.py (record_if_enabled + GET /v1/agent/audit) and
core/runtime/db_agent_audit.py (write_row/read_rows), flag-gated by
jc_audit_trail (default OFF)."""
import asyncio

import pytest

from apps.api.jarvis_api.routes import agent_audit
from apps.api.jarvis_api.routes import agent_loop
from core.runtime import db_agent_audit


class _FakeConn:
    """In-memory sqlite so tests never touch the real runtime DB."""
    def __init__(self):
        import sqlite3
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self._conn

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_db(monkeypatch):
    conn_holder = _FakeConn()
    monkeypatch.setattr(db_agent_audit, "connect", lambda: conn_holder)
    return conn_holder


class TestWriteReadRows:
    def test_audit_row_written_and_read_back(self, fake_db):
        ok = db_agent_audit.write_row(user_id="u1", role="guest", tool="write_file",
                                      target_summary="/x", decision="allow")
        assert ok is True
        rows = db_agent_audit.read_rows(user_id="u1")
        assert len(rows) == 1
        assert rows[0]["tool"] == "write_file"
        assert rows[0]["decision"] == "allow"

    def test_audit_distinct_from_cost(self, fake_db):
        """A row is written with no cost information at all — distinct
        record type from the cost-nerve."""
        db_agent_audit.write_row(user_id="u1", role="owner", tool="read_file", decision="allow")
        rows = db_agent_audit.read_rows()
        assert len(rows) == 1
        assert "cost" not in rows[0]
        assert "cost_usd" not in rows[0]


class TestRecordIfEnabled:
    def test_audit_row_written_when_flag_on(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_audit, "_flag", lambda name, default=False: name == "jc_audit_trail")
        agent_audit.record_if_enabled(user_id="u1", role="guest", tool="bash",
                                      target_summary="rm -rf", decision="deny")
        rows = db_agent_audit.read_rows()
        assert len(rows) == 1
        assert rows[0]["decision"] == "deny"

    def test_no_audit_when_flag_off(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_audit, "_flag", lambda name, default=False: False)
        agent_audit.record_if_enabled(user_id="u1", role="guest", tool="bash", decision="deny")
        rows = db_agent_audit.read_rows()
        assert rows == []


class TestOwnerOnlyReadback:
    def test_audit_readback_owner_only(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_audit, "_resolve_role", lambda: "guest", raising=False)
        monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "guest")
        with pytest.raises(Exception) as exc_info:
            asyncio.run(agent_audit.agent_audit(user_id=None, limit=100))
        assert getattr(exc_info.value, "status_code", None) == 403

    def test_owner_can_read(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "owner")
        db_agent_audit.write_row(user_id="u1", role="owner", tool="bash", decision="allow")
        result = asyncio.run(agent_audit.agent_audit(user_id=None, limit=100))
        assert result["count"] == 1


class TestToolsExecuteWiring:
    def test_deny_path_records_audit_when_flag_on(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "guest")
        monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
        monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: False)
        monkeypatch.setattr("core.services.gate_verdict_ledger.record", lambda **kw: None)
        monkeypatch.setattr(agent_audit, "_flag", lambda name, default=False: name == "jc_audit_trail")
        body = agent_loop._ExecBody(name="write_file", arguments={"path": "/x"}, user_id="u1")
        with pytest.raises(Exception):
            asyncio.run(agent_loop.tools_execute(body))
        rows = db_agent_audit.read_rows(user_id="u1")
        assert len(rows) == 1
        assert rows[0]["decision"] == "deny"

    def test_deny_path_no_audit_when_flag_off(self, fake_db, monkeypatch):
        monkeypatch.setattr(agent_loop, "_resolve_role", lambda: "guest")
        monkeypatch.setattr(agent_loop, "unalias", lambda n: n)
        monkeypatch.setattr(agent_loop, "check_brain_write_allowed", lambda name, role: False)
        monkeypatch.setattr("core.services.gate_verdict_ledger.record", lambda **kw: None)
        monkeypatch.setattr(agent_audit, "_flag", lambda name, default=False: False)
        body = agent_loop._ExecBody(name="write_file", arguments={"path": "/x"}, user_id="u1")
        with pytest.raises(Exception):
            asyncio.run(agent_loop.tools_execute(body))
        assert db_agent_audit.read_rows() == []
