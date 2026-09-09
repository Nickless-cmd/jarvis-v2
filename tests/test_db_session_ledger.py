"""Ledgerens tre invarianter — Fase 1's udgangs-kriterier.

Spec: `docs/specs/2026-09-08-deepseek-harness-lessons-for-jarvis.md`, Fase 1.

    «atomic append and idempotent replay tests pass under duplicate delivery
     and process restart»
    «a second process cannot acquire or append through a competing write
     handle, and a stale fencing token cannot write after lease loss»
    «read-only interrupted-session inspection writes nothing»
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_session_ledger as L


def _e(eid: str, kind: str = "turn/start", **payload):
    return {"event_id": eid, "kind": kind, "payload": payload}


@pytest.fixture
def sid(isolated_runtime):
    return "sess-" + datetime.now(UTC).strftime("%H%M%S%f")


# ── 1: sekvensen er tæt og pr. session ───────────────────────────────────

def test_sekvensen_starter_paa_1_og_har_ingen_huller(sid):
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t, events=[_e("e1"), _e("e2"), _e("e3")])
    assert [x["seq"] for x in L.read_session_events(sid)] == [1, 2, 3]


def test_sekvensen_er_PR_SESSION(sid):
    andet = sid + "-b"
    ta = L.acquire_write_lease(sid, owner="a")
    tb = L.acquire_write_lease(andet, owner="b")
    L.append_session_events(sid, owner="a", token=ta, events=[_e("x1")])
    L.append_session_events(andet, owner="b", token=tb, events=[_e("y1")])
    assert L.current_seq(sid) == 1 and L.current_seq(andet) == 1


def test_en_tom_session_har_sekvens_nul(sid):
    assert L.current_seq(sid) == 0
    assert L.read_session_events(sid) == []


# ── 2: append er atomisk og idempotent ───────────────────────────────────

def test_samme_event_id_to_gange_giver_EN_raekke(sid):
    """Genlevering må ikke fordoble turen — hverken ved gentagelse eller
    efter en genstart hvor afsenderen ikke ved hvad der nåede frem."""
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t, events=[_e("e1"), _e("e2")])
    r = L.append_session_events(sid, owner="a", token=t, events=[_e("e1"), _e("e2"), _e("e3")])
    assert r["duplicates"] == 2 and r["written"] == 1
    assert [x["event_id"] for x in L.read_session_events(sid)] == ["e1", "e2", "e3"]


def test_en_dublet_midt_i_batchen_braekker_ikke_resten(sid):
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t, events=[_e("b")])
    r = L.append_session_events(sid, owner="a", token=t, events=[_e("a"), _e("b"), _e("c")])
    assert r["written"] == 2 and r["duplicates"] == 1


def test_en_haendelse_uden_event_id_afvises_og_INTET_lander(sid):
    """Atomisk betyder atomisk: en halv tur i ledgeren er værre end ingen,
    fordi den ser komplet ud."""
    t = L.acquire_write_lease(sid, owner="a")
    with pytest.raises(ValueError):
        L.append_session_events(sid, owner="a", token=t,
                                events=[_e("ok1"), {"kind": "uden-id"}])
    assert L.read_session_events(sid) == []


def test_en_tom_batch_er_en_no_op(sid):
    t = L.acquire_write_lease(sid, owner="a")
    assert L.append_session_events(sid, owner="a", token=t, events=[])["written"] == 0


# ── 3: kun lease-ejeren, og kun med sin egen mønt ────────────────────────

def test_to_ejere_kan_ikke_holde_samme_session(sid):
    assert L.acquire_write_lease(sid, owner="a") == 1
    assert L.acquire_write_lease(sid, owner="b") is None


def test_uden_lease_kan_der_ikke_skrives(sid):
    with pytest.raises(L.LeaseLost):
        L.append_session_events(sid, owner="a", token=1, events=[_e("e1")])


def test_en_FORAELDET_moent_afvises_efter_tab_af_lease(sid):
    """Kernen i fencing. Den gamle ejer VED ikke at han har mistet leasen —
    og skal heller ikke behøve at vide det. Møntet afgør sagen."""
    gammel = L.acquire_write_lease(sid, owner="a", ttl_s=1)
    forbi = datetime.now(UTC) + timedelta(seconds=5)
    ny = L.acquire_write_lease(sid, owner="b", now=forbi)
    assert ny is not None and ny > gammel

    with pytest.raises(L.LeaseLost):
        L.append_session_events(sid, owner="a", token=gammel,
                                events=[_e("sent")], now=forbi)
    # …mens den nye ejer godt kan.
    L.append_session_events(sid, owner="b", token=ny, events=[_e("ok")], now=forbi)
    assert [x["event_id"] for x in L.read_session_events(sid)] == ["ok"]


def test_moenten_stiger_MONOTONT_ogsaa_ved_overtagelse(sid):
    # Hver lease får en KORT levetid, ellers kan den næste ikke overtage —
    # og så måler testen bare at overtagelse blev nægtet.
    a = L.acquire_write_lease(sid, owner="a", ttl_s=1)
    forbi = datetime.now(UTC) + timedelta(seconds=5)
    b = L.acquire_write_lease(sid, owner="b", ttl_s=1, now=forbi)
    endnu = forbi + timedelta(seconds=5)
    c = L.acquire_write_lease(sid, owner="c", ttl_s=1, now=endnu)
    assert a is not None and b is not None and c is not None
    assert a < b < c


def test_fornyelse_hos_SAMME_ejer_beholder_moenten(sid):
    """Ellers ville en ejer ugyldiggøre sine egne igangværende skrivninger
    hver gang han fornyede."""
    a = L.acquire_write_lease(sid, owner="a")
    assert L.acquire_write_lease(sid, owner="a") == a


def test_en_UDLOEBET_lease_kan_ikke_skrive_selv_med_rigtig_moent(sid):
    t = L.acquire_write_lease(sid, owner="a", ttl_s=1)
    forbi = datetime.now(UTC) + timedelta(seconds=5)
    with pytest.raises(L.LeaseLost):
        L.append_session_events(sid, owner="a", token=t, events=[_e("e")], now=forbi)


def test_slip_kraever_den_rigtige_moent(sid):
    t = L.acquire_write_lease(sid, owner="a")
    assert L.release_write_lease(sid, owner="a", token=t + 99) is False
    assert L.release_write_lease(sid, owner="b", token=t) is False
    assert L.release_write_lease(sid, owner="a", token=t) is True
    assert L.lease_state(sid) is None


def test_at_slippe_noget_man_ikke_ejer_er_en_no_op_ikke_en_fejl(sid):
    assert L.release_write_lease(sid, owner="ingen", token=1) is False


# ── læsning må aldrig skrive ─────────────────────────────────────────────

def test_laesning_kraever_ingen_lease_og_efterlader_intet_spor(sid):
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t, events=[_e("e1")])
    L.release_write_lease(sid, owner="a", token=t)

    assert len(L.read_session_events(sid)) == 1
    assert L.lease_state(sid) is None, "en læsning må ikke oprette en lease"


def test_interval_laesning_er_halvaabent(sid):
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t,
                            events=[_e("e1"), _e("e2"), _e("e3"), _e("e4")])
    assert [x["seq"] for x in L.read_session_events(sid, from_seq=1, to_seq=3)] == [2, 3]


def test_nyttelasten_overlever_rundturen(sid):
    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t,
                            events=[_e("e1", "tool/call", navn="bash", args={"cmd": "ls"})])
    e = L.read_session_events(sid)[0]
    assert e["kind"] == "tool/call"
    assert e["payload"] == {"navn": "bash", "args": {"cmd": "ls"}}


# ── storage_mode: én kilde til sandhed pr. session ───────────────────────

def _opret(sid: str) -> None:
    from core.services import chat_sessions as cs
    cs.create_session(session_id=sid, title="t") if hasattr(cs, "create_session") else None


def test_en_ukendt_session_er_legacy(sid):
    """Det SIKRE svar. En tom ledger må aldrig kunne læses som «der er ingen
    historik» — så ville en fejlkonfiguration se ud som en tom samtale."""
    assert L.storage_mode("findes-slet-ikke") == "legacy"


def test_skiftet_kan_kun_gaa_FREMAD(sid, isolated_runtime):
    from core.runtime.db import connect
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 't', '2026-01-01', '2026-01-01')", (sid,))
    assert L.storage_mode(sid) == "legacy"

    assert L.advance_storage_mode(sid, to="shadow") is True
    assert L.storage_mode(sid) == "shadow"

    # baglæns: nej
    assert L.advance_storage_mode(sid, to="legacy") is False
    assert L.storage_mode(sid) == "shadow"
    # samme sted: også nej (ellers ville en gentagelse se ud som et skifte)
    assert L.advance_storage_mode(sid, to="shadow") is False

    assert L.advance_storage_mode(sid, to="ledger") is True
    assert L.storage_mode(sid) == "ledger"
    assert L.advance_storage_mode(sid, to="shadow") is False


def test_en_ukendt_tilstand_afvises_uden_at_aendre_noget(sid, isolated_runtime):
    from core.runtime.db import connect
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 't', '2026-01-01', '2026-01-01')", (sid,))
    assert L.advance_storage_mode(sid, to="noget-andet") is False
    assert L.storage_mode(sid) == "legacy"


def test_skiftet_paa_en_session_der_ikke_findes_goer_intet(sid):
    assert L.advance_storage_mode("findes-ikke", to="shadow") is False


# ── bussen er en notifikation om sandheden, ikke sandheden ───────────────

def test_en_DOED_eventbus_koster_ikke_en_committet_haendelse(sid, monkeypatch):
    """Fase 1: «eventbus loss does not lose committed ledger events».

    Lod vi en fejl på bussen boble op, ville en committet hændelse se ud som
    en fejlet skrivning — og kalderen ville prøve igen eller give op på noget
    der faktisk ligger i ledgeren."""
    import core.eventbus.bus as bus
    class _Doed:
        def publish(self, *a, **k):
            raise RuntimeError("bussen er nede")
    monkeypatch.setattr(bus, "event_bus", _Doed())

    t = L.acquire_write_lease(sid, owner="a")
    r = L.append_session_events(sid, owner="a", token=t, events=[
        {"event_id": "e1", "kind": "message", "payload": {"x": 1}}])

    assert r["written"] == 1
    assert [e["event_id"] for e in L.read_session_events(sid)] == ["e1"]


def test_der_annonceres_EFTER_commit_ikke_foer(sid, monkeypatch):
    """Publicerede vi før commit, kunne en lytter reagere på noget der aldrig
    blev skrevet."""
    import core.eventbus.bus as bus
    set_ved_publish = []
    class _Kigger:
        def publish(self, kind, payload=None, **k):
            set_ved_publish.append(len(L.read_session_events(payload["session_id"])))
    monkeypatch.setattr(bus, "event_bus", _Kigger())

    t = L.acquire_write_lease(sid, owner="a")
    L.append_session_events(sid, owner="a", token=t, events=[
        {"event_id": "e1", "kind": "message", "payload": {}}])
    assert set_ved_publish == [1]


def test_en_batch_uden_NYE_haendelser_annoncerer_intet(sid, monkeypatch):
    """Ellers ville en genafspilning larme på bussen uden at der skete noget."""
    import core.eventbus.bus as bus
    kald = []
    class _Taeller:
        def publish(self, *a, **k): kald.append(1)
    monkeypatch.setattr(bus, "event_bus", _Taeller())

    t = L.acquire_write_lease(sid, owner="a")
    ev = [{"event_id": "e1", "kind": "message", "payload": {}}]
    L.append_session_events(sid, owner="a", token=t, events=ev)
    L.append_session_events(sid, owner="a", token=t, events=ev)   # dublet
    assert kald == [1]
