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
    # Bundet til KONSTANTEN og ikke et tal. Testen stod paa 0,72, valgt dengang
    # taersklen var 0,50 — den blev foraeldet da taersklen blev kalibreret til
    # 0,77 (15/9-2026) og fejlede paa sit eget magiske tal.
    _stub(monkeypatch, _traef(("deep-research", S._PRIMARY_THRESHOLD + 0.01)))
    ud = S.relevant_skills_section("lav en grundig rapport om emnet")
    assert "STÆRKT match" in ud
    assert "primære" in ud


def test_svagt_match_praesenteres_som_tilbud(monkeypatch):
    _stub(monkeypatch, _traef(("code-review", S._PRIMARY_THRESHOLD - 0.05)))
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


def test_explicit_research_context_precedes_ordinary_skill_suggestions(monkeypatch):
    from core.services.research_contract import ResearchPolicy
    from core.services.research_prompt_context import research_context

    _stub(monkeypatch, [])
    with research_context(ResearchPolicy(), skill_instructions="Use primary sources"):
        section = S.relevant_skills_section("find dokumentation for denne påstand")
    assert section.startswith("[RESEARCH CONTRACT]")
    assert "Use primary sources" in section


# ── skill_flade_event (16/9-2026) ────────────────────────────────────────
def _saet_memo(monkeypatch, besked, traef):
    import core.services.skill_relevance_surface as m
    monkeypatch.setattr(m, "_SIDSTE_TRAEF", (besked, traef))
    return m


def test_skill_flade_event_bygger_payload_med_primaer(monkeypatch):
    m = _saet_memo(monkeypatch, "lav et regneark over forbruget",
                   [{"name": "xlsx", "score": 0.78}, {"name": "csv", "score": 0.71}])
    ev = m.skill_flade_event("lav et regneark over forbruget")
    assert ev == {
        "type": "skill_surface",
        "matches": [
            {"name": "xlsx", "score": 0.78, "primary": True},
            {"name": "csv", "score": 0.71, "primary": False},
        ],
        "primary": True,
    }


def test_skill_flade_event_eksplicit_navn_er_primaert_trods_lav_score(monkeypatch):
    m = _saet_memo(monkeypatch, "brug pdf skill til rapporten", [{"name": "pdf", "score": 0.72}])
    ev = m.skill_flade_event("brug pdf skill til rapporten")
    assert ev["matches"][0]["primary"] is True


def test_skill_flade_event_anden_besked_giver_intet(monkeypatch):
    m = _saet_memo(monkeypatch, "en helt anden tur", [{"name": "xlsx", "score": 0.9}])
    assert m.skill_flade_event("lav et regneark") is None


def test_skill_flade_event_ingen_traef_giver_intet(monkeypatch):
    m = _saet_memo(monkeypatch, "lav et regneark", [])
    assert m.skill_flade_event("lav et regneark") is None


def test_skill_flade_event_forankret_kort_svar_matcher(monkeypatch):
    m = _saet_memo(monkeypatch, "ja\n\n[forrige svar: skal jeg lave regnearket?]",
                   [{"name": "xlsx", "score": 0.8}])
    assert m.skill_flade_event("ja")["matches"][0]["name"] == "xlsx"


def test_skill_flade_event_slaar_aldrig_op_selv(monkeypatch):
    m = _saet_memo(monkeypatch, "", [])
    monkeypatch.setattr(m, "_traef", lambda b: (_ for _ in ()).throw(AssertionError("opslag")))
    assert m.skill_flade_event("lav et regneark") is None


def test_sektionen_fylder_memoen_med_scorer(monkeypatch):
    import core.services.skill_relevance_surface as m
    monkeypatch.setattr(m, "_traef", lambda b: [{"name": "xlsx", "score": 0.8}])
    monkeypatch.setattr("core.services.research_prompt_context.research_prompt_section", lambda: "")
    m.relevant_skills_section("lav et regneark over forbruget i september")
    assert m.skill_flade_event("lav et regneark over forbruget i september")["matches"][0]["score"] == 0.8
