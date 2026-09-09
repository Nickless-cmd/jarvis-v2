"""Kompatibilitets-projektoren.

Fase 1's udgangskriterium: «projector can rebuild selected `chat_messages` rows
from an empty projection». Kan de IKKE genskabes, er ledgeren ikke sandheden —
og så skal ingen session flyttes.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_chat_messages as C
from core.services import projection_runtime as P


@pytest.fixture(autouse=True)
def _rent_register():
    P._unregister_all_for_tests()
    C.register()
    yield
    P._unregister_all_for_tests()


@pytest.fixture
def sid(isolated_runtime):
    s = "cm-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, "2026-09-09T09:00:00+00:00",
                                            "2026-09-09T09:00:00+00:00"))
    return s


def _besked(eid: str, rolle: str, tekst: str, **ekstra):
    p = {"role": rolle, "content": tekst, "created_at": "2026-09-09T10:00:00+00:00"}
    p.update(ekstra)
    return {"event_id": eid, "kind": "message", "payload": p}


def _skriv(sid: str, *events):
    t = L.acquire_write_lease(sid, owner="test")
    L.append_session_events(sid, owner="test", token=t, events=list(events))
    L.release_write_lease(sid, owner="test", token=t)


def _raekker(sid: str):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT message_id, role, content, user_id, reasoning_content, "
            "content_json, created_at FROM chat_messages WHERE session_id = ? "
            "ORDER BY id", (sid,))]


# ── genskabelse ──────────────────────────────────────────────────────────

def test_raekkerne_genskabes_fra_en_TOM_projektion(sid):
    _skriv(sid,
           _besked("e1", "user", "hej"),
           _besked("e2", "assistant", "hej selv"))
    r = C.rebuild(sid)
    assert r["state"]["skrevet"] == 2
    assert [(x["role"], x["content"]) for x in _raekker(sid)] == [
        ("user", "hej"), ("assistant", "hej selv")]


def test_alle_felter_overlever_turen(sid):
    _skriv(sid, _besked("e1", "assistant", "svar",
                        user_id="bjorn", workspace_name="w",
                        reasoning_content="tænkte", git_sha="abc123",
                        content_json=[{"type": "text", "text": "svar"}]))
    C.rebuild(sid)
    r = _raekker(sid)[0]
    assert r["user_id"] == "bjorn" and r["reasoning_content"] == "tænkte"
    assert '"type": "text"' in r["content_json"]
    assert r["created_at"] == "2026-09-09T10:00:00+00:00"


def test_tiden_kommer_fra_HAENDELSEN_ikke_fra_now(sid):
    """Ellers ville hver genfoldning flytte hele samtalen frem i tid."""
    _skriv(sid, _besked("e1", "user", "hej"))
    C.rebuild(sid)
    foer = _raekker(sid)[0]["created_at"]
    C.rebuild(sid)
    assert _raekker(sid)[0]["created_at"] == foer == "2026-09-09T10:00:00+00:00"


# ── genafspilning fordobler ikke ─────────────────────────────────────────

def test_TRE_genfoldninger_giver_stadig_to_raekker(sid):
    """Kernen: det oprindelige skrive-kald bruger uuid4 og ville lave en ny
    række hver gang. Projektoren UDLEDER id'et af hændelsen."""
    _skriv(sid, _besked("e1", "user", "hej"), _besked("e2", "assistant", "hej"))
    for _ in range(3):
        C.rebuild(sid)
    assert len(_raekker(sid)) == 2


def test_et_nedbrud_mellem_raekken_og_markoeren_fordobler_ikke(sid):
    """Nedbruddet efterlignes: rækken skrives, markøren rykkes ikke, der
    foldes igen over de samme hændelser."""
    _skriv(sid, _besked("e1", "user", "hej"))
    C.fold(C.start(), {"session_id": sid, "event_id": "e1", "kind": "message",
                       "payload": {"role": "user", "content": "hej"}})
    P.project(sid, C.PROJEKTION, force_refold=True)
    assert len(_raekker(sid)) == 1


def test_id_et_er_stabilt_paa_tvaers_af_processer(sid):
    a = C.message_id_for(sid, "e1")
    assert a == C.message_id_for(sid, "e1")
    assert a != C.message_id_for(sid, "e2")
    assert a != C.message_id_for("anden-session", "e1")


def test_en_rettet_fold_KONVERGERER(sid):
    """Derfor DO UPDATE og ikke DO NOTHING: en projektion skal kunne rettes,
    ikke bevare en gammel udregning fordi rækken tilfældigvis fandtes."""
    _skriv(sid, _besked("e1", "user", "forkert"))
    C.rebuild(sid)
    with connect() as c:
        c.execute("UPDATE chat_messages SET content = 'håndrettet' WHERE session_id = ?", (sid,))
    C.rebuild(sid)
    assert _raekker(sid)[0]["content"] == "forkert"


# ── validering: hverken tavs eller fatal ─────────────────────────────────

@pytest.mark.parametrize("payload,grund", [
    ({"content": "x"}, "mangler role"),
    ({"role": "user"}, "mangler content"),
    ({"role": " ", "content": "x"}, "mangler role"),
    ({"role": "user", "content": "x", "content_json": 7}, "content_json"),
])
def test_ugyldige_haendelser_afvises_med_en_GRUND(payload, grund):
    fejl = C.valider(payload)
    assert fejl is not None and grund in fejl


def test_en_ugyldig_haendelse_spaerrer_ikke_resten_af_samtalen(sid):
    """Validering der KASTER ville lukke sessionen for altid; validering der
    TIER ville være værre."""
    _skriv(sid,
           _besked("e1", "user", "før"),
           {"event_id": "e2", "kind": "message", "payload": {"content": "uden rolle"}},
           _besked("e3", "user", "efter"))
    r = C.rebuild(sid)
    assert r["state"]["skrevet"] == 2
    assert r["state"]["afviste"] == [{"event_id": "e2", "grund": "mangler role"}]
    assert [x["content"] for x in _raekker(sid)] == ["før", "efter"]


def test_andre_haendelsestyper_roerer_ikke_tabellen(sid):
    _skriv(sid, {"event_id": "e1", "kind": "lease_taget", "payload": {"hvem": "x"}})
    r = C.rebuild(sid)
    assert r["state"]["sprunget_over"] == 1 and _raekker(sid) == []


def test_en_tom_session_giver_ingen_raekker(sid):
    assert C.rebuild(sid)["state"] == {"skrevet": 0, "sprunget_over": 0, "afviste": []}


# ── kun projektoren skriver for en ledger-session ────────────────────────

def test_direkte_skrivning_afvises_naar_sessionen_er_i_LEDGER(sid):
    """Uden vagten ville skiftet give DOBBELT sandhed frem for at flytte den:
    nogle rækker foldet, andre skrevet udenom, og ingen måde at se hvilke."""
    from core.services.chat_sessions import append_chat_message
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    with pytest.raises(C.DirekteSkrivningAfvist):
        append_chat_message(session_id=sid, role="user", content="udenom")
    assert _raekker(sid) == []


def test_projektoren_selv_skriver_stadig_i_ledger_tilstand(sid):
    L.advance_storage_mode(sid, to="shadow")
    L.advance_storage_mode(sid, to="ledger")
    _skriv(sid, _besked("e1", "user", "gennem ledgeren"))
    C.rebuild(sid)
    assert [x["content"] for x in _raekker(sid)] == ["gennem ledgeren"]


@pytest.mark.parametrize("mode", ["legacy", "shadow"])
def test_direkte_skrivning_er_uroert_indtil_skiftet(sid, mode):
    """Vagten må ikke ændre noget for de sessioner der ikke er flyttet — og
    det er dem alle sammen lige nu."""
    from core.services.chat_sessions import append_chat_message
    if mode == "shadow":
        L.advance_storage_mode(sid, to="shadow")
    append_chat_message(session_id=sid, role="user", content="som altid")
    assert [x["content"] for x in _raekker(sid)] == ["som altid"]


def test_en_ulaeselig_tilstand_goer_ikke_samtalen_skrivebeskyttet(sid, monkeypatch):
    from core.services.chat_sessions import append_chat_message
    import core.runtime.db_session_ledger as _L
    monkeypatch.setattr(_L, "storage_mode",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nej")))
    append_chat_message(session_id=sid, role="user", content="stadig muligt")
    assert len(_raekker(sid)) == 1


def test_vagten_aabner_IKKE_en_ny_forbindelse_naar_den_faar_en(sid):
    """Forbindelserne er poolede: `with connect()` inde i et andet `with
    connect()` er den SAMME forbindelse — og committer den ydre transaktion
    når det indre blok slutter. En vagt der kaldes midt i en skrivning må
    derfor ikke åbne sin egen."""
    import core.runtime.db_session_ledger as _L
    from core.runtime.db import connect as _connect
    with _connect() as conn:
        kaldt = []
        aegte = _L.connect
        _L.connect = lambda *a, **k: kaldt.append(1) or aegte()
        try:
            C.guard_direct_write(sid, conn=conn)
        finally:
            _L.connect = aegte
    assert kaldt == []
