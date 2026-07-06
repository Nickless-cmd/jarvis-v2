import sqlite3
from unittest import mock

import pytest

from core.services import central_keymaker as km


@pytest.fixture
def tmpdb(tmp_path):
    """Peg keymaker's connect() på en midlertidig fil-DB (persisterer mellem kald i testen)."""
    path = str(tmp_path / "km.db")

    def _connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    with mock.patch("core.services.central_keymaker.connect", side_effect=_connect):
        yield


def test_earns_key_only_at_volume_and_zero_nongreen(tmpdb):
    fake = {
        "veto": {"cluster": "commit", "total": 124, "green": 124},          # ≥100, 0 fejl → OPTJENER
        "decision_gate": {"cluster": "commit", "total": 40, "green": 40},    # <100 → for lidt volumen
        "memory_promotion": {"cluster": "memory", "total": 500, "green": 90},  # fejl → nej
    }
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        out = km.evaluate_keys()
    domains = {e["domain"] for e in out["earned"]}
    assert domains == {"decentralize:veto"}
    issued = {e["domain"] for e in out["issued"]}
    assert issued == {"decentralize:veto"}


def test_security_gate_never_earns_key(tmpdb):
    fake = {"cross_user_share": {"cluster": "privacy", "total": 5000, "green": 5000}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        out = km.evaluate_keys()
    assert out["earned"] == [] and out["issued"] == []


def test_no_duplicate_pending_key(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        km.evaluate_keys()
        second = km.evaluate_keys()
    assert second["issued"] == []            # allerede pending → udsteder ikke igen
    assert [e["domain"] for e in second["earned"]] == ["decentralize:veto"]
    assert len([k for k in km.list_keys() if k["domain"] == "decentralize:veto"]) == 1


def test_approve_flips_flag_and_sets_ttl(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    flips = []
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled",
                       side_effect=lambda s, n, e: flips.append((s, n, e))):
        km.evaluate_keys()
        key_id = km.list_keys()[0]["id"]
        res = km.approve_key(key_id)
    assert res["ok"] and res["domain"] == "decentralize:veto"
    assert flips == [("decentralize", "veto", True)]
    row = [k for k in km.list_keys() if k["id"] == key_id][0]
    assert row["status"] == "approved" and row["expires_at"]


def test_approve_unknown_id_is_safe(tmpdb):
    with mock.patch("core.services.central_keymaker._observe"):
        res = km.approve_key(9999)
    assert res["ok"] is False


def test_expire_due_reverts_flag(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    flips = []
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled",
                       side_effect=lambda s, n, e: flips.append((s, n, e))):
        km.evaluate_keys()
        key_id = km.list_keys()[0]["id"]
        km.approve_key(key_id)
        # tving udløb i fortiden
        import sqlite3 as _s
        conn = km.connect()
        conn.execute("UPDATE central_keys SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                     (key_id,))
        conn.commit()
        conn.close()
        out = km.expire_due()
    assert out["expired"] == 1
    assert ("decentralize", "veto", False) in flips
    row = [k for k in km.list_keys(include_expired=True) if k["id"] == key_id][0]
    assert row["status"] == "expired"
