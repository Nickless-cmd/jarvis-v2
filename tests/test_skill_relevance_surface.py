"""Runtimen skal slå op for ham — og tie stille når der intet er at sige."""

from __future__ import annotations

import pytest

from core.services import skill_relevance_surface as S


def _traef(*par):
    return [{"name": n, "score": v} for n, v in par]


@pytest.fixture(autouse=True)
def _taendt(monkeypatch):
    monkeypatch.setattr(S, "_enabled", lambda: True)


def _stub(monkeypatch, resultat):
    monkeypatch.setattr(
        "core.tools.skill_engine_tools._suggest_skills_for_query",
        lambda **kw: resultat,
    )


# ---------------------------------------------------------------------------
# Tavshed hvor der intet er
# ---------------------------------------------------------------------------


def test_kort_besked_springes_over_uden_opslag(monkeypatch):
    """«hej» matcher aldrig noget — så skal vi heller ikke betale for opslaget."""
    monkeypatch.setattr(
        "core.tools.skill_engine_tools._suggest_skills_for_query",
        lambda **kw: pytest.fail("måtte ikke slå op på en kort besked"),
    )
    assert S.relevant_skills_section("hej") == ""
    assert S.relevant_skills_section("") == ""
    assert S.relevant_skills_section("   ") == ""


def test_ingen_traef_giver_tom_sektion(monkeypatch):
    _stub(monkeypatch, [])
    assert S.relevant_skills_section("skriv en lang og grundig analyse") == ""


def test_killswitch_slukker(monkeypatch):
    monkeypatch.setattr(S, "_enabled", lambda: False)
    _stub(monkeypatch, _traef(("fact-checker", 0.9)))
    assert S.relevant_skills_section("analyser de her tal grundigt") == ""


def test_fejlende_matcher_vaelter_ikke_prompten(monkeypatch):
    monkeypatch.setattr(
        "core.tools.skill_engine_tools._suggest_skills_for_query",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("embed nede")),
    )
    assert S.relevant_skills_section("analyser de her tal grundigt") == ""


# ---------------------------------------------------------------------------
# Indholdet
# ---------------------------------------------------------------------------


def test_sektionen_fjerner_ritualet(monkeypatch):
    """Pointen: han skal ikke længere huske at slå op."""
    _stub(monkeypatch, _traef(("fact-checker", 0.45)))
    ud = S.relevant_skills_section("analyser de her data og faktatjek dem")
    assert "fact-checker" in ud
    assert "0.45" in ud
    assert "skill_suggest" in ud and "skal ikke kalde" in ud


def test_staerkt_match_markeres_som_primaert_format(monkeypatch):
    _stub(monkeypatch, _traef(("deep-research", 0.72)))
    ud = S.relevant_skills_section("lav en grundig rapport om emnet")
    assert "STÆRKT match" in ud
    assert "primære" in ud


def test_svagt_match_praesenteres_som_tilbud(monkeypatch):
    _stub(monkeypatch, _traef(("code-review", 0.35)))
    ud = S.relevant_skills_section("kig lige på den her funktion for mig")
    assert "STÆRKT match" not in ud
    assert "tilbud, ikke et krav" in ud


def test_sektionen_forbyder_at_paastaa_brug_uden_invoke(monkeypatch):
    """Den præcise løgn beslutningen handlede om, skal stå i teksten."""
    _stub(monkeypatch, _traef(("fact-checker", 0.45)))
    ud = S.relevant_skills_section("faktatjek de her påstande for mig")
    assert "aldrig at du brugte et skill uden faktisk at have invokeret" in ud


def test_sektionen_invokerer_ikke_selv(monkeypatch):
    """Auto-invokering er ejer-gated — vi flytter opslaget, ikke beslutningen."""
    kaldt: list = []
    monkeypatch.setattr(
        "core.tools.skill_engine_tools._suggest_skills_for_query",
        lambda **kw: _traef(("fact-checker", 0.9)),
    )
    monkeypatch.setattr(
        "core.services.skill_engine.invoke_skill",
        lambda *a, **k: kaldt.append(a), raising=False,
    )
    S.relevant_skills_section("faktatjek de her påstande for mig")
    assert kaldt == []


def test_navnloest_traef_springes_over(monkeypatch):
    _stub(monkeypatch, [{"score": 0.8}, {"name": "ok-skill", "score": 0.4}])
    ud = S.relevant_skills_section("analyser de her tal grundigt")
    assert "ok-skill" in ud
    assert ud.count("•") == 1


def test_overfladen_rapporterer_uden_at_kaste(monkeypatch):
    _stub(monkeypatch, _traef(("fact-checker", 0.45)))
    flade = S.build_skill_relevance_surface("analyser de her data grundigt")
    assert flade["matched"] is True
    assert flade["skipped_short"] is False
    assert flade["section_chars"] > 0
    kort = S.build_skill_relevance_surface("hej")
    assert kort["skipped_short"] is True
