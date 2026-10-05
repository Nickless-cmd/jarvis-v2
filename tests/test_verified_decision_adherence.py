"""Legacy LLM breach suspicions must not dominate verified adherence."""
from __future__ import annotations

import sqlite3

from core.runtime import db_decisions


def _database(monkeypatch, tmp_path):
    path = tmp_path / "decisions.sqlite"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(db_decisions, "connect", connect)


def test_verified_review_ignores_legacy_auto_breaches(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    did = db_decisions.create_decision(directive="Cite a correction")["decision_id"]
    db_decisions.append_review(
        decision_id=did, verdict="broken", note="Auto-detected breach: possible",
    )
    # Tre tællende domme, ikke én: et maal kraever mere end et par domme
    # (`_MIN_VERDICTS`, 5/10-2026). Se den sidste test i filen.
    db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    result = db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    assert result["adherence_score"] == 1.0


def test_repair_removes_legacy_suspicion_from_existing_scores(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    did = db_decisions.create_decision(directive="Cite a correction")["decision_id"]
    db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    db_decisions.append_review(decision_id=did, verdict="kept", note="Observed citation")
    db_decisions.append_review(
        decision_id=did, verdict="broken", note="Auto-detected breach: possible",
    )
    db_decisions.repair_legacy_auto_adherence()
    result = db_decisions.get_decision(did)
    assert result["adherence_score"] == 1.0
    assert result["last_reviewed_at"] == db_decisions.list_reviews(did)[1]["created_at"]


def test_en_score_dannes_IKKE_paa_under_tre_domme(monkeypatch, tmp_path):
    """Et maal kraever mere end et par domme (5/10-2026).

    Maalt samme dag: 72 af 80 aktive beslutninger havde <=2 taellende domme, og
    ALLE 19 der stod paa 0.0 havde <=2 — ingen havde >=5. Gennemsnittet lober
    over 20 domme, som de fleste beslutninger aldrig naar, saa to domme i traek
    gav 0.0 i ugevis. Testen maaler BEGGE sider: under graensen er svaret «ikke
    maalt» (None), ved graensen dannes scoren.
    """
    _database(monkeypatch, tmp_path)
    did = db_decisions.create_decision(directive="Cite a correction")["decision_id"]
    db_decisions.append_review(decision_id=did, verdict="broken", note="Observed")
    result = db_decisions.append_review(decision_id=did, verdict="broken", note="Observed")
    assert result["adherence_score"] is None, "to domme er ikke et maal"
    result = db_decisions.append_review(decision_id=did, verdict="broken", note="Observed")
    assert result["adherence_score"] == 0.0, "tre domme ER et maal"


def test_repair_marks_auto_only_decision_unreviewed(monkeypatch, tmp_path):
    _database(monkeypatch, tmp_path)
    did = db_decisions.create_decision(directive="Cite a correction")["decision_id"]
    db_decisions.append_review(
        decision_id=did, verdict="broken", note="Auto-detected breach: possible",
    )
    db_decisions.repair_legacy_auto_adherence()
    result = db_decisions.get_decision(did)
    assert result["adherence_score"] is None
    assert result["last_reviewed_at"] is None
