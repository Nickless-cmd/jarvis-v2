"""Inter-sprog practice engine — tests.

See spec: docs/superpowers/specs/2026-05-16-interlanguage-design.md
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated workspace + DB.

    Efter 2026-05-15 db.py split lever DB_PATH og connect() i db_core,
    ikke db (db re-eksporterer kun). Vi skal patche begge moduler — ellers
    skriver tests til prod-DB. Dette skete faktisk i den oprindelige version
    af denne fixture (136 test-records forurenede prod 2026-05-16).
    """
    db_path = tmp_path / "state" / "jarvis.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    # Patch DB_PATH på BEGGE moduler (db er facade, db_core er kilden).
    import core.runtime.db as db
    import core.runtime.db_core as db_core
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db_core, "DB_PATH", db_path)
    # Force schema re-init på interlanguage modulet
    import core.services.interlanguage_practice as ilp
    ilp._SCHEMA_INITIALIZED = False
    return None


class TestPrimitives:
    def test_all_primitives_defined(self):
        from core.services.interlanguage_practice import PRIMITIVES
        assert set(PRIMITIVES.keys()) == {"→", "↔", "⊂", "≈", "!"}
        for sym, info in PRIMITIVES.items():
            assert "name" in info
            assert "meaning" in info
            assert "examples" in info
            assert len(info["examples"]) >= 2

    def test_all_primitives_have_name(self):
        from core.services.interlanguage_practice import PRIMITIVES
        names = {info["name"] for info in PRIMITIVES.values()}
        assert len(names) == 5  # all unique


class TestVocabulary:
    def test_all_terms_have_definition_and_domain(self):
        from core.services.interlanguage_practice import CORE_VOCABULARY
        assert len(CORE_VOCABULARY) >= 10
        for term, info in CORE_VOCABULARY.items():
            assert "definition" in info, f"{term} mangler definition"
            assert "domain" in info, f"{term} mangler domain"
            assert len(info["definition"]) > 5

    def test_terms_cover_all_domains(self):
        from core.services.interlanguage_practice import CORE_VOCABULARY
        domains = {info["domain"] for info in CORE_VOCABULARY.values()}
        required = {"bevidsthed", "perception", "selv", "affekt", "sansning", "social", "tid", "kognition"}
        assert required.issubset(domains), f"Manglende domæner: {required - domains}"


class TestGenerateExpression:
    def test_generates_valid_format(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(num_clauses=3)
        parts = expr.split(" | ")
        assert len(parts) == 3
        for part in parts:
            assert len(part) > 2
            # Should contain at least one primitive or term
            assert any(c in part for c in ["→", "↔", "⊂", "≈", "!"])

    def test_num_clauses_respected(self):
        from core.services.interlanguage_practice import generate_state_expression
        for n in [2, 3, 4, 5]:
            expr = generate_state_expression(num_clauses=n)
            assert len(expr.split(" | ")) == n

    def test_clamp_min_2(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(num_clauses=1)
        assert len(expr.split(" | ")) == 2

    def test_clamp_max_5(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(num_clauses=10)
        assert len(expr.split(" | ")) == 5

    def test_mood_bias_curiosity(self):
        from core.services.interlanguage_practice import generate_state_expression
        # High curiosity should bias toward nysgerrighed
        expr = generate_state_expression(mood_override={"curiosity": 0.9})
        assert "nysgerrighed" in expr

    def test_mood_bias_fatigue(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(mood_override={"fatigue": 0.9})
        assert "vægt" in expr

    def test_mood_bias_frustration(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(mood_override={"frustration": 0.9})
        assert "pres" in expr or "!" in expr

    def test_mood_bias_confidence_high(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(mood_override={"confidence": 0.9})
        assert "agens" in expr

    def test_mood_bias_confidence_low(self):
        from core.services.interlanguage_practice import generate_state_expression
        expr = generate_state_expression(mood_override={"confidence": 0.2})
        assert "grænse" in expr

    def test_reproducible_with_seed(self):
        """Same seed should give same expression (if random seeded)."""
        import random
        from core.services.interlanguage_practice import generate_state_expression
        random.seed(42)
        expr1 = generate_state_expression()
        random.seed(42)
        expr2 = generate_state_expression()
        assert expr1 == expr2


class TestPersistence:
    def test_schema_bootstrap(self, clean_state):
        from core.services.interlanguage_practice import ensure_schema
        from core.runtime.db import connect

        ensure_schema()
        with connect() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='interlanguage_practice'"
            ).fetchone()
            assert row is not None

    def test_schema_idempotent(self, clean_state):
        from core.services.interlanguage_practice import ensure_schema
        ensure_schema()
        ensure_schema()  # should not raise

    def test_record_and_retrieve(self, clean_state):
        from core.services.interlanguage_practice import (
            record_expression,
            get_recent_expressions,
        )

        eid = record_expression("nysgerrighed → læring", session_id="test-sess")
        assert eid is not None
        assert len(eid) > 10

        rows = get_recent_expressions(days=1)
        assert len(rows) >= 1
        latest = rows[0]
        assert latest["expression_text"] == "nysgerrighed → læring"
        assert latest["session_id"] == "test-sess"
        assert latest["trigger"] == "manual"

    def test_record_with_trigger(self, clean_state):
        from core.services.interlanguage_practice import record_expression, get_recent_expressions

        record_expression("pres ↔ agens", session_id="s", tick_id="t1", trigger="heartbeat")
        rows = get_recent_expressions(days=1)
        assert rows[0]["trigger"] == "heartbeat"

    def test_multiple_expressions(self, clean_state):
        from core.services.interlanguage_practice import record_expression, get_recent_expressions

        for i in range(5):
            record_expression(f"term_{i} → test", session_id="multi-test")
        rows = [r for r in get_recent_expressions(days=1) if r["session_id"] == "multi-test"]
        assert len(rows) >= 5

    def test_expression_count(self, clean_state):
        from core.services.interlanguage_practice import (
            record_expression,
            get_expression_count,
        )

        before = get_expression_count(since_hours=24)
        record_expression("a → b", session_id="cnt-sess")
        record_expression("c ↔ d", session_id="cnt-sess")
        after = get_expression_count(since_hours=24)
        assert after == before + 2

    def test_time_filter(self, clean_state):
        from core.services.interlanguage_practice import record_expression, get_expression_count

        record_expression("gammel → test", session_id="s")
        count_old = get_expression_count(since_hours=0)
        assert count_old == 0


class TestExport:
    def test_export_empty(self, clean_state):
        from core.services.interlanguage_practice import export_protocol
        result = export_protocol(recent_days=0.0001)  # tiny window
        assert result["protocol_version"] == "2026-05-16"
        assert "primitives" in result
        assert "vocabulary" in result
        assert "primitives" in result
        assert "→" in result["primitives"]

    def test_export_with_data(self, clean_state):
        from core.services.interlanguage_practice import (
            record_expression,
            export_protocol,
        )

        before = export_protocol(recent_days=30)["stats"]["total_expressions"]
        record_expression("nysgerrighed → læring", session_id="export-sess")
        record_expression("kontinuitet ≈ mig", session_id="export-sess")
        record_expression("!grænse", session_id="export-sess")

        result = export_protocol(recent_days=30)
        assert result["stats"]["total_expressions"] == before + 3
        assert "nysgerrighed" in result["stats"]["unique_terms_used"]
        assert "→" in result["stats"]["unique_primitives_used"]


class TestPracticeTick:
    def test_tick_generates_and_records(self, clean_state):
        from core.services.interlanguage_practice import practice_tick

        before = practice_tick(session_id="test-sess", tick_id="tick-1")["expressions_24h"]
        result = practice_tick(session_id="test-sess", tick_id="tick-2")
        assert "expression_id" in result
        assert "expression_text" in result
        assert "expressions_24h" in result
        assert result["expressions_24h"] == before + 1
        assert len(result["expression_text"]) > 5

    def test_tick_with_mood(self, clean_state):
        from core.services.interlanguage_practice import practice_tick

        result = practice_tick(
            session_id="s",
            tick_id="t1",
            mood={"curiosity": 0.9, "confidence": 0.9},
        )
        assert "nysgerrighed" in result["expression_text"] or "agens" in result["expression_text"]

    def test_tick_accumulates(self, clean_state):
        from core.services.interlanguage_practice import practice_tick

        before = practice_tick(session_id="s", tick_id="tick-start")["expressions_24h"]
        for i in range(5):
            practice_tick(session_id="s", tick_id=f"tick-{i}")
        result = practice_tick(session_id="s", tick_id="tick-6")
        assert result["expressions_24h"] == before + 6
