import sqlite3
from unittest import mock
import pytest
from core.services import central_surgery as cs


@pytest.fixture
def tmpdb(tmp_path):
    path = str(tmp_path / "surg.db")

    def _connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    with mock.patch("core.services.central_surgery.connect", side_effect=_connect), \
            mock.patch("core.services.central_surgery._observe"):
        yield


def test_assess_flags_self_image_and_blast():
    with mock.patch("core.services.central_surgery._blast_count", return_value=15), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="")
        a = cs.assess_risk("core/services/central_self_state.py")
    assert a["self_image"] is True and a["risk"] == "high" and a["blast_files"] == 15


def test_assess_frozen_core_blocks():
    with mock.patch("core.services.central_surgery._blast_count", return_value=2), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="block")
        a = cs.assess_risk("core/runtime/db.py")
    assert a["protected"] is True and a["risk"] == "frozen"


def test_low_risk_small_blast():
    with mock.patch("core.services.central_surgery._blast_count", return_value=1), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="")
        a = cs.assess_risk("core/services/some_leaf.py")
    assert a["risk"] == "low"


def test_pipeline_proposed_verified_escalated(tmpdb):
    with mock.patch("core.services.central_surgery._blast_count", return_value=4), \
            mock.patch("core.services.central_surgery._is_tested", return_value=True), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="")
        p = cs.propose_surgery("core/services/central_echo_breaker.py", rationale="forenkl")
        assert p["ok"] and p["risk"] == "medium"
        pid = p["id"]
        assert cs.simulate(pid)["tested"] is True
        assert cs.verify(pid)["status"] == "verified"
        assert cs.escalate(pid)["status"] == "escalated"
    rows = cs.list_proposals()
    assert rows[0]["status"] == "escalated"


def test_verify_blocks_frozen_core(tmpdb):
    with mock.patch("core.services.central_surgery._blast_count", return_value=50), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="block")
        pid = cs.propose_surgery("core/runtime/db.py")["id"]
        v = cs.verify(pid)
    assert v["status"] == "blocked"


def test_cannot_escalate_unverified(tmpdb):
    with mock.patch("core.services.central_surgery._blast_count", return_value=1), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="")
        pid = cs.propose_surgery("core/services/x.py")["id"]
        # proposed → escalate skal afvises (kun verified/simulated kan)
        assert cs.escalate(pid)["ok"] is False


def test_snapshot_and_rollback_roundtrip(tmpdb, tmp_path):
    f = tmp_path / "leaf.py"
    f.write_text("original = 1\n")
    with mock.patch("core.services.central_surgery._REPO", str(tmp_path)), \
            mock.patch("core.services.central_surgery._blast_count", return_value=0), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="")
        snap = cs.snapshot_file("leaf.py")
        assert snap["ok"]
        f.write_text("BROKEN\n")                       # simulér et indgreb
        res = cs.rollback(snap["snapshot_id"])
        assert res["ok"]
    assert f.read_text() == "original = 1\n"            # atomisk gendannet


def test_rollback_refuses_frozen_core(tmpdb, tmp_path):
    f = tmp_path / "db.py"
    f.write_text("x = 1\n")
    with mock.patch("core.services.central_surgery._REPO", str(tmp_path)), \
            mock.patch("core.services.gate_mutation.mutation_gate") as mg:
        mg.return_value = mock.MagicMock(action="block")   # frossen
        # snapshot (læsning) tilladt, men rollback (skrivning) nægtes
        with mock.patch("core.services.central_surgery.assess_risk", return_value={"protected": False}):
            snap = cs.snapshot_file("db.py")
        res = cs.rollback(snap["snapshot_id"])
    assert res["ok"] is False and "frossen" in res["error"]
