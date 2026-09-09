"""Efterfyldning og skygge-start på en RIGTIG session.

Rækkefølgen er ikke en detalje: slog man bare skyggen til, ville ledgeren have
3 beskeder og tabellen 300 — drift ville melde uenighed for altid, og porten
ville aldrig kunne åbne. Skyggen ville måle ingenting.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import ledger_canary as K
from core.services import projection_chat_messages as C
from core.services import projection_drift as D
from core.services.chat_sessions import append_chat_message


# `_ro()` — en venteløkke for systemets egne baggrundstråde — stod her indtil
# 9/9-2026. Den var en OMGÅELSE af at `emotion_concepts` startede en tråd (og
# dermed en ny sqlite-forbindelse) pr. brugerbesked, hvilket gav «database is
# locked» på testens eget INSERT i ~50 % af kørslerne.
#
# Kilden er rettet: persisteringen bruger nu én arbejdstråd med én genbrugt
# forbindelse. Målt bagefter: 0 af 10 kørsler fejler uden ventetiden.
TID = "2026-09-09T10:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "kn-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _historik(sid, n):
    for i in range(n):
        append_chat_message(session_id=sid, role="user" if i % 2 == 0 else "assistant",
                            content=f"besked {i}", created_at=TID)


# ── efterfyldningen ──────────────────────────────────────────────────────

def test_historikken_havner_i_ledgeren(sid):
    _historik(sid, 5)
    r = K.backfill(sid)
    assert r["beskeder"] == 5 and r["skrevet"] == 5
    assert L.current_seq(sid) == 5


def test_efterfyldningen_kan_koeres_IGEN_uden_dubletter(sid):
    """Det farlige øjeblik er ikke det første forsøg, men det andet — når
    nogen er i tvivl om det gik godt."""
    _historik(sid, 4)
    K.backfill(sid)
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and r["dubletter"] == 4
    assert L.current_seq(sid) == 4


def test_raekkefoelgen_bevares(sid):
    _historik(sid, 6)
    K.backfill(sid)
    assert [e["payload"]["content"] for e in L.read_session_events(sid)] == \
           [f"besked {i}" for i in range(6)]


def test_en_tom_session_efterfyldes_ikke(sid):
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and "ingen beskeder" in r["grund"]


def test_en_optaget_lease_efterfylder_IKKE_halvt(sid):
    _historik(sid, 3)
    L.acquire_write_lease(sid, owner="en-anden")
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and L.current_seq(sid) == 0


# ── skyggen slås til ─────────────────────────────────────────────────────

def test_efterfyldning_FOER_skifte_giver_enighed(sid):
    _historik(sid, 10)
    r = K.enable_shadow(sid)
    assert r["ok"] is True
    assert r["drift"]["enige"] is True
    assert r["drift"]["ledger"] == r["drift"]["tabel"] == 10
    assert L.storage_mode(sid) == "shadow"


def test_nye_beskeder_efter_skiftet_holder_siderne_enige(sid):
    _historik(sid, 5)
    K.enable_shadow(sid)
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    d = D.compare(sid)
    assert d["enige"] is True and d["ledger_beskeder"] == 6


def test_sessionen_kan_derefter_SKIFTE(sid):
    """Hele pointen: efter efterfyldning + skygge er porten åben."""
    _historik(sid, 5)
    K.enable_shadow(sid)
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is True and "6 beskeder" in hvorfor


def test_UDEN_efterfyldning_kan_porten_aldrig_aabne(sid):
    """Bevis for hvorfor rækkefølgen ikke er en detalje."""
    _historik(sid, 10)
    L.advance_storage_mode(sid, to="shadow")          # skyggen alene, ingen historik
    append_chat_message(session_id=sid, role="user", content="ny", created_at=TID)
    ok, _ = D.may_cut_over(sid)
    assert ok is False


def test_en_session_der_allerede_er_flyttet_roeres_ikke(sid):
    _historik(sid, 3)
    K.enable_shadow(sid)
    r = K.enable_shadow(sid)
    assert r["ok"] is False and "allerede" in r["grund"]


def test_skiftet_kan_fortrydes_og_skrivningen_stopper(sid):
    """Et eksperiment man ikke kan slukke, bliver stående tændt."""
    _historik(sid, 3)
    K.enable_shadow(sid)
    assert L.abandon_shadow(sid) is True
    append_chat_message(session_id=sid, role="user", content="efter", created_at=TID)
    assert L.current_seq(sid) == 3                     # ingen ny hændelse


def test_hele_vejen_igennem_kan_samtalen_genskabes(sid):
    """Efterfyld, skygge, nye beskeder, riv rækkerne ud, byg dem op igen."""
    _historik(sid, 8)
    K.enable_shadow(sid)
    append_chat_message(session_id=sid, role="assistant", content="ny", created_at=TID)
    with connect() as c:
        foer = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
        c.execute("DELETE FROM chat_messages WHERE session_id = ?", (sid,))
    C.register()
    C.rebuild(sid)
    with connect() as c:
        efter = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
    assert efter == foer


# ── kompakt-markører ─────────────────────────────────────────────────────

def _markoer(sid, tekst="opsummering", sha="abc123"):
    from core.services.chat_sessions import store_compact_marker
    return store_compact_marker(sid, tekst, sha)


def test_markoerer_efterfyldes_MED(sid):
    """De blev udeladt i første udgave. De er `chat_messages`-rækker som alle
    andre, og en projektion der ikke kendte dem, ville tabe dem ved et skifte."""
    _historik(sid, 4)
    _markoer(sid)
    r = K.backfill(sid)
    assert r["beskeder"] == 5 and r["skrevet"] == 5
    roller = [e["payload"]["role"] for e in L.read_session_events(sid)]
    assert roller.count("compact_marker") == 1


def test_en_NY_markoer_skygge_skrives(sid):
    _historik(sid, 3)
    K.enable_shadow(sid)
    _markoer(sid, "ny opsummering")
    assert L.current_seq(sid) == 4
    assert L.read_session_events(sid)[-1]["payload"]["content"] == "ny opsummering"


def test_git_sha_paa_markoeren_overlever(sid):
    _historik(sid, 2)
    K.enable_shadow(sid)
    _markoer(sid, "x", sha="deadbeef")
    assert L.read_session_events(sid)[-1]["payload"]["git_sha"] == "deadbeef"


def test_drift_ser_en_markoer_der_MANGLER_i_ledgeren(sid):
    """Præcis den tilstand «Kode-session» stod i, før dette blev rettet."""
    _historik(sid, 3)
    _markoer(sid)
    L.advance_storage_mode(sid, to="shadow")     # skygge UDEN efterfyldning
    d = D.compare(sid)
    assert d["enige"] is False and d["tabel_beskeder"] == 4


def test_en_samtale_MED_markoer_genskabes_helt(sid):
    _historik(sid, 5)
    _markoer(sid, "midtvejs")
    K.enable_shadow(sid)
    with connect() as c:
        foer = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, git_sha FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
        c.execute("DELETE FROM chat_messages WHERE session_id = ?", (sid,))
    C.register()
    C.rebuild(sid)
    with connect() as c:
        efter = [dict(r) for r in c.execute(
            "SELECT message_id, role, content, git_sha FROM chat_messages "
            "WHERE session_id = ? ORDER BY id", (sid,))]
    assert efter == foer
    assert any(r["role"] == "compact_marker" for r in efter)


def test_en_LEDGER_session_skriver_markoeren_GENNEM_ledgeren(sid):
    """Landminen er ryddet — bevidst, som den gamle test krævede.

    Indtil markør-skrivningen var koblet til et `SessionHandle`, KASTEDE dette
    kald på skrive-vagten. Det var den rigtige opførsel dengang: fejl højt frem
    for tavst at skrive en række der ikke kan genskabes. Nu går markøren samme
    vej som enhver anden besked, og projektoren laver rækken.
    """
    _historik(sid, 2)
    K.enable_shadow(sid)
    L.advance_storage_mode(sid, to="ledger")

    mid = _markoer(sid, "opsummering", sha="cafe123")

    # hændelsen er i ledgeren …
    sidste = L.read_session_events(sid)[-1]
    assert sidste["event_id"] == mid
    assert sidste["payload"]["role"] == "compact_marker"
    assert sidste["payload"]["git_sha"] == "cafe123"

    # … og RÆKKEN findes, fordi handlet kørte projektoren
    with connect() as c:
        r = c.execute("SELECT role, content, git_sha FROM chat_messages "
                      "WHERE message_id = ?", (mid,)).fetchone()
    assert r is not None and r[0] == "compact_marker" and r[2] == "cafe123"


# ── et hul i MIDTEN kan ikke lappes ved at føje til ──────────────────────

def _hul_i_midten(sid):
    """Efterlign den tilstand «Kode-session» stod i: en række findes i tabellen
    på plads N, men mangler i ledgeren, som ellers har resten."""
    _historik(sid, 3)
    _markoer(sid, "midtvejs")
    _historik(sid, 3)
    L.advance_storage_mode(sid, to="shadow")
    with connect() as c:
        ids = [r[0] for r in c.execute(
            "SELECT message_id FROM chat_messages WHERE session_id = ? "
            "AND role != 'compact_marker' ORDER BY id", (sid,))]
    t = L.acquire_write_lease(sid, owner="t")
    L.append_session_events(sid, owner="t", token=t, events=[
        {"event_id": i, "kind": "message",
         "payload": {"message_id": i, "role": "user", "content": "x",
                     "created_at": TID}} for i in ids])
    L.release_write_lease(sid, owner="t", token=t)


def test_efterfyldning_AFVISER_naar_den_ville_lande_bagerst(sid):
    """Målt på «Kode-session» 9/9: markøren manglede på plads 474, blev lagt
    på seq 579, og drift meldte 291 uenigheder. At føje til alligevel ville
    lave en ledger der SER fyldt ud og er forkert."""
    _hul_i_midten(sid)
    foer = L.current_seq(sid)
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and "reseed" in r["grund"]
    assert L.current_seq(sid) == foer          # intet blev lagt bagerst


def test_reseed_skriver_helt_om_og_genopretter_raekkefoelgen(sid):
    _hul_i_midten(sid)
    r = K.reseed(sid)
    assert r["ok"] is True and r["drift"]["enige"] is True
    roller = [e["payload"]["role"] for e in L.read_session_events(sid)]
    assert roller[3] == "compact_marker"       # tilbage på sin plads


def test_reseed_afviser_en_LEDGER_session(sid):
    """Dér ville det være at kassere historik, ikke at rette en måling."""
    _historik(sid, 2)
    K.enable_shadow(sid)
    L.advance_storage_mode(sid, to="ledger")
    r = K.reseed(sid)
    assert r["ok"] is False and "shadow" in r["grund"]


def test_reseed_afviser_en_LEGACY_session(sid):
    _historik(sid, 2)
    assert K.reseed(sid)["ok"] is False


def test_en_ren_efterfyldning_er_stadig_tilladt(sid):
    """Præfiks-vagten må ikke stå i vejen for det normale tilfælde: ledgeren
    er et præfiks af tabellen, og resten skal føjes til."""
    _historik(sid, 5)
    K.enable_shadow(sid)
    _historik(sid, 2)                          # skygge-skrevet, altså i takt
    r = K.backfill(sid)
    assert r["skrevet"] == 0 and r.get("dubletter") == 7
