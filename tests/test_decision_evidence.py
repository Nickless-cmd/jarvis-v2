"""Regnskabet skal kunne bære en dom — og sige fra når det ikke kan."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import decision_evidence as DE


# ---------------------------------------------------------------------------
# Porten — kernen i C3
# ---------------------------------------------------------------------------


def test_kept_uden_ydre_spor_bliver_unknown():
    """Junis fejl i én linje: modellen sagde kept, intet var sket, scoren steg."""
    assert DE.evidence_permits_verdict("kept", {"has_evidence": False}) == "unknown"


def test_partial_uden_ydre_spor_bliver_ogsaa_unknown():
    """partial giver 0.5 i gennemsnittet og løfter altså også scoren."""
    assert DE.evidence_permits_verdict("partial", {"has_evidence": False}) == "unknown"


def test_kept_med_ydre_spor_staar_ved_magt():
    assert DE.evidence_permits_verdict("kept", {"has_evidence": True}) == "kept"
    assert DE.evidence_permits_verdict("partial", {"has_evidence": True}) == "partial"


def test_broken_slipper_altid_igennem():
    """Fraværet af handling ER ofte bruddet — et brud kræver ikke bevis for aktivitet."""
    assert DE.evidence_permits_verdict("broken", {"has_evidence": False}) == "broken"
    assert DE.evidence_permits_verdict("broken", {}) == "broken"


def test_ukendt_dom_falder_tilbage_til_unknown():
    assert DE.evidence_permits_verdict("", {"has_evidence": True}) == "unknown"
    assert DE.evidence_permits_verdict("vrøvl", {"has_evidence": True}) == "vrøvl"


# ---------------------------------------------------------------------------
# Indsamlingen
# ---------------------------------------------------------------------------


def test_tomt_vindue_giver_intet_bevis(monkeypatch):
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=24))
    assert ud["has_evidence"] is False
    assert ud["tool_calls_total"] == 0
    assert "Værktøjer kørt: ingen" in ud["summary"]
    assert "Commits: ingen" in ud["summary"]


def test_vaerktoejer_alene_er_nok_bevis(monkeypatch):
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {"bash": 3, "read_file": 1})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["has_evidence"] is True
    assert ud["tool_calls_total"] == 4
    assert "bash×3" in ud["summary"]


def test_commits_alene_er_nok_bevis(monkeypatch):
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: ["abc1234 fix: noget"])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=6))
    assert ud["has_evidence"] is True
    assert "abc1234" in ud["summary"]


def test_naive_tidsstempler_taales(monkeypatch):
    """Kalderen må ikke skulle huske tidszone for at få et regnskab."""
    monkeypatch.setattr(DE, "_tool_names_since", lambda s, u: {})
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime(2026, 9, 5, 8, 0, 0))
    assert ud["window_hours"] >= 0


def test_indsamling_er_selvsikker_mod_doed_db(monkeypatch):
    """Kan DB'en ikke læses, er svaret 'ingen bevis' — ikke en exception."""
    def _sprang(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _sprang)
    monkeypatch.setattr(DE, "_commits_since", lambda s, u: [])
    ud = DE.gather_evidence(since=datetime.now(UTC) - timedelta(hours=1))
    assert ud["has_evidence"] is False


def test_kun_udfoerte_vaerktoejer_taeller():
    """tool.invoked alene beviser intet — et kald kan afvises af en gate."""
    assert "tool.completed" in DE._TOOL_EVENT_KINDS
    assert "tool.invoked" not in DE._TOOL_EVENT_KINDS
