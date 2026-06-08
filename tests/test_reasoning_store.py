"""Tests for core.services.reasoning_store — minimal coverage.

Focus is on the 2026-06-08 fix: capture_conclusion(emit_event=True) must
call event_bus.publish() (not the non-existent event_bus.emit() that the
pre-fix code referenced — that would have raised AttributeError the first
time emit_event=True was ever passed).
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def stub_db(monkeypatch, tmp_path):
    """Patch connect() + is_enabled() so the store can be exercised without
    touching the real Jarvis DB. We don't care about the persisted row —
    we care that emit_event=True doesn't raise.
    """
    from core.services import reasoning_store

    # Fake connection: execute/commit are no-ops, close is a no-op.
    fake_conn = MagicMock()
    fake_conn.execute = MagicMock()
    fake_conn.commit = MagicMock()
    fake_conn.close = MagicMock()

    monkeypatch.setattr(reasoning_store, "connect", lambda: fake_conn)
    monkeypatch.setattr(reasoning_store, "_ensure_table", lambda conn: None)
    monkeypatch.setattr(reasoning_store, "is_enabled", lambda: True)

    return fake_conn


def test_capture_conclusion_emit_event_uses_publish(stub_db):
    """The fix: emit_event=True must call event_bus.publish (not .emit
    which doesn't exist on the bus).
    """
    from core.services import reasoning_store

    with patch.object(reasoning_store.event_bus, "publish") as mock_publish:
        cid = reasoning_store.capture_conclusion(
            source="test",
            conclusion_text="hello",
            confidence=0.5,
            emit_event=True,
        )

    assert cid is not None
    mock_publish.assert_called_once()
    call_kind = mock_publish.call_args.args[0]
    call_payload = mock_publish.call_args.args[1]
    assert call_kind == "reasoning.conclusion.captured"
    assert call_payload["source"] == "test"
    assert call_payload["confidence"] == 0.5
    assert call_payload["conclusion_id"] == cid


def test_capture_conclusion_emit_event_false_skips_publish(stub_db):
    """emit_event=False must not touch the bus at all."""
    from core.services import reasoning_store

    with patch.object(reasoning_store.event_bus, "publish") as mock_publish:
        cid = reasoning_store.capture_conclusion(
            source="test",
            conclusion_text="silent",
            emit_event=False,
        )

    assert cid is not None
    mock_publish.assert_not_called()


def test_capture_conclusion_disabled_returns_none(monkeypatch):
    """When the killswitch is off, capture_conclusion returns None and
    never touches the bus.
    """
    from core.services import reasoning_store

    monkeypatch.setattr(reasoning_store, "is_enabled", lambda: False)

    with patch.object(reasoning_store.event_bus, "publish") as mock_publish:
        cid = reasoning_store.capture_conclusion(
            source="test",
            conclusion_text="nope",
            emit_event=True,
        )

    assert cid is None
    mock_publish.assert_not_called()


def test_event_bus_has_publish_not_emit():
    """Regression guard: the bus must expose publish(), not emit().

    The pre-fix code in reasoning_store.py called event_bus.emit() which
    doesn't exist. If someone re-introduces .emit() on the bus without
    aliasing it to publish(), this test won't catch it — but if someone
    removes .publish(), it will fail loudly.
    """
    from core.eventbus.bus import event_bus

    assert hasattr(event_bus, "publish")
    assert callable(event_bus.publish)
