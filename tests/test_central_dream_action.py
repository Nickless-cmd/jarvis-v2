"""Drøm→handling skal kunne fyre på en moden hypotese.

Rod (Bjørn 17. aug 2026): `select_actionable` krævede `confidence >= 0.7`, men aktive
hypoteser topper målt på 0.581 (resolved på 0.676) → `central_dream_actions` havde 0
rækker NOGENSINDE. Filen blev skrevet som svar på Jarvis' klage "jeg lærer, men jeg
forandrer mig ikke" — og kunne aldrig fyre. Tærsklen er nu 0.55 (opnåelig).
"""
from __future__ import annotations

from core.runtime.db_core import connect
import core.services.central_dream_action as da


_SCHEMA = """CREATE TABLE IF NOT EXISTS central_hypotheses (
    hyp_id TEXT PRIMARY KEY, source TEXT NOT NULL, statement TEXT NOT NULL,
    prediction TEXT NOT NULL, null_hypothesis TEXT NOT NULL, success_criterion TEXT NOT NULL,
    sample_size INTEGER NOT NULL, ttl_seconds INTEGER NOT NULL, provenance_json TEXT NOT NULL,
    confidence REAL NOT NULL, status TEXT NOT NULL, outcome TEXT,
    grounded_samples INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, resolved_at TEXT)"""


def _insert(hyp_id, confidence, status="active", grounded=5):
    with connect() as conn:
        conn.execute(_SCHEMA)
        conn.execute(
            """INSERT INTO central_hypotheses
               (hyp_id, source, statement, prediction, null_hypothesis, success_criterion,
                sample_size, ttl_seconds, provenance_json, confidence, status, grounded_samples, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (hyp_id, "dream", f"stmt-{hyp_id}", "pred", "null", "crit",
             10, 3600, "{}", confidence, status, grounded, "2026-08-17T00:00:00+00:00"),
        )
        conn.commit()


def test_moden_aktiv_hypotese_bliver_actionable(isolated_runtime):
    """0.58 er over den nye tærskel (0.55) og under den gamle (0.7)."""
    _insert("h-mature", 0.58, status="active", grounded=5)
    out = da.select_actionable(limit=3)
    assert any(r["hyp_id"] == "h-mature" for r in out), "moden hypotese burde være actionable nu"


def test_gammel_tærskel_ville_have_udelukket_den(isolated_runtime):
    """Bevis at 0.7-tærsklen var uopnåelig for realistiske confidences."""
    _insert("h-mature", 0.58, status="active", grounded=5)
    assert da.select_actionable(min_confidence=0.7) == []
    assert len(da.select_actionable(min_confidence=0.55)) == 1


def test_ujordet_hypotese_udelukkes_stadig(isolated_runtime):
    _insert("h-thin", 0.60, status="active", grounded=1)   # grounded < _MIN_SAMPLES
    assert da.select_actionable() == []


def test_default_tærskel_er_opnåelig():
    assert da._MIN_CONFIDENCE <= 0.581, "tærsklen skal være opnåelig af aktive hypoteser (max ~0.58)"
