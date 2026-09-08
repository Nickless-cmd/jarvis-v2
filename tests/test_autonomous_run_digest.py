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


# ── postningen ──────────────────────────────────────────────────────────────

def test_referatet_lander_i_hans_sidst_aktive_samtale():
    skrevet: list = []
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale",
               return_value="chat-abc"), \
         patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: skrevet.append(kw)):
        assert post_referat(run_id="r1", session_id="auto-dream-1",
                            output="Jeg læste mine drømme igennem.") == "chat-abc"
    assert skrevet[0]["session_id"] == "chat-abc"
    assert "Drømme" in skrevet[0]["content"]


def test_uden_en_frisk_samtale_skrives_der_ingenting():
    """Ellers ville referatet ligge i en silo igen — præcis det han klagede over."""
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale", return_value=""), \
         patch("core.services.chat_sessions.append_chat_message") as m:
        assert post_referat(run_id="r1", session_id="auto-dream-1", output="noget") == ""
    m.assert_not_called()


def test_et_laekket_output_tages_IKKE_med():
    """Samme værn som den proaktive kanal: et referat der citerer maskineriet
    er lige så ubrugeligt som en tanke der gør det. Men filerne står stadig."""
    skrevet: list = []
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale",
               return_value="chat-abc"), \
         patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: skrevet.append(kw)):
        post_referat(run_id="r1", session_id="auto-work-1",
                     output="Initiative: a genuine next step — perhaps re-reading the trace.",
                     aendrede_filer=["core/x.py"], committet=True)
    assert "Initiative:" not in skrevet[0]["content"]
    assert "core/x.py" in skrevet[0]["content"]


def test_et_fejlende_referat_vaelter_ikke_afslutningen():
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale",
               side_effect=RuntimeError("væk")):
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
