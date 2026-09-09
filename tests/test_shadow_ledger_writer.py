"""Skygge-skrivningen — den første kobling mellem drift og ledgeren.

Fase 1: «Keep legacy sessions authoritative in `chat_messages`; shadow-write
only selected test sessions.»

Den ene regel der betyder alt: skyggen må aldrig kunne vælte den ægte
skrivning. Men den må heller ikke tie — en stille skygge er det værste af
begge dele: man tror man måler, og man måler ingenting.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_chat_messages as C
from core.services import projection_drift as D
from core.services import shadow_ledger_writer as S
from core.services.chat_sessions import append_chat_message


def _ro(grænse: float = 5.0) -> None:
    """Vent på de baggrundstråde `append_chat_message` selv starter.

    En brugerbesked udløser `emotion_concepts._safe_persist` i en tråd, og den
    kører `CREATE TABLE IF NOT EXISTS` før sin skrivning — DDL tager en
    eksklusiv lås. Skriver testen næste besked imens, får DEN
    «database is locked» på sit eget `INSERT INTO chat_messages`.

    Det er ikke ledgerens fejl og heller ikke testens: det er systemets egen
    adfærd. Ventetiden skjuler den ikke, den venter bare på den — så det der
    måles er ledgeren og ikke trådenes timing.
    """
    import threading
    import time
    slut = time.monotonic() + grænse
    while time.monotonic() < slut:
        levende = [t for t in threading.enumerate()
                   if t is not threading.current_thread() and t.is_alive()
                   and ("_safe_persist" in t.name or "eventbus-writer" == t.name)]
        if not any("_safe_persist" in t.name for t in levende):
            return
        time.sleep(0.01)

TID = "2026-09-09T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _rene_taellere():
    S._nulstil_for_tests()
    yield
    S._nulstil_for_tests()


@pytest.fixture
def sid(isolated_runtime):
    s = "sh-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _raekker(sid):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT message_id, role, content FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]


# ── legacy: skyggen rører intet ──────────────────────────────────────────

def test_en_LEGACY_session_skriver_ikke_i_ledgeren(sid):
    """Alle sessioner er legacy indtil nogen flytter en. Skyggen skal koste
    dem ingenting."""
    append_chat_message(session_id=sid, role="user", content="hej", created_at=TID)
    assert L.current_seq(sid) == 0
    assert S.taellere()["sprunget_over"] == 1
    assert S.taellere()["skrevet"] == 0


# ── shadow: begge steder ─────────────────────────────────────────────────

def test_en_SHADOW_session_skriver_begge_steder(sid):
    L.advance_storage_mode(sid, to="shadow")
    append_chat_message(session_id=sid, role="user", content="hej", created_at=TID)
    assert len(_raekker(sid)) == 1
    assert [e["event_id"] for e in L.read_session_events(sid)] == [_raekker(sid)[0]["message_id"]]


def test_de_to_sider_er_ENIGE_efter_en_rigtig_samtale(sid):
    L.advance_storage_mode(sid, to="shadow")
    for r, t in [("user", "hej"), ("assistant", "hej selv"), ("user", "hvad så")]:
        append_chat_message(session_id=sid, role=r, content=t, created_at=TID)
    r = D.compare(sid)
    assert r["enige"] is True and r["ledger_beskeder"] == 3


def test_alle_felter_foelger_med(sid):
    L.advance_storage_mode(sid, to="shadow")
    append_chat_message(session_id=sid, role="assistant", content="svar",
                        created_at=TID, reasoning_content="tænkte",
                        user_id="bjorn", workspace_name="w",
                        content_json='[{"type": "text"}]')
    p = L.read_session_events(sid)[0]["payload"]
    assert p["reasoning_content"] == "tænkte" and p["user_id"] == "bjorn"
    assert D.compare(sid)["enige"] is True


# ── det der ville have ødelagt skiftet ───────────────────────────────────

def test_message_id_BEVARES_saa_skiftet_ikke_dublerer_samtalen(sid):
    """Udledte projektoren sit eget id ved skiftet, ville den lægge den samme
    samtale ind én gang til ved siden af sig selv — uden at nogen kunne se
    hvilken var den ægte."""
    L.advance_storage_mode(sid, to="shadow")
    append_chat_message(session_id=sid, role="user", content="hej", created_at=TID)
    append_chat_message(session_id=sid, role="assistant", content="hej selv", created_at=TID)
    foer = _raekker(sid)

    C.register()
    C.rebuild(sid)                       # som ved et skifte
    efter = _raekker(sid)

    assert len(efter) == 2
    assert [r["message_id"] for r in efter] == [r["message_id"] for r in foer]


def test_samme_besked_to_gange_bliver_til_EN_haendelse(sid):
    """`message_id` som event_id gør skrivningen idempotent."""
    L.advance_storage_mode(sid, to="shadow")
    r = append_chat_message(session_id=sid, role="user", content="hej", created_at=TID)
    S.shadow_append(sid, message_id=r["id"], role="user", content="hej", created_at=TID)
    assert L.current_seq(sid) == 1


# ── skyggen må ikke vælte den ægte skrivning ─────────────────────────────

def test_en_DOED_ledger_koster_ikke_brugerens_besked(sid, monkeypatch):
    """Hvis brugeren mister sin besked fordi et eksperiment fejlede, er
    eksperimentet værre end det problem det skulle løse."""
    L.advance_storage_mode(sid, to="shadow")
    monkeypatch.setattr(L, "append_session_events",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ledger nede")))
    r = append_chat_message(session_id=sid, role="user", content="vigtig", created_at=TID)
    assert r["content"] == "vigtig"
    assert [x["content"] for x in _raekker(sid)] == ["vigtig"]


def test_en_OPTAGET_lease_blokerer_IKKE_skyggen(sid):
    """Skygge-skrivningen tager ingen lease — dét er hele grunden til at den
    kun koster én transaktion. En lease en anden holder, er derfor uden
    betydning her; ledgeren er ikke sandheden i skygge-tilstand."""
    L.advance_storage_mode(sid, to="shadow")
    L.acquire_write_lease(sid, owner="en-anden-proces")
    append_chat_message(session_id=sid, role="user", content="vigtig", created_at=TID)
    assert [x["content"] for x in _raekker(sid)] == ["vigtig"]
    assert L.current_seq(sid) == 1
    assert S.taellere()["fejl"] == 0


def test_skyggen_koster_EN_transaktion_ikke_tre(sid, monkeypatch):
    """Den ejede vej er tag-lease, skriv, giv-fri. På den varmeste sti der
    findes, i en database hvor to processer skriver samtidig, er det forkert."""
    L.advance_storage_mode(sid, to="shadow")
    kald = []
    for navn in ("acquire_write_lease", "release_write_lease", "append_session_events"):
        monkeypatch.setattr(L, navn,
                            (lambda n: lambda *a, **k: kald.append(n))(navn))
    append_chat_message(session_id=sid, role="user", content="x", created_at=TID)
    assert kald == [] and L.current_seq(sid) == 1


def test_en_fejlet_skygge_TIER_IKKE(sid, monkeypatch):
    """En stille skygge er det værste af begge dele: man tror man måler, og
    man måler ingenting."""
    L.advance_storage_mode(sid, to="shadow")
    monkeypatch.setattr(L, "append_unowned",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    append_chat_message(session_id=sid, role="user", content="x", created_at=TID)
    assert S.taellere()["fejl"] == 1


def test_en_fejlet_skygge_HOLDER_SKIFTET_LUKKET(sid, monkeypatch):
    """Det gør ikke noget at en skygge fejler, så længe porten ved det."""
    L.advance_storage_mode(sid, to="shadow")
    append_chat_message(session_id=sid, role="user", content="en", created_at=TID)

    # Fejlen tændes og slukkes med et flag frem for monkeypatch.undo():
    # `isolated_runtime` bruger SELV monkeypatch til at flytte HOME, og et
    # undo() ville rulle DEN tilbage — så resten af testen ville kigge i den
    # ægte database uden at det kunne ses.
    nede = {"ja": True}
    aegte = L.append_unowned
    monkeypatch.setattr(L, "append_unowned",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede"))
                        if nede["ja"] else aegte(*a, **k))
    append_chat_message(session_id=sid, role="user", content="to", created_at=TID)
    nede["ja"] = False

    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False and "uenighed" in hvorfor


def test_en_LEDGER_session_afviser_skrivning_uden_ejerskab(sid):
    """Afkaldet på fencing er bundet af KODE, ikke af disciplin: bliver
    ledgeren kanonisk, skal skrivning gå gennem et SessionHandle."""
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    with pytest.raises(PermissionError, match="SessionHandle"):
        L.append_unowned(sid, events=[{"event_id": "e1", "kind": "message",
                                       "payload": {"role": "user", "content": "x"}}])
