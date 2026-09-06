"""Task 3 (memory repair 2026-09-04): one generalized policy per rule key."""
from __future__ import annotations

import sqlite3
from unittest.mock import patch


def test_abstract_rule_reinforces_instead_of_duplicating(tmp_path):
    from core.services import policy_abstraction as pa

    db = tmp_path / "t.sqlite"

    def _connect():
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        return c

    fake_llm = lambda **kw: {"generalized_principle": "In tool workflows: synthesize before expanding.", "abstraction_level": "medium", "transfer_domains": ["tool-operations"], "confidence": 0.7}
    with patch.object(pa, "connect", _connect), patch.object(pa, "_llm_generalize", fake_llm), \
         patch.object(pa, "is_enabled", lambda: True), patch.object(pa.event_bus, "publish", lambda *a, **k: None):
        first = pa.abstract_rule(rule_key="synthesize-after-tool-burst", policy="p", lesson="l",
                                 target_context="tool-operations", evidence_count=3, confidence=0.9)
        second = pa.abstract_rule(rule_key="synthesize-after-tool-burst", policy="p", lesson="l",
                                  target_context="tool-operations", evidence_count=4, confidence=0.95)
    assert first["status"] == "created"
    assert second["status"] == "reinforced"
    c = _connect()
    rows = c.execute("SELECT specific_rule_key, match_count FROM generalized_policies").fetchall()
    assert len(rows) == 1
    assert rows[0]["match_count"] == 1
