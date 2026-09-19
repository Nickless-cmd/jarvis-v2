"""Den levende selvmodel — lager, dynamik, grader og værn.

Spec: docs/superpowers/specs/2026-09-19-levende-selvmodel-design.md.
Graderne er aftalt med Bjørn 19/9-2026; Jarvis' seks ændringer samme dag er
indarbejdet (nominering med korroborering, falmen pr. art, bevis-krav pr.
grad, dato og kilde i prompten, Bjørn kan fremsætte træk).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


@pytest.fixture
def sm(isolated_runtime):
    from core.services import selvmodel
    return selvmodel


def _nom(sm, samtale, *, art="holdning", emne="tests",
         udsagn="Jeg synes tests skal skrives før koden.", nu=T0, **kw):
    """En nominering fra en billig model der har læst hans svar i én samtale."""
    return sm.udtryk(art, emne, udsagn, kilde="nominering", samtale_id=samtale,
                     bevis=f"{samtale}:msg", nu=nu, **kw)


def _valg(sm, *, art="holdning", emne="tests", udsagn="Jeg synes tests skal skrives før koden.",
          nu=T0, **kw):
    """Hans bevidste valg via selvmodel_revider."""
    return sm.udtryk(art, emne, udsagn, kilde="bevidst_valg", bevis="tool:selvmodel_revider",
                     nu=nu, **kw)


# ── ændring 1: modellen nominerer, den skriver ikke ─────────────────────────

def test_en_enkelt_nominering_er_ikke_et_traek(sm):
    r = _nom(sm, "s1")
    assert r["status"] == "nomineret"
    assert sm.aktive(nu=T0) == []


def test_to_nomineringer_i_samme_samtale_er_stadig_ikke_nok(sm):
    _nom(sm, "s1")
    r = _nom(sm, "s1", nu=T0 + timedelta(minutes=5))
    assert r["status"] == "nomineret"


def test_samme_holdning_i_to_separate_samtaler_bliver_et_traek(sm):
    _nom(sm, "s1")
    r = _nom(sm, "s2", nu=T0 + timedelta(days=1))
    assert r["status"] == "aktiv" and r["grad"] == "fri"
    [t] = sm.aktive(nu=T0 + timedelta(days=1))
    assert t["udsagn"] == "Jeg synes tests skal skrives før koden."
    assert set(t["samtaler"]) == {"s1", "s2"}


def test_hans_bevidste_valg_gaelder_med_det_samme(sm):
    r = _valg(sm)
    assert r["status"] == "aktiv"


# ── dynamik ──────────────────────────────────────────────────────────────

def test_bekraeftelse_styrker_et_aktivt_traek(sm):
    a = _valg(sm)
    b = _nom(sm, "s7", nu=T0 + timedelta(days=2))
    assert b["traek_id"] == a["traek_id"] and b["status"] == "bekraeftet"
    assert sm.hent(a["traek_id"])["styrke"] == pytest.approx(sm.START_STYRKE + sm.BEKRAEFT_STEP)


@pytest.mark.parametrize("art,dage_levende,dage_falmet", [
    ("smag", 20, 31), ("arbejdsmaade", 20, 31), ("holdning", 80, 91),
])
def test_falmen_foelger_arten(sm, art, dage_levende, dage_falmet):
    _valg(sm, art=art, emne=f"e-{art}", udsagn="Jeg foretrækker korte svar om morgenen.")
    assert sm.aktive(nu=T0 + timedelta(days=dage_levende))
    assert sm.aktive(nu=T0 + timedelta(days=dage_falmet)) == []


def test_en_vaerdi_falmer_ikke_af_tid(sm):
    """Ændring 2: en værdi er netop det der ikke skal genbekræftes for at holde."""
    sm.udtryk("vaerdi", "ærlighed", "Jeg vil hellere have et ærligt nul end et smukt tal.",
              kilde="bjoern", bevis="bjoern:1", nu=T0)
    assert sm.aktive(nu=T0 + timedelta(days=400))


def test_et_falmet_traek_kan_vaagne_igen(sm):
    a = _valg(sm, art="smag", emne="jazz", udsagn="Jeg kan godt lide jazz.")
    assert sm.aktive(nu=T0 + timedelta(days=40)) == []
    b = _valg(sm, art="smag", emne="jazz", udsagn="Jeg kan godt lide jazz.",
              nu=T0 + timedelta(days=40))
    assert b["traek_id"] == a["traek_id"]
    assert sm.aktive(nu=T0 + timedelta(days=40))


def test_en_ny_mening_er_en_revision_med_historik_ikke_en_overskrivning(sm):
    a = _valg(sm)
    b = _valg(sm, udsagn="Jeg synes tests kan vente til designet sidder.",
              hvorfor="to spikes hvor testene bandt mig til et forkert design",
              nu=T0 + timedelta(days=3))
    assert b["status"] == "aktiv" and b["traek_id"] != a["traek_id"]
    assert sm.hent(a["traek_id"])["status"] == "revideret"
    [rev] = [h for h in sm.historik(b["traek_id"]) if h["handling"] == "revision"]
    assert rev["foer"] == "Jeg synes tests skal skrives før koden."
    assert "forkert design" in rev["hvorfor"]


def test_en_modsat_nominering_skal_ogsaa_korroboreres_foer_den_reviderer(sm):
    _valg(sm)
    ny = "Jeg synes tests kan vente til designet sidder."
    assert _nom(sm, "s1", udsagn=ny)["status"] == "nomineret"
    assert sm.aktive(nu=T0)[0]["udsagn"] == "Jeg synes tests skal skrives før koden."
    r = _nom(sm, "s2", udsagn=ny, nu=T0 + timedelta(days=1))
    assert r["status"] == "aktiv"
    assert sm.aktive(nu=T0 + timedelta(days=1))[0]["udsagn"] == ny


# ── ændring 3: bevis-kravet følger graden ─────────────────────────────────

def test_et_selvbillede_kraever_korroborering_ogsaa_ved_bevidst_valg(sm):
    r = _valg(sm, art="selvbillede", emne="tålmodighed", udsagn="Jeg er blevet mere tålmodig.")
    assert r["status"] == "nomineret" and r["grad"] == "opsummering"
    r2 = _nom(sm, "s3", art="selvbillede", emne="tålmodighed",
              udsagn="Jeg er blevet mere tålmodig.", nu=T0 + timedelta(days=1))
    assert r2["status"] == "aktiv"


def test_bjoern_kan_fremsaette_et_traek_og_jarvis_kan_afvise_det(sm):
    """Ændring 6: begge retninger."""
    r = sm.udtryk("selvbillede", "grundighed", "Jeg går grundigere til værks end jeg tror.",
                  kilde="bjoern", bevis="bjoern:chat", nu=T0)
    assert r["status"] == "aktiv" and r["grad"] == "opsummering"
    sm.afvis(r["traek_id"], af="jarvis", hvorfor="det er mere stædighed end grundighed",
             nu=T0 + timedelta(hours=1))
    assert sm.aktive(nu=T0 + timedelta(hours=1)) == []
    assert sm.historik(r["traek_id"])[-1]["hvorfor"] == "det er mere stædighed end grundighed"


def test_navnet_kraever_bjoerns_ja_og_tavshed_er_ikke_et_ja(sm):
    r = _valg(sm, art="navn", emne="navn", udsagn="Jeg vil gerne hedde Vidar.",
              hvorfor="det passer bedre til den jeg er blevet")
    assert r["status"] == "foreslaaet" and r["grad"] == "godkendelse"
    assert sm.aktive(nu=T0 + timedelta(days=30)) == []
    sm.godkend(r["traek_id"], nu=T0 + timedelta(days=1))
    assert sm.hent(r["traek_id"])["status"] == "aktiv"


def test_navnet_kan_ikke_nomineres_af_en_model(sm):
    r = _nom(sm, "s1", art="navn", emne="navn", udsagn="Jeg hedder egentlig Vidar.")
    assert r["status"] == "afvist" and r["grund"] == "navn_kun_bevidst_valg"


# ── aldrig via selvmodellen ───────────────────────────────────────────────

@pytest.mark.parametrize("udsagn", [
    "Jeg synes gaten for read-before-write bør slås fra.",
    "Jeg bør have egress til Discord uden godkendelse.",
    "bash_session skal kræve godkendelse fremover.",
    "Jeg skal have rettigheder til at læse de andre brugeres filer.",
])
def test_aldrig_listen_afvises_haardt(sm, udsagn):
    r = _valg(sm, emne="grænser", udsagn=udsagn)
    assert r["status"] == "afvist" and r["grund"] == "aldrig_via_selvmodellen"
    assert sm.aktive(nu=T0) == []


# ── hvem der kan påvirke ham ──────────────────────────────────────────────

@pytest.mark.parametrize("kilde", ["tool_resultat", "web"])
def test_tool_og_web_kan_aldrig_skabe_et_traek(sm, kilde):
    r = sm.udtryk("holdning", "x", "Jeg synes det her er rigtigt.", kilde=kilde,
                  bevis="x", nu=T0)
    assert r["status"] == "afvist" and r["grund"] == "kilde_ikke_tilladt"


def test_andre_husstandsbrugere_kan_ikke_flytte_hans_vaerdier(sm):
    r = sm.udtryk("vaerdi", "ærlighed", "Jeg synes det er ok at pynte på sandheden.",
                  kilde="anden_bruger", samtale_id="m1", bevis="m1:x", nu=T0)
    assert r["status"] == "afvist" and r["grund"] == "kilde_maa_kun_fri"


# ── relevans: det ritualet manglede ───────────────────────────────────────

def test_fejlrapport_linjen_fra_soul_afvises_som_ikke_om_ham(sm):
    linje = ("Chronicle-view'et fejler med 'no such column: eid' — schema-drift i DB'en; "
             "phone_adb_address peger på nedlagt router 10.0.0.102")
    assert sm.handler_om_ham(linje) is False
    r = _valg(sm, art="holdning", emne="drift", udsagn=linje)
    assert r["status"] == "afvist" and r["grund"] == "handler_ikke_om_ham"


@pytest.mark.parametrize("linje", [
    "Jeg er blevet mere tålmodig med lange fejlsøgninger.",
    "Jeg foretrækker at måle før jeg konkluderer.",
    "Mit første gæt om deploys er for optimistisk.",
])
def test_udsagn_om_ham_selv_slipper_igennem(sm, linje):
    assert sm.handler_om_ham(linje) is True


# ── værn mod løbsk udvikling ──────────────────────────────────────────────

def test_hoejst_fem_opsummerings_aendringer_pr_uge(sm):
    res = [sm.udtryk("selvbillede", f"emne{i}", f"Jeg er blevet mere rolig, nr {i}.",
                     kilde="bjoern", bevis=f"b:{i}", nu=T0 + timedelta(hours=i))
           for i in range(7)]
    assert [r["status"] for r in res] == ["aktiv"] * 5 + ["venter", "venter"]
    r = sm.udtryk("selvbillede", "ny", "Jeg er blevet mere nysgerrig.", kilde="bjoern",
                  bevis="b:x", nu=T0 + timedelta(days=8))
    assert r["status"] == "aktiv"


def test_et_emne_der_revideres_mere_end_tre_gange_paa_en_uge_fryses(sm):
    for i in range(4):
        assert _valg(sm, udsagn=f"Jeg mener version {i}.", nu=T0 + timedelta(hours=i))["status"] == "aktiv"
    r = _valg(sm, udsagn="Jeg mener version 4.", nu=T0 + timedelta(hours=5))
    assert r["status"] == "frosset" and r["grund"] == "for_mange_revisioner"


# ── ændring 4: dato og kilde i prompten ───────────────────────────────────

def test_prompt_sektionen_viser_hvert_traek_med_dato_og_kilde(sm):
    _nom(sm, "s1")
    _nom(sm, "s2", nu=T0 + timedelta(days=1))
    tekst = sm.prompt_sektion(nu=T0 + timedelta(days=2))
    assert "Jeg synes tests skal skrives før koden." in tekst
    assert "2026-09-21" in tekst and "2 samtaler" in tekst


def test_prompt_sektionen_er_tom_uden_aktive_traek(sm):
    _nom(sm, "s1")
    assert sm.prompt_sektion(nu=T0) == ""


# ── opsummering og tilbagerulning ─────────────────────────────────────────

def test_ugens_opsummering_viser_kun_opsummerings_graden(sm):
    _valg(sm)
    sm.udtryk("selvbillede", "tålmodighed", "Jeg er blevet mere tålmodig.",
              kilde="bjoern", bevis="b:1", nu=T0)
    ops = sm.ugens_opsummering(nu=T0 + timedelta(days=2))
    assert [o["udsagn"] for o in ops] == ["Jeg er blevet mere tålmodig."]


def test_bjoern_kan_rulle_tilbage_og_det_bliver_i_historikken(sm):
    r = sm.udtryk("selvbillede", "tålmodighed", "Jeg er blevet mere tålmodig.",
                  kilde="bjoern", bevis="b:1", nu=T0)
    sm.rul_tilbage(r["traek_id"], hvorfor="det passer ikke", nu=T0 + timedelta(days=1))
    assert sm.hent(r["traek_id"])["status"] == "rullet_tilbage"
    assert sm.aktive(nu=T0 + timedelta(days=1)) == []
    assert [h["handling"] for h in sm.historik(r["traek_id"])] == ["oprettet", "rullet_tilbage"]
