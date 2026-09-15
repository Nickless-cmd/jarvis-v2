"""Prompten bad om et værktøj der ikke lå i kaldet.

## Målt 15/9-2026

Codex' analyse, efterprøvet: af kataloget på 471 værktøjer har 24 «skill» i
navnet, og **ingen** af dem overlevede beskæringen til de 48 i den synlige
lane — heller ikke på «brug pdf skill». Alligevel skriver prompten ordret:

    skill_invoke("<navn>") og læs HELE SKILL.md før du skriver svaret

Jarvis gjorde derfor det rationelle: fandt filen med `explore` og læste
SKILL.md i hånden. Det var ikke ulydighed; det var den eneste vej han kunne se.

## Tredje gang mønsteret bider

Kommentaren over `REQUIRED_LAZY_TOOL_NAMES` beskriver præcis det samme for
`explore` den 6/9: «scope tillod det, kataloget nævnte det, prompten anbefalede
det — og pruneren fjernede det fra selve tool-arrayet».

## Reglen

Runtimen må aldrig instruere modellen i at kalde et værktøj, som ikke findes i
den aktuelle request.
"""
from __future__ import annotations

import pytest

from core.tools import copilot_tool_pruning as p
from core.services import skill_relevance_surface as s


def _navn(t: dict) -> str:
    return t.get("name") or (t.get("function") or {}).get("name") or ""


@pytest.fixture
def katalog():
    from core.tools.simple_tools import get_tool_definitions
    return get_tool_definitions()


# ────────────────────────────────────────────────── selve betingelsen

def test_uden_match_faestnes_ingenting():
    """En plads ud af 48 er ikke gratis. Uden et match nævner prompten ingen
    skills, og `skill_invoke` ville være et værktøj uden et navn at give det."""
    assert p._betinget_kraevede("hej") == ()
    assert p._betinget_kraevede("") == ()


def test_med_match_faestnes_skill_invoke():
    assert p._betinget_kraevede("hjaelp mig med excel") == ("skill_invoke",)


def test_betingelsen_kaster_aldrig(monkeypatch):
    """Kan vi ikke afgøre det, fæstner vi ingenting og er præcis lige så dårligt
    stillet som før — aldrig værre."""
    monkeypatch.setattr(s, "matchede_skills",
                        lambda _m: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert p._betinget_kraevede("hjaelp mig med excel") == ()


# ──────────────────────────────────── kontrakten, maalt paa det AEGTE katalog

@pytest.mark.parametrize("besked", [
    "hjaelp mig med excel", "lav en pdf rapport",
    "skriv en rapport om kvartalet", "docker container starter ikke",
])
def test_naevner_prompten_det_saa_LIGGER_det_der(katalog, besked):
    """Kontrakten. Før rettelsen fejlede alle fire."""
    naevner = "skill_invoke(" in (s.relevant_skills_section(besked) or "")
    if not naevner:
        pytest.skip(f"matcheren fandt intet for «{besked}» — intet loefte at holde")
    ud = p.select_tools_for_visible(katalog, user_message=besked)
    assert "skill_invoke" in {_navn(t) for t in ud}


@pytest.mark.parametrize("besked", ["hej", "ok tak"])
def test_naevner_prompten_det_IKKE_spildes_pladsen_ikke(katalog, besked):
    ud = p.select_tools_for_visible(katalog, user_message=besked)
    assert "skill_invoke" not in {_navn(t) for t in ud}


def test_kappen_holder_stadig(katalog):
    """Fæstningen må ikke sprænge loftet — så ville den bare flytte problemet."""
    for besked in ("hjaelp mig med excel", "hej"):
        ud = p.select_tools_for_visible(katalog, user_message=besked)
        assert len(ud) <= p.VISIBLE_MAX_TOOLS, (besked, len(ud))


def test_de_faste_vaerktoejer_overlever_stadig(katalog):
    """`load_more_tools` og `explore` var der før. En ny betinget regel må ikke
    have skubbet dem ud — det var netop sådan `explore` forsvandt 6/9."""
    ud = {_navn(t) for t in p.select_tools_for_visible(katalog, user_message="hjaelp mig med excel")}
    for navn in ("load_more_tools", "explore"):
        assert navn in ud, navn


# ───────────────────────────────── ÉN faestning, ikke to (den skjulte fejl)

def test_faestningen_findes_praecis_ÉT_sted():
    """Logikken lå i TO kopier i samme funktion — én i den tidlige udgang
    (`remaining <= 0`) og én efter Tier 2. Da reglen blev tilføjet, ramte den
    kun den ene, og rettelsen så ud til ikke at virke: Tier 1 sprænger kappen
    alene i cowork-scope, så det er netop den tidlige udgang der tages.

    To kopier af samme beslutning er dobbelt sandhed.
    """
    import inspect
    kilde = inspect.getsource(p.select_tools_for_copilot)
    assert kilde.count("_faestn_kraevede(") == 2, "de to udgange deler ikke faestningen"
    assert "REQUIRED_LAZY_TOOL_NAMES" not in kilde, "der er stadig en egen kopi"


def test_den_tidlige_udgang_faestner_ogsaa(katalog):
    """Den vej der FAKTISK tages i cowork-scope, hvor Tier 1 alene er over 48."""
    lille = 8   # tvinger remaining <= 0
    ud = p.select_tools_for_copilot(
        katalog, user_message="hjaelp mig med excel", max_tools=lille, stable_only=True)
    assert "skill_invoke" in {_navn(t) for t in ud}


# ───────────────────────────────────────── ét opslag, to forbrugere

def test_prompt_og_beskaerer_deler_opslaget(monkeypatch):
    """To opslag kunne give to forskellige svar — og så ville kontrakten kunne
    brydes uden at nogen af siderne var forkerte hver for sig."""
    kald = []
    aegte = s._traef
    monkeypatch.setattr(s, "_traef", lambda b: kald.append(b) or aegte(b))
    s._SIDSTE = ("", [])
    s.relevant_skills_section("hjaelp mig med excel")
    n_efter_prompt = len(kald)
    p._betinget_kraevede("hjaelp mig med excel")
    assert len(kald) == n_efter_prompt, "beskaereren slog op igen i stedet for at genbruge"


# ─────────────────────────────── autonome ture (15/9-2026)

@pytest.fixture
def ryd_memo():
    s._SIDSTE = ("", [])
    yield
    s._SIDSTE = ("", [])


def _saet_run(rid: str) -> None:
    import core.services.run_closure_gate as g
    g._set_current_run(rid)


def test_autonome_ture_faar_ingen_skills(ryd_memo):
    """Målt over tre timer: fladen fyrede tre gange, og alle tre var autonome
    ture. Der var ingen bruger der spurgte om noget.

        autonomous-e  «Begge bekræftet. Dream note verificeret…»
        autonomous-d  «Data samlet. DB er sund (integrity OK)…»
        autonomous-3  «hjemme. Her er den korte rapport…»

    Nul af forslagene blev brugt — hvilket var KORREKT, ikke en fejl. Det
    kostede ~55 ms opslag og en plads ud af 48 på hver baggrundstur.
    """
    _saet_run("autonomous-abc123")
    try:
        assert s.matchede_skills("hjaelp mig med excel") == []
        assert s.relevant_skills_section("hjaelp mig med excel").find("excel") == -1
    finally:
        _saet_run("")


def test_synlige_ture_er_uberoerte(ryd_memo):
    _saet_run("visible-abc123")
    try:
        assert s.matchede_skills("hjaelp mig med excel") == ["excel-automation"]
    finally:
        _saet_run("")


def test_uden_et_kendt_run_koerer_vi_som_foer(ryd_memo):
    """Fejlretningen: tvivlen falder ud til at BEHOLDE skills for hans ture.
    Run-id'et sættes kun af `runtime.autonomous_run_started`, så en synlig tur
    har ofte slet intet id — og den må ikke miste sine skills af den grund."""
    _saet_run("")
    assert s.matchede_skills("hjaelp mig med excel") == ["excel-automation"]


def test_beskaereren_foelger_med(ryd_memo):
    """Det er hele pointen med ét delt opslag: prompten og værktøjsvalget kan
    ikke komme til at sige hver sit."""
    _saet_run("autonomous-abc123")
    try:
        assert p._betinget_kraevede("hjaelp mig med excel") == ()
    finally:
        _saet_run("")


def test_en_fejl_i_opslaget_undtager_ikke(ryd_memo, monkeypatch):
    """Kan vi ikke afgøre det, er svaret NEJ — altså kør som før."""
    import core.services.session_context_resolve as scr
    monkeypatch.setattr(scr, "aktivt_run_id",
                        lambda standard="": (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert s._er_autonom_tur() is False
