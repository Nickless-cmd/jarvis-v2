"""Tests for adaptive decay per domain (Feature 1)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest


# ---------------------------------------------------------------------------
# _record_type_to_domain mapping
# ---------------------------------------------------------------------------

def test_self_model_maps_to_identity():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("self-model-carry") == "identity"


def test_continuity_maps_to_identity():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("continuity-reinforce") == "identity"
    assert _record_type_to_domain("continuity-carry") == "identity"


def test_diary_maps_to_social():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("diary-carry") == "social"


def test_state_snapshot_maps_to_debug_context():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("state-snapshot-carry") == "debug_context"


def test_inner_note_maps_to_empty_default():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("inner-note-carry") == ""


def test_unknown_type_maps_to_empty_default():
    from apps.api.jarvis_api.services.session_distillation import _record_type_to_domain
    assert _record_type_to_domain("something-unknown") == ""


# ---------------------------------------------------------------------------
# DOMAIN_DECAY_RATES values
# ---------------------------------------------------------------------------

def test_identity_decay_slower_than_default():
    from apps.api.jarvis_api.services.memory_decay_daemon import DOMAIN_DECAY_RATES, _DECAY_RATE
    assert DOMAIN_DECAY_RATES["identity"] < _DECAY_RATE


def test_debug_context_decay_faster_than_default():
    from apps.api.jarvis_api.services.memory_decay_daemon import DOMAIN_DECAY_RATES, _DECAY_RATE
    assert DOMAIN_DECAY_RATES["debug_context"] > _DECAY_RATE


def test_all_required_domains_present():
    from apps.api.jarvis_api.services.memory_decay_daemon import DOMAIN_DECAY_RATES
    for domain in ("identity", "code_pattern", "social", "debug_context"):
        assert domain in DOMAIN_DECAY_RATES, f"Missing domain: {domain}"


def test_decay_rates_are_positive():
    from apps.api.jarvis_api.services.memory_decay_daemon import DOMAIN_DECAY_RATES
    for domain, rate in DOMAIN_DECAY_RATES.items():
        assert 0 < rate < 1.0, f"Rate {rate} for domain {domain!r} not in (0, 1)"


# ---------------------------------------------------------------------------
# decay_private_brain_records_by_domain
# ---------------------------------------------------------------------------

def test_domain_decay_applies_higher_rate_to_debug_context():
    """debug_context records should lose more salience per cycle than identity records."""
    from core.runtime.db import decay_private_brain_records_by_domain

    identity_rows = [{"record_id": "r1", "salience": 1.0, "domain": "identity"}]
    debug_rows = [{"record_id": "r2", "salience": 1.0, "domain": "debug_context"}]

    identity_rate = 0.023
    debug_rate = 0.347
    rates = {"identity": identity_rate, "debug_context": debug_rate}

    import sqlite3
    fake_conn = MagicMock()
    # Simulate the SELECT returning identity_rows then debug_rows combined
    all_rows = identity_rows + debug_rows

    # We'll call the function with a mocked connect()
    updated_calls = []

    def fake_execute(sql, params=()):
        if "SELECT" in sql:
            class FakeCursor:
                def fetchall(self_inner):
                    return [
                        {"record_id": r["record_id"], "salience": r["salience"], "domain": r["domain"]}
                        for r in all_rows
                    ]
            return FakeCursor()
        elif "UPDATE" in sql:
            updated_calls.append(params)
            return MagicMock()
        return MagicMock()

    fake_conn.execute = fake_execute
    fake_conn.commit = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_private_brain_records_table"):
        counts = decay_private_brain_records_by_domain(rates, default_rate=0.05)

    # identity → 1 record, debug_context → 1 record
    assert counts.get("identity", 0) == 1
    assert counts.get("debug_context", 0) == 1

    # Check the salience values written
    update_by_record = {params[2]: params[0] for params in updated_calls}
    assert abs(update_by_record["r1"] - (1.0 - identity_rate)) < 1e-9
    assert abs(update_by_record["r2"] - (1.0 - debug_rate)) < 1e-9


def test_domain_decay_uses_default_rate_for_unknown_domain():
    """Records with empty/unknown domain should use default_rate."""
    from core.runtime.db import decay_private_brain_records_by_domain

    rows = [{"record_id": "r-unknown", "salience": 0.8, "domain": ""}]
    default_rate = 0.05

    updated_calls = []

    fake_conn = MagicMock()

    def fake_execute(sql, params=()):
        if "SELECT" in sql:
            class FC:
                def fetchall(self_):
                    return [{"record_id": r["record_id"], "salience": r["salience"], "domain": r["domain"]}
                            for r in rows]
            return FC()
        elif "UPDATE" in sql:
            updated_calls.append(params)
            return MagicMock()
        return MagicMock()

    fake_conn.execute = fake_execute
    fake_conn.commit = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_private_brain_records_table"):
        counts = decay_private_brain_records_by_domain({}, default_rate=default_rate)

    assert counts.get("default", 0) == 1
    new_salience = updated_calls[0][0]
    assert abs(new_salience - (0.8 - default_rate)) < 1e-9


# ---------------------------------------------------------------------------
# tick_memory_decay_daemon uses domain-aware path
# ---------------------------------------------------------------------------

def test_tick_memory_decay_daemon_uses_domain_decay():
    """tick_memory_decay_daemon should call decay_private_brain_records_by_domain."""
    from apps.api.jarvis_api.services import memory_decay_daemon as mdd

    # Reset cadence gate so tick runs
    mdd._last_decay_at = None

    with patch.object(mdd, "decay_private_brain_records_by_domain",
                      return_value={"identity": 2, "debug_context": 1}) as mock_decay, \
         patch.object(mdd, "maybe_rediscover", return_value=None):
        result = mdd.tick_memory_decay_daemon()

    assert result["decayed"] is True
    assert result["records_updated"] == 3
    assert "domain_counts" in result
    mock_decay.assert_called_once()


# ---------------------------------------------------------------------------
# insert_private_brain_record passes domain through
# ---------------------------------------------------------------------------

def test_insert_private_brain_record_accepts_domain():
    """insert_private_brain_record should accept a domain kwarg without error."""
    from core.runtime.db import insert_private_brain_record

    fake_conn = MagicMock()
    fake_conn.execute.return_value = MagicMock()
    fake_conn.commit = MagicMock()
    fake_conn.__enter__ = lambda s: fake_conn
    fake_conn.__exit__ = MagicMock(return_value=False)

    with patch("core.runtime.db.connect", return_value=fake_conn), \
         patch("core.runtime.db._ensure_private_brain_records_table"), \
         patch("core.runtime.db.get_private_brain_record", return_value={"record_id": "r1", "domain": "identity"}):
        result = insert_private_brain_record(
            record_id="r1",
            record_type="self-model-carry",
            layer="private_brain",
            session_id="s1",
            run_id="",
            focus="identity focus",
            summary="I am Jarvis",
            detail="",
            source_signals="self-model:abc",
            confidence="high",
            created_at="2026-01-01T00:00:00+00:00",
            domain="identity",
        )

    assert result.get("domain") == "identity"
