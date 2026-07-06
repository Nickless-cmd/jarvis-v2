"""Blinde vinkler lukket 6. jul (multi-agent audit): compact_ground_truth + process_watcher.

Invarianter:
  * compaction-validering emitter et METADATA-ONLY signal (ingen rå claim/kontekst-tekst).
  * begge nye families er i FAMILY_ROUTES OG ikke i PRIVATE-blocklisten.
"""
from __future__ import annotations

from unittest import mock

from core.services import eventbus_central_bridge as bridge


def test_new_families_in_routes_and_not_private():
    routes = bridge.FAMILY_ROUTES
    assert routes.get("compaction") == ("truth", "validation")
    assert routes.get("process_watcher") == ("system", "watch_match")
    # må ALDRIG samtidig være privat-ekskluderet (ville være selvmodsigende egress-regel)
    assert "compaction" not in bridge.PRIVATE_FAMILIES_EXCLUDED_M0
    assert "process_watcher" not in bridge.PRIVATE_FAMILIES_EXCLUDED_M0


def test_validation_failure_emits_metadata_only():
    """_log_validation_failure emitter compaction.validation_failed UDEN rå claim-tekst."""
    import core.context.compact_ground_truth as cgt

    failures = [
        {"pattern": "p1", "context": "HEMMELIG privat kontekst der IKKE må lække",
         "evidence": "fil findes", "confidence": "high"},
        {"pattern": "p2", "context": "mere privat", "evidence": "x", "confidence": "low"},
    ]

    published: list = []

    class _FakeConn:
        def execute(self, *a, **k):
            class _Cur:
                def fetchone(_self):
                    return [42]
            return _Cur()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    class _FakeBus:
        def publish(self, family, payload):
            published.append((family, payload))

    with mock.patch.object(cgt, "_ensure_compaction_validation_table", lambda: None), \
            mock.patch("core.runtime.db.connect", return_value=_FakeConn()), \
            mock.patch("core.eventbus.bus.event_bus", _FakeBus()):
        row = cgt._log_validation_failure("sess-1", "marker-1", failures)

    assert row == 42
    assert len(published) == 1
    family, payload = published[0]
    assert family == "compaction.validation_failed"
    # metadata-only: kun tællere + id'er, ALDRIG rå claim/kontekst/evidens-tekst (§24.4)
    assert payload == {"session_id": "sess-1", "marker_id": "marker-1",
                       "failure_count": 2, "high_confidence": 1, "row_id": 42}
    blob = str(payload)
    assert "HEMMELIG" not in blob and "privat" not in blob and "kontekst" not in blob
