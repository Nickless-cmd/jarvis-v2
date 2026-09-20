"""Mønstret i komponistens forslag: hvad han plejer at BEDE OM.

Det åbne spørgsmål i Jarvis' plan var stil eller opgavetype. Bjørn 20/9-2026:
«så går vi med jers vudering» — altså opgavetype. En stil-profil konvergerer
mod gennemsnittet af ham, og noget han SELV kunne finde på er ikke hans
gennemsnit.

Den farligste fejl her er ikke et upræcist mønster. Det er at hans egne ord
sniger sig ind ad bagdøren, eller at mønstret bliver så skarpt at forslaget
holder op med at være et tilbud og bliver en vane. Begge dele står pinnet.
"""
from __future__ import annotations

import pytest

from core.services import composer_moenster as cm


def _valg(*par: tuple[str, str]) -> list[dict[str, str]]:
    """(forslag, valg) → rækker som `db_composer_choice` ville give dem."""
    return [
        {"forslag": f, "valg": v, "vist_at": "2999-01-01T00:00:00+00:00",
         "forslag_id": f"cs-{i}", "session_id": "s1", "kilde_besked_id": "m1"}
        for i, (f, v) in enumerate(par)
    ]


def _saet(monkeypatch, raekker):
    monkeypatch.setattr(cm, "_valg_i_vinduet", lambda: raekker)


# ── arten ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("forslag,forventet", [
    ("Vis mig de to der står i karantæne", "vise noget frem"),
    ("Ret det og kør testene igen", "rette noget"),
    ("Kør testene igen", "køre noget"),
    ("Deploy det til ct105", "køre noget"),
    ("Hvorfor fejler den kun på ct105?", "forklare noget"),
    ("Tjek om den kom op igen", "måle noget"),
    ("Grib fat i den der", "andet"),
    ("", "andet"),
])
def test_arten_afgoeres_af_VERBET(forslag, forventet):
    """Et forslag er en ordre eller et spørgsmål — dér bærer verbet meningen."""
    assert cm.art(forslag) == forventet


# ── mønstret ───────────────────────────────────────────────────────────────

def test_under_taersklen_siges_der_INTET(monkeypatch):
    """Et forslag der retter sig efter tre tastetryk er ikke læring, det er
    overtro. Prompten er bedre uden en linje der er gættet."""
    _saet(monkeypatch, _valg(*[("Kør testene igen", "accepteret")] * (cm.MIN_VALG - 1)))
    assert cm.moenster() == ""


def test_moenstret_peger_paa_det_han_TAGER_IMOD(monkeypatch):
    _saet(monkeypatch, _valg(
        *[("Kør testene igen", "accepteret")] * 8,
        *[("Deploy det til ct105", "accepteret")] * 4,
        *[("Hvorfor fejler den?", "eget")] * 6,
    ))
    linje = cm.moenster()
    assert "køre noget" in linje
    assert "han skriver oftest selv når det beder om at forklare noget" in linje


def test_en_art_der_baade_tages_og_vrages_naevnes_IKKE(monkeypatch):
    """En art med delt dom siger intet — og at nævne den ville kun gøre
    prompten længere."""
    _saet(monkeypatch, _valg(
        *[("Kør testene igen", "accepteret")] * 5,
        *[("Kør testene igen", "eget")] * 5,
        *[("Vis mig loggen", "accepteret")] * 4,
    ))
    linje = cm.moenster()
    assert "vise noget frem" in linje
    assert "køre noget" not in linje


def test_hoejst_TO_arter_i_hver_retning(monkeypatch):
    """Flere bliver til en liste modellen ikke kan bruge."""
    _saet(monkeypatch, _valg(
        *[("Kør det", "accepteret")] * 6, *[("Vis mig det", "accepteret")] * 5,
        *[("Ret det", "accepteret")] * 4, *[("Tjek det", "accepteret")] * 3,
    ))
    linje = cm.moenster()
    assert linje.count(" eller ") <= 1


def test_et_ÅBENT_forslag_taeller_ikke_med(monkeypatch):
    """«vist» er ingen dom — det står stadig og venter på skærmen."""
    from core.runtime import db_composer_choice as dc
    monkeypatch.setattr(dc, "seneste_valg", lambda **k: _valg(
        *[("Kør testene igen", "vist")] * 20))
    assert cm.moenster() == ""


def test_valg_UDENFOR_vinduet_taeller_ikke_med(monkeypatch):
    """Horisonten er en TID, ikke et antal. Samme lære som telemetrien fik
    samme dag: et loft på antal flytter vinduet når aktiviteten gør."""
    from core.runtime import db_composer_choice as dc
    gamle = _valg(*[("Kør testene igen", "accepteret")] * 20)
    for r in gamle:
        r["vist_at"] = "2020-01-01T00:00:00+00:00"
    monkeypatch.setattr(dc, "seneste_valg", lambda **k: gamle)
    assert cm.moenster() == ""


# ── vagterne ───────────────────────────────────────────────────────────────

def test_HANS_egne_ord_kan_ikke_naa_prompten(monkeypatch):
    """Signalet tælles udelukkende over SERVERENS egne forslag. Kom hans tekst
    med ad en bagdør, ville mønstret blive et spejl af ham — præcis det vi
    valgte fra."""
    raekker = _valg(*[("Kør testene igen", "accepteret")] * 12)
    for r in raekker:
        # En fremtidig kolonne kunne friste; den må aldrig havne i linjen.
        r["bruger_tekst"] = "nej, vent med testene"
    _saet(monkeypatch, raekker)
    assert "vent med testene" not in cm.moenster()


def test_linjen_er_en_ERFARING_ikke_en_ordre(monkeypatch):
    """Et forslag der altid beder om det samme, er en vane og ikke et tilbud.
    Modellen skal vægte, ikke adlyde."""
    _saet(monkeypatch, _valg(*[("Kør testene igen", "accepteret")] * 12))
    linje = cm.moenster()
    assert linje.startswith("Erfaring fra hans tidligere valg:")
    assert "skal" not in linje and "altid" not in linje


def test_kontakten_slukker_linjen(monkeypatch):
    _saet(monkeypatch, _valg(*[("Kør testene igen", "accepteret")] * 12))
    monkeypatch.setattr(cm, "er_taendt", lambda: False)
    assert cm.prompt_linje() == ""
    monkeypatch.setattr(cm, "er_taendt", lambda: True)
    assert cm.prompt_linje() != ""


def test_en_FEJL_i_moenstret_koster_ikke_forslaget(monkeypatch):
    """Komponisten må aldrig kunne gå i stykker af en erfaring."""
    monkeypatch.setattr(cm, "_valg_i_vinduet",
                        lambda: (_ for _ in ()).throw(RuntimeError("basen er nede")))
    assert cm.moenster() == ""


def test_forslaget_baerer_moenstret_MED_i_prompten(monkeypatch):
    """Den fælde huset kender: en sektion der er bygget, men aldrig når frem."""
    from core.services import composer_suggest as cs

    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "m1",
        "content": "Det er rettet og verificeret — testene er groenne igen."}])
    monkeypatch.setattr(cm, "prompt_linje", lambda: "Erfaring fra hans tidligere valg: X.")
    sendt: list[str] = []
    monkeypatch.setattr(cs, "_kald_model", lambda p: sendt.append(p) or "deploy det")
    cs.foreslaa_naeste("s1")
    assert "Erfaring fra hans tidligere valg: X." in sendt[0]
    assert sendt[0].rstrip().endswith("X."), "erfaringen står sidst, efter beskeden"


def test_moenstret_kan_SES_i_klartekst(isolated_runtime, monkeypatch):
    """Et moenster der former hans forslag, skal han kunne kigge paa. Ellers er
    det en profil der taler om ham bag hans ryg."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    _saet(monkeypatch, _valg(*[("Koer testene igen", "accepteret")] * 12))
    svar = rute.moenster()
    assert svar["taendt"] is True
    assert svar["valg_i_vinduet"] == 12 and svar["kraever_mindst"] == cm.MIN_VALG
    assert "koere noget" in svar["linje"] or "køre noget" in svar["linje"]


def test_ruten_siger_det_AERLIGT_naar_der_intet_er(isolated_runtime):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    svar = rute.moenster()
    assert svar["linje"] == "" and svar["valg_i_vinduet"] == 0
