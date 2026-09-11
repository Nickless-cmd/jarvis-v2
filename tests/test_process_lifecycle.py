"""Flaget der ikke fandtes — og som syv tabte runder hang på."""
from __future__ import annotations

import threading

from core.runtime import process_lifecycle as pl


def setup_function() -> None:
    pl.nulstil_til_test()


def test_starter_som_ikke_lukkende():
    assert pl.lukker_ned() is False
    assert pl.grund() == ""


def test_markering_holder():
    pl.markér_nedlukning("SIGTERM")
    assert pl.lukker_ned() is True
    assert pl.grund() == "SIGTERM"


def test_idempotent_foerste_grund_vinder():
    """Anden markering maa ikke overskrive hvorfor vi lukker."""
    pl.markér_nedlukning("SIGTERM")
    pl.markér_nedlukning("noget andet")
    assert pl.grund() == "SIGTERM"


def test_tom_grund_bliver_alligevel_til_noget_laesbart():
    pl.markér_nedlukning()
    assert pl.grund() == "shutdown"


def test_flere_traade_ser_det_samme():
    """Loekken koerer i en anden traad end lifespan-hooken."""
    set_af: list[bool] = []
    klar = threading.Event()

    def laeser() -> None:
        klar.wait(timeout=2)
        set_af.append(pl.lukker_ned())

    t = threading.Thread(target=laeser)
    t.start()
    pl.markér_nedlukning("SIGTERM")
    klar.set()
    t.join(timeout=3)
    assert set_af == [True]


# ---------------------------------------------------------------------------
# Flaget nytter kun hvis nogen SPØRGER det.
# ---------------------------------------------------------------------------

def _loekkens_vagt() -> str:
    """Kildeteksten fra løkkehovedet til den første `break`."""
    import re
    src = open("core/services/visible_runs.py", encoding="utf-8").read()
    i = src.index("for _agentic_round in range(_AGENTIC_MAX_ROUNDS):")
    return src[i:i + 3000]


def test_loekken_spoerger_flaget_ved_rundegraensen():
    vagt = _loekkens_vagt()
    assert "lukker_ned" in vagt, "løkken spørger ikke om processen lukker"
    assert '_agentic_loop_exit_reason = "shutdown"' in vagt
    assert "break" in vagt


def test_nedlukning_bruger_IKKE_force_finalize():
    """`_force_finalize_next` sætter `_is_last_round` → `tool_choice="none"`
    → ét LLM-kald mere. På en døende proces er det præcis det man ikke vil:
    kaldet når sjældent at blive færdigt, og turen taber alligevel runden.

    Vejen efter løkken er ren bogføring — ingen udbyder røres."""
    vagt = _loekkens_vagt()
    i = vagt.index("lukker_ned")
    j = vagt.index("break", i)
    assert "_force_finalize_next" not in vagt[i:j], \
        "nedluknings-vagten tvinger en finalize — det koster et LLM-kald"


def test_vagten_staar_FOER_rundens_arbejde():
    """Den skal fyre før runde-start-eventet og før udbyder-kaldet, ellers har
    vi brugt runden inden vi opdagede at vi lukkede."""
    vagt = _loekkens_vagt()
    assert vagt.index("lukker_ned") < vagt.index("_publish_agentic_round_start")


# ---------------------------------------------------------------------------
# EN VAGT DER FÅR BESKED SIDST KAN ALDRIG NÅ AT SIGE FRA
#
# Tre offer-ture blev kappet med vilje 11/9-2026. Vagten fyrede nul gange,
# fordi lifespan-shutdown kører SIDST i uvicorns nedlukning — efter
# forbindelserne er revet ned:
#
#     08:25:11  Waiting for application shutdown.
#     08:25:13  visible-run unhandled exception: chat session not found
#     08:25:13  proces markeret til nedlukning: lifespan-shutdown
#
# Flaget blev sat i samme sekund som runnet døde.
# ---------------------------------------------------------------------------

def test_signalvagten_saetter_flaget_naar_signalet_ankommer():
    import signal
    kaldt: list[int] = []
    forrige = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda s, f: kaldt.append(s))
    try:
        pl.installer_signalvagt()
        assert pl.lukker_ned() is False, "maa ikke fyre foer signalet"
        signal.raise_signal(signal.SIGTERM)
        assert pl.lukker_ned() is True, "flaget blev ikke sat af signalet"
        assert kaldt == [signal.SIGTERM], \
            "den oprindelige handler blev ikke kaldt — processen ville aldrig lukke"
    finally:
        signal.signal(signal.SIGTERM, forrige)


def test_signalvagten_erstatter_ikke_uvicorns_handler():
    """Uden videresendelse ville processen ikke lukke ned overhovedet."""
    import signal
    set_af: list[str] = []
    forrige = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda s, f: set_af.append("uvicorn"))
    try:
        pl.installer_signalvagt()
        signal.raise_signal(signal.SIGTERM)
        assert set_af == ["uvicorn"]
    finally:
        signal.signal(signal.SIGTERM, forrige)


def test_vagten_installeres_FOER_alt_andet_i_lifespan():
    """Kildetekst-test: rækkefølgen i lifespan er hele pointen."""
    src = open("apps/api/jarvis_api/app.py", encoding="utf-8").read()
    i = src.index("async def lifespan(")
    vindue = src[i:i + 1400]
    assert "installer_signalvagt" in vindue
    assert vindue.index("installer_signalvagt") < vindue.index("wire_root_logging")
