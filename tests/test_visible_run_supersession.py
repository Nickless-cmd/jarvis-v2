"""Et stop er endeligt; en ny besked er ikke et stop.

Opgave 5. De to ting lignede hinanden i journalen: begge endte en tur. Men et
stop skal aldrig genoptages, og en ny besked midt i en tur skal styre den —
ikke slette opgaven. Blev brugerens besked ikke leveret, hører den stadig til
opgaven og skal følge med ind i fortsættelsen.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D
from core.services.visible_run_segment_settlement import settle_user_stop


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    return poster


def test_et_stop_bliver_ALDRIG_genoptaget():
    """Uden dette lignede stoppet en afbrudt tur — og en afbrudt tur genoptages.
    Brugeren ville se sit eget stop starte igen af sig selv."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="skriv en rapport")
    ud = settle_user_stop(run_id="r1", session_id="s1")
    assert ud.decision.should_continue is False
    assert ifr.claim_due_recovery(owner="nogen-anden") is None
    assert D.recover_due_once()["started"] == 0


def test_en_uleveret_besked_foelger_med_ind_i_fortsaettelsen(monkeypatch):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="ret cheap lane")
    assert ifr.queue_steer("r1", "og tjek testene bagefter") is True
    ifr.settle_recovering("r1", reason="shutdown", summary="ret cheap lane")

    kald: list[dict] = []
    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached",
        lambda **kw: kald.append(kw) or "visible-2")
    assert D.recover_due_once()["started"] == 1
    assert "ret cheap lane" in kald[0]["message"]
    assert "og tjek testene bagefter" in kald[0]["message"]


def test_samme_besked_to_gange_er_EN_besked():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ifr.queue_steer("r1", "husk migrationen")
    ifr.queue_steer("r1", "husk migrationen")
    assert ifr._load()["r1"]["pending_steers"] == ["husk migrationen"]


def test_en_ny_besked_sletter_ikke_den_koerende_opgave():
    """Supersession er ikke en afslutning: opgaven står, og posten bliver."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="den lange opgave")
    ifr.queue_steer("r1", "også det her")
    post = ifr._load()["r1"]
    assert post["status"] == "running"
    assert post["original_request"] == "den lange opgave"


def test_en_koe_paa_en_ukendt_opgave_siger_nej():
    assert ifr.queue_steer("findes-ikke", "hej") is False


def test_stoppet_afgoeres_af_HANDLINGEN_ikke_af_ordet():
    """Knappen kan hedde hvad som helst. Det der gør det til et stop, er at et
    menneske trykkede — ikke at grunden tilfældigvis står på en liste."""
    ifr.mark_started(run_id="r2", session_id="s1", user_message="x")
    ud = settle_user_stop(run_id="r2", session_id="s1", reason="stop-knap-i-desk")
    assert ud.decision.state.value == "cancelled", "et ukendt ord blev læst som «færdig»"
    assert ifr._load()["r2"]["status"] == "cancelled"
    assert ifr.claim_due_recovery(owner="nogen") is None


def test_en_ny_besked_STYRER_den_koerende_tur(monkeypatch):
    """Turen kører stadig: beskeden hører til DEN opgave og skal ind i løkken,
    ikke ved siden af den."""
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    from core.services.visible_runs_sections import detached_run as dr

    monkeypatch.setattr(rel, "claim_or_create", lambda sid, **kw: ("visible-kører", False))
    styringer: list[tuple[str, str]] = []
    monkeypatch.setattr(vr, "append_visible_run_steer",
                        lambda rid, tekst: styringer.append((rid, tekst)) or True)
    rid, attached = dr.start_or_attach_user_run(message="også tjekke testene",
                                                session_id="s1")
    assert attached is True and rid == "visible-kører"
    assert styringer == [("visible-kører", "også tjekke testene")]


def test_en_besked_der_ikke_kan_leveres_havner_i_koeen(monkeypatch):
    """Segmentet er ved at dø, så styringen bliver afvist. Beskeden må ikke
    forsvinde med det segment — den hører til opgaven."""
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    from core.services.visible_runs_sections import detached_run as dr

    ifr.mark_started(run_id="visible-doeende", session_id="s1", user_message="opgaven")
    monkeypatch.setattr(rel, "claim_or_create", lambda sid, **kw: ("visible-doeende", False))
    monkeypatch.setattr(vr, "append_visible_run_steer", lambda rid, tekst: False)
    dr.start_or_attach_user_run(message="husk migrationen", session_id="s1")
    assert ifr._load()["visible-doeende"]["pending_steers"] == ["husk migrationen"]
