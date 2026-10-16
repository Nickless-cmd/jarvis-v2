"""Wakeup-dispatch-skip → indbakken (13/10-2026).

Bjørn: «Så kør wakeup dispatch skip i indbak».

Dispatcheren springer en fyret vækning over når en tur kører i dens session.
For afvisningen `user_active` prøver den den ALDRIG igen — vækningen stod
derfor kun i awareness. Nu løfter `inbox_idle_waker` den når intet kører.

Den TREDJE klasse (`KAN_DISPATCHES_KILDETYPER`) er hele forskellen: en post
der MÅ starte et run, men ALDRIG må nægte en mutation.

Det farlige led er modenheden. Vækningens post oprettes ved BOOKINGEN, ikke
ved fyringen — så uden `_er_moden` ville vækkeren starte et run for en vækning
der først fyrer i morgen, og gøre det hver eneste poll-runde.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    sti = tmp_path / "skip.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _vaeknings_post(bruger="bjorn", id="wake-abc", **kw) -> dict:
    """En væknings indbakke-post som bookingen skriver den.

    Målt 13/10-2026: `kraever_handling=0` — vækninger gater ikke i praksis,
    fordi `opret_eller_hent` giver gatende poster en frist der udløber.
    """
    r = db_inbox.opret_eller_hent(
        bruger_id=bruger, kildetype=kw.pop("kildetype", "wakeup"), kilde_id=id,
        oprettende_run_id="visible-abc",
        verificeret_ejer=kw.pop("ejer", db_inbox.EJER_JARVIS),
        kraever_handling=kw.pop("kraever_handling", False),
        beskrivelse=kw.pop("beskrivelse", "foelg op"), **kw)
    assert r["status"] == "ok", r
    return r["post"]


def _record(wid="wake-abc", **kw) -> dict:
    r = {"wakeup_id": wid, "status": "fired", "prompt": "Tjek CI",
         "reason": "r1", "session_id": "chat-1"}
    r.update(kw)
    return r


# ── den tredje klasse ───────────────────────────────────────────────────────

def test_wakeup_er_dispatchbar_men_ikke_gatende():
    """Sættet siger «må starte et run» — det rører ikke gating-flaget."""
    from core.services.inbox_state import KAN_DISPATCHES_KILDETYPER, kan_dispatch

    assert kan_dispatch("wakeup") is True
    assert kan_dispatch("run_closure") is False
    # Grænsen: de to sæt er UAFHÆNGIGE. Blev «må dispatche» blandet sammen med
    # «må gate», ville en vækning kunne låse det næste værktøjskald.
    assert "wakeup" not in KAN_DISPATCHES_KILDETYPER.symmetric_difference({"wakeup"})


# ── modenhed: fyret OG sprunget ─────────────────────────────────────────────

def test_ufyret_vaekning_loeftes_ikke(inbox_db, monkeypatch):
    """Posten findes fra bookingen. Uden modenheds-test ville den køre nu."""
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-abc")
    monkeypatch.setattr(w, "_wakeup_records", lambda: {})

    assert w.kandidater("bjorn") == []


def test_ufyret_frisk_gatende_vaekning_loeftes_ikke(inbox_db, monkeypatch):
    """En frisk booking maa ikke omgaa sit ur via det generelle opgaveflag.

    En Jarvis-ejet wakeup registreres med ``kraever_handling=1`` mens det run,
    der booker den, stadig lever. Efter en genstart er runnet væk, og
    indbakke-vækkeren poller straks. Kildens tomme modenheds-svar er stadig
    autoritativt: wakeup'en er ikke fyret og må derfor ikke blive kandidat.
    """
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-fremtid", kraever_handling=True)
    monkeypatch.setattr(w, "_wakeup_records", lambda: {})

    assert w.kandidater("bjorn") == []


def test_sprunget_vaekning_loeftes(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-abc")
    monkeypatch.setattr(w, "_wakeup_records", lambda: {"wake-abc": _record()})

    ids = [p["kilde_id"] for p in w.kandidater("bjorn")]
    assert ids == ["wake-abc"]


def test_ventende_efter_skip_kraever_fired_og_sprunget(monkeypatch):
    """Kilden er den eneste der kan svare på «er den moden»."""
    import core.services.self_wakeup as sw

    poster = [
        _record("w-fyret-sprunget", dispatch_skipped=True),
        _record("w-pending", status="pending", dispatch_skipped=True),
        _record("w-fyret-uden-skip"),
        _record("w-allerede-dispatchet", dispatch_skipped=True, dispatched=True),
        _record("w-forbrugt", status="consumed", dispatch_skipped=True),
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(poster))

    ids = [r["wakeup_id"] for r in sw.ventende_efter_skip()]
    assert ids == ["w-fyret-sprunget"], (
        "kun FYRET + SPRUNGET + ikke-dispatchet + ikke-forbrugt må løftes"
    )


def test_allerede_dispatchet_loeftes_ikke(inbox_db, monkeypatch):
    """En vækning der BLEV dispatchet i et senere tick bærer stadig sit
    skip-flag. Uden `dispatched`-guarden ville vækkeren starte et run oveni
    — den dublet vi fjerner."""
    import core.services.self_wakeup as sw

    monkeypatch.setattr(sw, "_load", lambda: [
        _record("w-disp", dispatch_skipped=True, dispatched=True)])
    assert sw.ventende_efter_skip() == []


# ── hvad runnet får med ─────────────────────────────────────────────────────

def test_loeftet_run_bruger_vaekningens_direktiv_og_session(inbox_db, monkeypatch):
    """Runnet skal køre i DEN SAMTALE vækningen blev booket fra — og med den
    samme instruktion dispatcheren ville have givet."""
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-abc")
    monkeypatch.setattr(w, "_wakeup_records", lambda: {"wake-abc": _record()})
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    kaldt: list[dict] = []
    monkeypatch.setattr(w, "_start_run",
                        lambda tekst, **kw: kaldt.append({"tekst": tekst, **kw}))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")

    assert r["vaekket"] == 1
    assert len(kaldt) == 1
    assert "wake-abc" in kaldt[0]["tekst"], "direktivet skal navngive vækningen"
    assert "[wakeup:no-update]" in kaldt[0]["tekst"], "5/10-reglen skal med"
    assert kaldt[0]["session_id"] == "chat-1", (
        "en sprunget vækning hører til sin egen samtale, ikke en auto-session"
    )


def test_loeftet_post_gater_stadig_ikke(inbox_db, monkeypatch):
    """Vækkeren må ikke give posten magt ved at løfte den."""
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-abc")
    monkeypatch.setattr(w, "_wakeup_records", lambda: {"wake-abc": _record()})
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: None)

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="wake-abc")
    assert post["kraever_handling"] == 0
    assert post["verificeret_ejer"] == db_inbox.EJER_JARVIS


def test_samme_vaekning_loeftes_kun_en_gang(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    _vaeknings_post(id="wake-abc")
    monkeypatch.setattr(w, "_wakeup_records", lambda: {"wake-abc": _record()})
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet: list[str] = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0
    assert len(startet) == 1


# ── én definition af direktivet ─────────────────────────────────────────────

def test_dispatcheren_bruger_den_faelles_tekst(monkeypatch):
    """To kopier ville drive fra hinanden — den ene ville mangle 5/10-reglen."""
    import core.services.self_wakeup as sw
    import core.services.wakeup_dispatcher as wd

    kaldt: list[dict] = []
    monkeypatch.setattr(sw, "direktiv_for",
                        lambda rec: kaldt.append(rec) or "FELLES")
    monkeypatch.setattr(wd, "_active_turn_blocks", lambda sid: "")
    monkeypatch.setattr(wd, "pick_wakeup_run_target", lambda **k: "sess-1")
    monkeypatch.setattr(sw, "due_wakeups", lambda **k: [_record()])
    monkeypatch.setattr(sw, "_load", lambda: [_record()])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: type("S", (), {"nudge_system_enabled": False})(),
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification", lambda *a, **k: None)
    monkeypatch.setattr(
        "core.services.heartbeat_phases.tick_with_phases", lambda *a, **k: None)
    sendt: list[str] = []
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda tekst, **k: sendt.append(tekst))

    r = wd.dispatch_due_wakeups()

    assert r["dispatched"] == 1
    assert kaldt and kaldt[0]["wakeup_id"] == "wake-abc"
    assert sendt == ["FELLES"]
