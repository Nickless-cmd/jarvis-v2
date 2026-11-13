"""Referat af en autonom kørsel.

Bjørn 8/9-2026: de autonome runs «ligger i en session for sig selv så ser dem
ikke rigtigt». Han bad om at flytte dem; tallene sagde nej:

    auto-recurring-20260907   168 beskeder — heraf 155 TOOL-resultater

Så arbejdet bliver hvor det er, og et **referat** går derhen hvor han er.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.services.autonomous_run_digest import (
    _foerste_afsnit, byg_referat, post_referat,
)


def test_referatet_siger_hvad_koerslen_VAR():
    """Navnene er hans sprog: han skal kunne se hvad det var uden at slå op."""
    for sid, navn in (("auto-dream-20260908", "Drømme"),
                      ("auto-heartbeat-20260908", "Hjerteslag"),
                      ("auto-recurring-20260908", "Tilbagevendende"),
                      ("auto-wakeup-20260908", "Vækning")):
        ud = byg_referat(session_id=sid, output="Jeg kiggede på noget.")
        assert navn in ud


def test_en_koersel_uden_output_og_uden_aendringer_faar_INTET_referat():
    """«Jeg kørte og lavede ingenting» er støj, og der er 3-4 af dem om dagen."""
    assert byg_referat(session_id="auto-dream-1", output="", aendrede_filer=[]) == ""
    assert byg_referat(session_id="auto-dream-1", output="   ",
                       tool_calls=["read_file", "bash"]) == ""


def test_tool_listen_forkortes():
    """155 tool-beskeder var netop dét der gjorde sessionerne ulæselige."""
    ud = byg_referat(session_id="auto-work-1", output="Noget skete.",
                     tool_calls=[f"vaerktoej_{i}" for i in range(12)])
    assert "+7" in ud


def test_filer_vises_med_committet_eller_aendret():
    ja = byg_referat(session_id="auto-work-1", output="x",
                     aendrede_filer=["a.py"], committet=True)
    nej = byg_referat(session_id="auto-work-1", output="x",
                      aendrede_filer=["a.py"], committet=False)
    assert "Committet:" in ja and "Ændrede:" in nej


# ── uddraget ────────────────────────────────────────────────────────────────

def test_uddraget_klippes_ved_et_saetningsskel():
    """Et referat der selv ender midt i et ord ville være endnu en af de
    lækager der stod i den proaktive kanal."""
    lang = ("Første sætning er færdig her. " * 20)
    ud = _foerste_afsnit(lang)
    assert ud.endswith(".") and len(ud) <= 225


def test_kort_output_beholdes_helt():
    assert _foerste_afsnit("Kort og færdigt.") == "Kort og færdigt."


def test_tomt_output_giver_tom_streng():
    assert _foerste_afsnit("") == ""
    assert _foerste_afsnit(None) == ""  # type: ignore[arg-type]


# ── postningen (omskrevet 13/11-2026) ───────────────────────────────────────
#
# Referatet gik før til den sidst aktive SAMTALE. Målt 13/11: 18 baggrundsrun i
# døgnet gav 18 «🌙 Hjerteslag»-klumper midt i chatten, som Bjørn ikke kunne
# skelne fra den ægte puls. Bjørn: «de kunne lande i din inbak og lade værnet
# der styre inboxen». Testene måler nu INDBAKKE-vejen, og at chatten er urørt.

def _registreret() -> list[dict]:
    return []


def test_referatet_lander_i_indbakken_som_digest():
    skrevet = _registreret()

    def _fake(**kw):
        skrevet.append(kw)
        return {"status": "ok", "post_id": 1}

    with patch("core.services.inbox_state.registrer_kilde", side_effect=_fake), \
         patch("core.services.inbox_state._ejer_id", return_value="bjorn-1"):
        assert post_referat(run_id="r1", session_id="auto-dream-1",
                            output="Jeg læste mine drømme igennem.") == "referat-r1"

    assert skrevet[0]["kildetype"] == "digest"
    assert skrevet[0]["importance"] == "normal"
    assert "Drømme" in skrevet[0]["beskrivelse"]


def test_referatet_gaar_IKKE_til_chatten():
    """Den bærende vagt for hele ændringen. Uden den er flytningen kosmetisk:
    posten ville ligge begge steder, og chatten ville stadig være forurenet."""
    with patch("core.services.inbox_state.registrer_kilde",
               return_value={"status": "ok"}), \
         patch("core.services.inbox_state._ejer_id", return_value="bjorn-1"), \
         patch("core.services.notification_bridge.send_session_notification") as chat:
        post_referat(run_id="r1", session_id="auto-dream-1", output="noget nyt")
    chat.assert_not_called()


def test_digest_kan_ikke_gate():
    """Strukturel, ikke et grep: kildetypen skal stå i det sæt der afgør om en
    post må nægte en mutation. Et referat er ORIENTERING."""
    from core.services.inbox_state import IKKE_GATENDE_KILDETYPER

    assert "digest" in IKKE_GATENDE_KILDETYPER


def test_uden_ejer_skrives_der_ingenting():
    """En post uden ejer ville havne i den forkerte indbakke."""
    with patch("core.services.inbox_state._ejer_id", return_value=""), \
         patch("core.services.inbox_state.registrer_kilde") as m:
        assert post_referat(run_id="r1", session_id="auto-dream-1", output="noget") == ""
    m.assert_not_called()


def test_et_laekket_output_tages_IKKE_med():
    """Samme værn som den proaktive kanal: et referat der citerer maskineriet
    er lige så ubrugeligt som en tanke der gør det. Men filerne står stadig."""
    skrevet = _registreret()

    def _fake(**kw):
        skrevet.append(kw)
        return {"status": "ok"}

    with patch("core.services.inbox_state.registrer_kilde", side_effect=_fake), \
         patch("core.services.inbox_state._ejer_id", return_value="bjorn-1"):
        post_referat(run_id="r1", session_id="auto-work-1",
                     output="Initiative: a genuine next step — perhaps re-reading the trace.",
                     aendrede_filer=["core/x.py"], committet=True)
    assert "Initiative:" not in skrevet[0]["beskrivelse"]
    assert "core/x.py" in skrevet[0]["beskrivelse"]


def test_et_fejlende_referat_vaelter_ikke_afslutningen():
    with patch("core.services.inbox_state.registrer_kilde",
               side_effect=RuntimeError("væk")), \
         patch("core.services.inbox_state._ejer_id", return_value="bjorn-1"):
        assert post_referat(run_id="r1", session_id="auto-dream-1", output="x") == ""


def test_run_closure_kalder_referatet():
    """Uden koblingen ville modulet være endnu et der er bygget og ikke kaldt."""
    import inspect

    import core.services.run_closure_gate as R

    src = inspect.getsource(R._on_run_completed)
    assert "post_referat" in src
    # output skal være bundet FØR referatet læser den — uden tool-kald ville
    # navnet ellers ikke findes (samme unbound-name-fejl som _guard_py_escapes)
    assert src.index('output = ""') < src.index("output=output,")
