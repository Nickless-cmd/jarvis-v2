"""Et godkendelses-kort skal efterlade et spor når det BLIVER LAVET.

Målt 7/9-2026 på Bjørns historik:

    tool.approval_resolved      496
    tool.approval_requested       0   ← fandtes ikke

Man kunne altså tælle hvad han havde svaret på, aldrig hvad han var blevet
spurgt om. Da han sagde «jeg har ikk fået noget kort?», var der intet at holde
det op imod — spørgsmålet var ikke bare ubesvaret, det var ubesvarligt.

Det beviser ikke at kortet nåede skærmen. Men uden det er leveringen ikke
engang målbar, og målbarhed er betingelsen for at turde røre de sidste
uportede veje.
"""

from __future__ import annotations

import pytest


def test_haendelsen_baerer_det_man_skal_bruge_for_at_maale_levering(monkeypatch):
    from core.services import visible_runs as VR

    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        VR.event_bus, "publish",
        lambda navn, payload: set_events.append((navn, payload)),
    )

    VR._publicer_approval_requested(
        approval_id="approval-abc", tool="bash", run_id="visible-1",
        session_id="chat-1",
        result={"classification": "destructive", "gate_type": "exec_command"},
    )

    assert len(set_events) == 1
    navn, p = set_events[0]
    assert navn == "tool.approval_requested"
    # Uden approval_id kan anmodning og svar ikke parres, og maalingen er
    # meningsloes.
    assert p["approval_id"] == "approval-abc"
    assert p["tool"] == "bash"
    assert p["session_id"] == "chat-1"
    # Klassifikationen skiller «destruktiv» fra «aendrer systemet», saa man kan
    # se OM det er de farlige der forsvinder.
    assert p["classification"] == "destructive"


def test_telemetri_maa_aldrig_forhindre_kortet(monkeypatch):
    """Et event-bus der er nede maa ikke koste Bjoern godkendelsen.

    Kortet er det vigtige; sporet er til os.
    """
    from core.services import visible_runs as VR

    def eksploder(*a, **kw):
        raise RuntimeError("bus nede")

    monkeypatch.setattr(VR.event_bus, "publish", eksploder)
    VR._publicer_approval_requested(
        approval_id="a", tool="bash", run_id="r", session_id="s", result={},
    )  # maa ikke kaste


def test_et_resultat_uden_klassifikation_giver_tomme_felter_ikke_fejl(monkeypatch):
    from core.services import visible_runs as VR

    set_events: list[tuple[str, dict]] = []
    monkeypatch.setattr(VR.event_bus, "publish",
                        lambda n, p: set_events.append((n, p)))
    VR._publicer_approval_requested(
        approval_id="a", tool="write_file", run_id="r", session_id="s", result=None,
    )
    assert set_events[0][1]["classification"] == ""


@pytest.mark.parametrize("linje", [
    "_publicer_approval_requested(",
])
def test_BEGGE_kortsteder_publicerer(linje):
    """visible_runs har to steder der laver kort: den simple og den agentiske sti.

    Rammer man kun det ene, maaler man kun halvdelen af turene — og det ville
    se ud som om leveringen var daarligere eller bedre end den er.
    """
    import pathlib
    kilde = pathlib.Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"
    tekst = kilde.read_text(encoding="utf-8")
    assert tekst.count(linje) >= 3, (
        "forventede definitionen + BEGGE kald; fandt %d" % tekst.count(linje)
    )
