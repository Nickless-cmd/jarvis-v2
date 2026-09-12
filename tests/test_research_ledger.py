"""Research-runnet i session-ledgeren — Fase A4.

Et research-run lever ellers udelukkende i sin egen `research_*`-store. Det
overlever genstart, men det er ikke en del af *sessionens* historik: åbner man
ledgeren for at se hvad der skete i en samtale, er runnet usynligt.

Kontrakten er den samme som skygge-skrivningen, og den ene regel betyder alt:
**research må aldrig kunne vælte turen.** Skrivningen sker efter at runnet selv
har skrevet sin sandhed, og den kaster aldrig.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import research_ledger as R


@pytest.fixture(autouse=True)
def _rene_taellere():
    R._nulstil_for_tests()
    yield
    R._nulstil_for_tests()


@pytest.fixture
def sid(isolated_runtime):
    s = "rs-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute(
            "INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
            "VALUES (?, 'T', ?, ?)",
            (s, "2026-09-13T10:00:00+00:00", "2026-09-13T10:00:00+00:00"),
        )
    return s


def _events(sid):
    return L.read_session_events(sid)


# ── legacy: runnet skrives alligevel ─────────────────────────────────────

def test_en_LEGACY_session_skriver_runnet(sid):
    """Legacy-sessioner skrives OGSÅ.

    Det er hele pointen med A4: 478 af 482 sessioner er legacy, så skrev vi
    kun for skygge-sessioner, ville featuren være usynlig i praksis. Det er
    forsvarligt, fordi hændelsen har `kind="research"` og hver eneste læser
    af ledgeren filtrerer på `kind` (drift, projektion, recovery — målt
    13/9-2026). Et research-run er metadata OM en tur, ikke turen selv.
    """
    ok = R.record_run_started(sid, run_id="r1", tier="orchestrated", query="hvad?")
    assert ok is True
    ev = _events(sid)
    assert len(ev) == 1 and ev[0]["kind"] == "research"
    assert R.taellere()["skrevet"] == 1
    assert R.taellere()["sprunget_over"] == 0


def test_en_kanonisk_LEDGER_session_springes_over(sid):
    """I `ledger`-mode kræver skrivning et SessionHandle med lease. Et
    research-run må ikke tage ejerskabet fra turen — vi springer over."""
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    ok = R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    assert ok is False
    assert _events(sid) == []
    assert R.taellere()["sprunget_over"] == 1


# ── shadow: runnet bliver synligt ────────────────────────────────────────

def test_en_SHADOW_session_skriver_runnet(sid):
    L.advance_storage_mode(sid, to="shadow")
    ok = R.record_run_started(sid, run_id="r1", tier="orchestrated", query="hvad?")
    assert ok is True
    ev = _events(sid)
    assert len(ev) == 1
    assert ev[0]["event_id"] == "r1:started"
    assert ev[0]["payload"]["event"] == "research_started"
    assert ev[0]["payload"]["tier"] == "orchestrated"
    assert R.taellere()["skrevet"] == 1


def test_start_og_slut_er_to_nummererede_haendelser(sid):
    L.advance_storage_mode(sid, to="shadow")
    R.record_run_started(sid, run_id="r1", tier="orchestrated", query="q")
    R.record_run_completed(
        sid, run_id="r1", sources=4, quality="passed", timed_out=False, tool_calls=9,
    )
    ev = _events(sid)
    assert [e["seq"] for e in ev] == [1, 2]
    assert [e["payload"]["event"] for e in ev] == ["research_started", "research_completed"]
    assert ev[1]["payload"]["sources"] == 4
    assert ev[1]["payload"]["tool_calls"] == 9


def test_run_id_er_idempotens_noeglen(sid):
    """Samme run skrevet igennem to gange — genstart, retry — bliver ÉN række.

    Det er derfor `event_id` er ``f"{run_id}:started"`` og ikke et uuid4:
    identiteten ER nøglen.
    """
    L.advance_storage_mode(sid, to="shadow")
    assert R.record_run_started(sid, run_id="r1", tier="inline", query="q") is True
    R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    assert len(_events(sid)) == 1
    assert L.current_seq(sid) == 1


def test_to_forskellige_runs_er_to_raekker(sid):
    L.advance_storage_mode(sid, to="shadow")
    R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    R.record_run_started(sid, run_id="r2", tier="inline", query="q")
    assert [e["event_id"] for e in _events(sid)] == ["r1:started", "r2:started"]


# ── kanter: sidecar-hændelsen må ikke forstyrre resten ───────────────────

def test_research_haendelsen_forstyrrer_IKKE_drift(sid):
    """Drift-sammenligningen måler BESKEDER. Et research-run i ledgeren må
    ikke få den til at melde uenighed — den filtrerer på `kind`."""
    from core.services import projection_drift as D

    L.advance_storage_mode(sid, to="shadow")
    R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    r = D.compare(sid)
    assert r["enige"] is True and r["ledger_beskeder"] == 0


def test_research_haendelsen_BLOKERER_ikke_en_canary_migrering(sid):
    """Målt 13/9-2026: `ledger_canary.backfill` sammenlignede ALLE
    ledger-hændelser mod tabel-beskederne, så en sidecar-hændelse fik
    præfiks-tjekket til at afvise en ellers ren migrering. Invarianten handler
    om besked-rækkefølgen — og det er nu også det den måler."""
    from core.services import ledger_canary as K

    with connect() as c:
        for i in range(3):
            c.execute(
                "INSERT INTO chat_messages (message_id, session_id, role, content, "
                "created_at) VALUES (?, ?, 'user', ?, ?)",
                (f"m{i}-{sid}", sid, f"besked {i}", f"2026-09-13T10:0{i}:00+00:00"),
            )
    # Et research-run lander FØR migreringen — det er den rækkefølge der skete.
    R.record_run_started(sid, run_id="r1", tier="inline", query="q")

    r = K.backfill(sid)
    assert r["skrevet"] == 3, r
    assert L.current_seq(sid) == 4  # 1 research + 3 beskeder


def test_en_LEDGER_session_springes_over_uden_at_kaste(sid):
    """Den kanoniske vej kræver ejerskab. Vi skipper — og det koster intet."""
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    assert R.record_run_started(sid, run_id="r1", tier="inline", query="q") is False
    assert _events(sid) == []


# ── det må ikke kunne vælte et run ───────────────────────────────────────

def test_en_doed_ledger_kaster_ikke(sid, monkeypatch):
    """Et run der dør fordi det ikke kunne skrive en metadatalinje, ville være
    et eksperiment der er værre end det problem det løser."""
    L.advance_storage_mode(sid, to="shadow")
    monkeypatch.setattr(
        L, "append_unowned",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ledger nede")),
    )
    ok = R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    assert ok is False
    assert R.taellere()["fejl"] == 1
    assert R.taellere()["skrevet"] == 0


def test_tomt_session_id_springes_over():
    """Uden en session er der ingen række at skrive i — og det skal ikke kaste."""
    assert R.record_research_event("", event_id="r1:started", event="x") is False
    assert R.record_research_event("s", event_id="", event="x") is False
    assert R.taellere()["sprunget_over"] == 2


def test_taellerne_er_et_spejl_ikke_sandheden(sid):
    """`False` betyder IKKE at runnet fejlede — kun at metadatalinjen ikke
    landede. Tælleren er stedet at kigge når noget ser skævt ud."""
    L.advance_storage_mode(sid, to="shadow")
    R.record_run_started(sid, run_id="r1", tier="inline", query="q")
    R.record_run_completed(
        sid, run_id="r1", sources=0, quality="not_evaluated",
        timed_out=False, tool_calls=0,
    )
    t = R.taellere()
    assert t["skrevet"] == 2 and t["fejl"] == 0 and t["sprunget_over"] == 0
