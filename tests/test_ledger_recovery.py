"""Afbrudte sessioner — Fase 1's sidste kriterium.

    «read-only interrupted-session inspection writes nothing; recovery appends
     balancing events only under write ownership»

De to halvdele hører sammen: kræver det at KIGGE skriveretten, tager man den
enten fra den proces der stadig arbejder, eller også lader man være med at
kigge. Begge dele er værre end problemet.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime.db import connect
from core.services import ledger_recovery as R

TID = "2026-09-09T12:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "rc-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _tur(sid, *roller):
    t = L.acquire_write_lease(sid, owner="t")
    L.append_session_events(sid, owner="t", token=t, events=[
        {"event_id": f"e{L.current_seq(sid) + 1 + i}", "kind": "message",
         "payload": {"role": r, "content": r, "created_at": TID}}
        for i, r in enumerate(roller)])
    L.release_write_lease(sid, owner="t", token=t)


# ── inspektionen skriver INTET ───────────────────────────────────────────

def test_inspektionen_efterlader_ingen_spor(sid):
    _tur(sid, "user", "assistant", "user")
    L.acquire_write_lease(sid, owner="init")
    with connect() as c:
        c.execute("DELETE FROM session_write_leases WHERE session_id = ?", (sid,))

    def _aftryk():
        with connect() as c:
            return (list(c.execute("SELECT * FROM session_write_leases WHERE session_id = ?", (sid,))),
                    L.current_seq(sid))
    foer = _aftryk()
    R.inspect(sid)
    assert _aftryk() == foer


def test_inspektionen_virker_mens_en_ANDEN_holder_leasen(sid):
    """Den hyppigste grund til at kigge er at finde ud af hvad der gik galt —
    og det må ikke kræve at man tager retten fra den der stadig arbejder."""
    _tur(sid, "user")
    L.acquire_write_lease(sid, owner="stadig-i-gang")
    f = R.inspect(sid)
    assert f["ubalanceret"] is True


# ── hvad «ubalanceret» betyder ───────────────────────────────────────────

def test_en_afsluttet_tur_er_i_balance(sid):
    _tur(sid, "user", "assistant")
    assert R.inspect(sid)["ubalanceret"] is False


def test_en_tur_der_ender_paa_brugeren_er_ABEN(sid):
    _tur(sid, "user", "assistant", "user")
    f = R.inspect(sid)
    assert f["ubalanceret"] is True and f["sidste_rolle"] == "user" and f["sidste_seq"] == 3


def test_en_tom_session_er_ikke_ubalanceret(sid):
    assert R.inspect(sid)["ubalanceret"] is False


# ── genopretning kræver skriveret ────────────────────────────────────────

def test_uden_ejerskab_skrives_der_IKKE(sid):
    """Punktum. Det er hele forskellen på at inspicere og at genoprette."""
    _tur(sid, "user")
    L.acquire_write_lease(sid, owner="en-anden-proces")
    foer = L.current_seq(sid)
    r = R.recover(sid)
    assert r["skrevet"] is False and "skriveret" in r["grund"]
    assert L.current_seq(sid) == foer


def test_med_ejerskab_tilfoejes_en_balancerende_haendelse(sid):
    _tur(sid, "user", "assistant", "user")
    r = R.recover(sid, grund="streamen brast")
    assert r["skrevet"] is True and r["for_seq"] == 3
    sidste = L.read_session_events(sid)[-1]
    assert sidste["kind"] == R.BALANCE_KIND
    assert sidste["payload"]["for_seq"] == 3
    assert sidste["payload"]["grund"] == "streamen brast"


def test_historikken_bliver_LAENGERE_aldrig_kortere(sid):
    """Ledgeren er append-only. En afbrudt tur bliver ikke ugjort ved at slette
    den — det ville være at lyve om hvad der skete."""
    _tur(sid, "user", "assistant", "user")
    foer = [e["event_id"] for e in L.read_session_events(sid)]
    R.recover(sid)
    efter = [e["event_id"] for e in L.read_session_events(sid)]
    assert efter[:len(foer)] == foer and len(efter) == len(foer) + 1


def test_en_BALANCERET_tur_genoprettes_ikke_igen(sid):
    """En genopretning der «for en sikkerheds skyld» tilføjer en hændelse,
    ville gøre historikken usand."""
    _tur(sid, "user")
    R.recover(sid)
    n = L.current_seq(sid)
    r = R.recover(sid)
    assert r["skrevet"] is False and L.current_seq(sid) == n


def test_en_LUKKET_tur_genoprettes_ikke(sid):
    _tur(sid, "user", "assistant")
    assert R.recover(sid)["skrevet"] is False


# ── den balancerende hændelse er ikke en besked ──────────────────────────

def test_balancen_bliver_IKKE_til_en_raekke_i_samtalen(sid):
    """Den er til den der læser ledgeren, ikke til den der læser chatten."""
    from core.services import projection_chat_messages as C
    _tur(sid, "user", "assistant", "user")
    R.recover(sid)
    C.register()
    r = C.rebuild(sid)
    assert r["state"]["skrevet"] == 3 and r["state"]["sprunget_over"] == 1
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                      (sid,)).fetchone()[0]
    assert n == 3


def test_en_ny_aaben_tur_efter_en_balance_ses_ogsaa(sid):
    _tur(sid, "user")
    R.recover(sid)
    _tur(sid, "assistant", "user")
    f = R.inspect(sid)
    assert f["ubalanceret"] is True and f["allerede_balanceret"] == 1
