"""Drift-detektionen — det der gør skygge-tilstanden mere end dobbelt arbejde.

Fase 1: «drift detection reports no mismatch for canary fixtures». Uden en
sammenligning har man skrevet begge steder i uger og ved stadig ikke om de er
enige.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import projection_drift as D
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


@pytest.fixture
def sid(isolated_runtime):
    s = "dr-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    L.advance_storage_mode(s, to="shadow")
    return s


def _begge(sid: str, rolle: str, tekst: str, **ekstra):
    """Skriv som skygge-tilstanden gør det: begge steder.

    Den skrev tidligere BEGGE sider selv. Siden `append_chat_message` fik sin
    skygge-skrivning, er den anden halvdel produktionens arbejde — og en
    hjælper der gjorde det igen, ville skrive hver besked to gange og teste en
    verden der ikke findes.
    """
    append_chat_message(session_id=sid, role=rolle, content=tekst,
                        created_at=TID, **ekstra)
    _ro()


def _kun_tabellen(sid: str, rolle: str, tekst: str, **ekstra):
    """En besked der KUN når tabellen.

    Siden skygge-skrivningen blev en del af `append_chat_message`, kan man
    ikke længere lave den slags ad normal vej — og det er en god ting. I
    virkeligheden opstår uenighed kun når skygge-skrivningen FEJLER, så det er
    sådan den fremstilles her: ledgeren er nede i præcis det ene kald.

    (En optaget lease duer ikke længere: skygge-skrivningen tager ingen lease.)
    """
    aegte = L.append_unowned
    L.append_unowned = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede"))
    try:
        append_chat_message(session_id=sid, role=rolle, content=tekst,
                            created_at=TID, **ekstra)
    finally:
        L.append_unowned = aegte
    _ro()


def _kun_ledger(sid: str, eid: str, rolle: str, tekst: str, **ekstra):
    p = {"role": rolle, "content": tekst, "created_at": TID}
    p.update(ekstra)
    t = L.acquire_write_lease(sid, owner="s")
    L.append_session_events(sid, owner="s", token=t, events=[
        {"event_id": eid, "kind": "message", "payload": p}])
    L.release_write_lease(sid, owner="s", token=t)


# ── kanarie-fikstur: ingen uenighed ──────────────────────────────────────

def test_en_almindelig_samtale_giver_NUL_uenigheder(sid):
    _begge(sid, "user", "hej")
    _begge(sid, "assistant", "hej selv")
    _begge(sid, "user", "hvad så")
    r = D.compare(sid)
    assert r["enige"] is True and r["uenigheder"] == []
    assert r["ledger_beskeder"] == r["tabel_beskeder"] == 3


def test_raesonnement_og_content_json_taeller_med(sid):
    _begge(sid, "assistant", "svar", reasoning_content="tænkte",
           content_json='[{"type": "text", "text": "svar"}]')
    assert D.compare(sid)["enige"] is True


def test_message_id_er_IKKE_en_uenighed(sid):
    """uuid4 mod et udledt id kan aldrig blive ens — og skal ikke: id'et er en
    nøgle, ikke indhold. At kræve dem ens ville gøre hver session falsk uenig."""
    _begge(sid, "user", "hej")
    with connect() as c:
        ids = [r[0] for r in c.execute(
            "SELECT message_id FROM chat_messages WHERE session_id = ?", (sid,))]
    from core.services.projection_chat_messages import message_id_for
    assert ids[0] != message_id_for(sid, "e1")
    assert D.compare(sid)["enige"] is True


def test_content_json_som_tekst_vs_objekt_er_ikke_uenighed(sid):
    """Forskel i FORM, ikke i indhold. En detektor der flagede den ville
    larme om noget ingen kan rette."""
    _kun_tabellen(sid, "assistant", "x", content_json='{"b": 2, "a": 1}')
    _kun_ledger(sid, "e1", "assistant", "x", content_json={"a": 1, "b": 2})
    assert D.compare(sid)["enige"] is True


# ── uenigheder findes, og de siger HVOR ──────────────────────────────────

def test_forskelligt_indhold_peger_paa_plads_og_felt(sid):
    _kun_tabellen(sid, "user", "tabellen")
    _kun_ledger(sid, "e1", "user", "ledgeren")
    r = D.compare(sid)
    assert r["enige"] is False
    assert r["uenigheder"] == [{"plads": 0, "felt": "content",
                                "ledger": "ledgeren", "tabel": "tabellen"}]


def test_en_besked_kun_i_ledgeren_ses(sid):
    _begge(sid, "user", "hej")
    _kun_ledger(sid, "e2", "assistant", "kun her")
    r = D.compare(sid)
    assert r["enige"] is False and r["uenigheder"][0]["tabel"] is None


def test_en_besked_kun_i_tabellen_ses(sid):
    """Sådan ser en FEJLET skygge-skrivning ud i drift."""
    _begge(sid, "user", "hej")
    _kun_tabellen(sid, "assistant", "kun her")
    r = D.compare(sid)
    assert r["enige"] is False and r["uenigheder"][0]["ledger"] is None


def test_forkert_RAEKKEFOELGE_er_en_uenighed(sid):
    """To sider med de samme beskeder i forskellig orden er ikke enige — det
    er en samtale hvor svaret kommer før spørgsmålet."""
    _kun_tabellen(sid, "user", "a")
    _kun_tabellen(sid, "user", "b")
    _kun_ledger(sid, "e1", "user", "b")
    _kun_ledger(sid, "e2", "user", "a")
    assert D.compare(sid)["enige"] is False


def test_sammenligningen_SKRIVER_ingenting(sid):
    """En sammenligning der ændrer det den måler, måler ikke."""
    _begge(sid, "user", "hej")
    def _fingeraftryk():
        with connect() as c:
            return (list(c.execute("SELECT * FROM chat_messages WHERE session_id = ?", (sid,))),
                    L.current_seq(sid))
    foer = _fingeraftryk()
    D.compare(sid)
    assert _fingeraftryk() == foer


# ── må sessionen skifte? ─────────────────────────────────────────────────

def test_en_enig_shadow_session_maa_skifte(sid):
    _begge(sid, "user", "hej")
    _begge(sid, "assistant", "hej selv")
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is True and "2 beskeder" in hvorfor


def test_en_TOM_ledger_maa_ALDRIG_skifte(sid):
    """En tom ledger og en tom sammenligning ser ens ud. Et skifte dér ville
    gøre en samtale til ingenting."""
    _kun_tabellen(sid, "user", "findes kun i tabellen")
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False


def test_en_helt_tom_session_maa_heller_ikke_skifte(sid):
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False and "tom" in hvorfor


def test_uenighed_blokerer_skiftet_og_siger_hvorfor(sid):
    _kun_tabellen(sid, "user", "tabellen")
    _kun_ledger(sid, "e1", "user", "ledgeren")
    ok, hvorfor = D.may_cut_over(sid)
    assert ok is False and "uenighed" in hvorfor


def test_et_spring_direkte_fra_LEGACY_afvises(sid, isolated_runtime):
    """Ledgeren skal have været prøvet mod virkeligheden først."""
    s = "dr-legacy-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    ok, hvorfor = D.may_cut_over(s)
    assert ok is False and "legacy" in hvorfor
