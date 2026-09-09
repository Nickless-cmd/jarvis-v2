"""`SessionHandle` — ejerskab man holder, og formatet som en dom.

Fase 1:
    «read-only interrupted-session inspection writes nothing; recovery appends
     balancing events only under write ownership»
    «current, historical-migratable, future-unsupported, and corrupt formats
     produce distinct verified outcomes while source generations remain
     byte-identical»
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from core.runtime import db_session_ledger as L
from core.runtime import session_handle as H
from core.runtime.db import connect

TID = "2026-09-09T10:00:00+00:00"


@pytest.fixture
def sid(isolated_runtime):
    s = "sh-" + datetime.now(UTC).strftime("%H%M%S%f")
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, TID, TID))
    return s


def _saet_header(sid: str, raa: str):
    with connect() as c:
        H._ensure_header_column(c)
        c.execute("UPDATE chat_sessions SET ledger_header = ? WHERE session_id = ?", (raa, sid))


def _ev(i: str):
    return {"event_id": i, "kind": "message",
            "payload": {"role": "user", "content": i, "created_at": TID}}


# ── headeren er uforanderlig ─────────────────────────────────────────────

def test_headeren_skrives_EN_gang(sid):
    """Kan generationen ændres bagefter, kan en session påstå den er skrevet
    efter regler den ikke er skrevet efter — og så betyder formatet intet."""
    H.write_header(sid)
    with pytest.raises(ValueError, match="uforanderlig"):
        H.write_header(sid)


def test_headeren_kan_laeses_tilbage(sid):
    a = H.write_header(sid)
    b = H.read_header(sid)
    assert b == a and b.generation == H.CURRENT_GENERATION


def test_en_session_uden_header_er_ikke_en_fejl(sid):
    assert H.read_header(sid) is None


def test_header_paa_en_ukendt_session_afvises(isolated_runtime):
    with pytest.raises(ValueError, match="ukendt session"):
        H.write_header("findes-ikke")


# ── fire formater, fire udfald ───────────────────────────────────────────

def test_current(sid):
    H.write_header(sid, generation=H.CURRENT_GENERATION)
    assert H.classify_format(sid) == H.FORMAT_CURRENT


def test_uden_header_er_current(sid):
    """Sessionen er ikke skrevet af ledgeren endnu. Det er ikke en fejl."""
    assert H.classify_format(sid) == H.FORMAT_CURRENT


def test_future(sid):
    _saet_header(sid, json.dumps({"session_id": sid, "generation": 99, "created_at": TID}))
    assert H.classify_format(sid) == H.FORMAT_FUTURE


def test_corrupt(sid):
    _saet_header(sid, "{ ikke json")
    assert H.classify_format(sid) == H.FORMAT_CORRUPT


def test_historical(sid, monkeypatch):
    monkeypatch.setattr(H, "CURRENT_GENERATION", 2)
    monkeypatch.setattr(H, "READABLE_GENERATIONS", (1, 2))
    _saet_header(sid, json.dumps({"session_id": sid, "generation": 1, "created_at": TID}))
    assert H.classify_format(sid) == H.FORMAT_HISTORICAL


def test_de_fire_udfald_er_FORSKELLIGE(sid, isolated_runtime, monkeypatch):
    """Kriteriet er at de kan SKELNES. Fire tilstande der alle giver 'fejl'
    ville betyde at ingen kunne håndtere dem forskelligt."""
    monkeypatch.setattr(H, "CURRENT_GENERATION", 2)
    monkeypatch.setattr(H, "READABLE_GENERATIONS", (1, 2))
    domme = set()
    for g, raa in [("c", json.dumps({"session_id": "x", "generation": 2, "created_at": TID})),
                   ("h", json.dumps({"session_id": "x", "generation": 1, "created_at": TID})),
                   ("f", json.dumps({"session_id": "x", "generation": 9, "created_at": TID})),
                   ("k", "@@@")]:
        s = f"fmt-{g}-" + datetime.now(UTC).strftime("%H%M%S%f")
        with connect() as c:
            c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                      "VALUES (?, 'T', ?, ?)", (s, TID, TID))
        _saet_header(s, raa)
        domme.add(H.classify_format(s))
    assert domme == {H.FORMAT_CURRENT, H.FORMAT_HISTORICAL,
                     H.FORMAT_FUTURE, H.FORMAT_CORRUPT}


@pytest.mark.parametrize("raa,dom", [
    (json.dumps({"session_id": "x", "generation": 99, "created_at": TID}), H.FORMAT_FUTURE),
    ("{ ødelagt", H.FORMAT_CORRUPT),
])
def test_future_og_corrupt_fejler_HOEJT_ved_aabning(sid, raa, dom):
    """En session der åbner sig halvt er værre end en der ikke åbner sig:
    felter vi ikke kender ville forsvinde i stilhed."""
    _saet_header(sid, raa)
    with pytest.raises(H.SessionFormatError) as e1:
        H.open_readonly(sid)
    assert e1.value.verdict == dom
    with pytest.raises(H.SessionFormatError):
        H.open_for_write(sid, owner="a")


def test_en_historisk_session_aabnes_SKRIVEBESKYTTET(sid, monkeypatch):
    """At skrive nyt format ind i en gammel session ville lave en blanding
    ingen af delene kan læse."""
    monkeypatch.setattr(H, "CURRENT_GENERATION", 2)
    monkeypatch.setattr(H, "READABLE_GENERATIONS", (1, 2))
    _saet_header(sid, json.dumps({"session_id": sid, "generation": 1, "created_at": TID}))
    h = H.open_for_write(sid, owner="a")
    assert h.writable is False and h.format == H.FORMAT_HISTORICAL
    with pytest.raises(H.NotWritable):
        h.append(_ev("e1"))


# ── skrivebeskyttet inspektion skriver INTET ─────────────────────────────

def test_open_readonly_efterlader_INGEN_spor(sid):
    """Den hyppigste grund til at kigge på en session er at finde ud af hvad
    der gik galt i den — og det må ikke tage skriveretten fra den der arbejder."""
    def _spor():
        with connect() as c:
            return (list(c.execute("SELECT * FROM session_write_leases WHERE session_id = ?", (sid,))),
                    L.current_seq(sid))
    L.acquire_write_lease(sid, owner="init")  # sørg for at tabellen findes
    with connect() as c:
        c.execute("DELETE FROM session_write_leases WHERE session_id = ?", (sid,))
    foer = _spor()
    with H.open_readonly(sid) as h:
        assert h.writable is False
        h.seq()
    assert _spor() == foer


def test_et_skrivebeskyttet_haandtag_har_ingen_append(sid):
    """Ikke en advarsel — et fravær."""
    with H.open_readonly(sid) as h:
        with pytest.raises(H.NotWritable, match="skrivebeskyttet"):
            h.append(_ev("e1"))


def test_en_anden_der_holder_lease_giver_et_SKRIVEBESKYTTET_haandtag(sid):
    """Aldrig et der lader som om det kan skrive."""
    L.acquire_write_lease(sid, owner="foerste")
    h = H.open_for_write(sid, owner="anden")
    assert h.writable is False
    with pytest.raises(H.NotWritable):
        h.append(_ev("e1"))


# ── kø, flush og lukning ─────────────────────────────────────────────────

def test_intet_roerer_databasen_foer_flush(sid):
    with H.open_for_write(sid, owner="a") as h:
        h.append(_ev("e1"))
        h.append(_ev("e2"))
        assert h.seq() == 0
        assert h.flush() == 2
        assert h.seq() == 2


def test_koeen_skrives_som_EN_batch(sid):
    """Ledgerens append er atomisk pr. batch: en tur der skrev én ad gangen
    kunne efterlade en HALV tur hvis processen døde midtvejs."""
    h = H.open_for_write(sid, owner="a")
    h.append(_ev("e1"))
    h.append({"kind": "message", "payload": {}})   # mangler event_id
    with pytest.raises(ValueError):
        h.flush()
    assert L.current_seq(sid) == 0                # heller ikke den gyldige


def test_close_TIER_IKKE_om_en_koe_den_ikke_kan_skrive(sid):
    """At kaste på lukning er ubelejligt. At droppe hændelser i stilhed er
    værre — det er nøjagtig den fejl der ikke kan opdages bagefter."""
    h = H.open_for_write(sid, owner="a")
    h.append({"kind": "message", "payload": {}})   # kan ikke skrives
    with pytest.raises(ValueError):
        h.close()
    # men leasen er givet fra sig alligevel — ellers ville en fejl paa vej ud
    # spaerre sessionen i fem minutter.
    assert H.open_for_write(sid, owner="b").writable is True


def test_en_fejlet_flush_beholder_koeen(sid):
    """Mister vi lease'n, er hændelserne stadig i hukommelsen og kan skrives
    af den der overtager — frem for at være væk fordi en skrivning fejlede."""
    h = H.open_for_write(sid, owner="a")
    h.append(_ev("e1"))
    h._token = 999                     # stjålet/forældet token
    with pytest.raises(Exception):
        h.flush()
    assert len(h._pending) == 1


def test_close_flusher_og_GIVER_LEASEN_FRA_SIG(sid):
    """Uden det venter næste proces på udløbet af en lease ingen bruger."""
    with H.open_for_write(sid, owner="a") as h:
        h.append(_ev("e1"))
    assert L.current_seq(sid) == 1
    assert H.open_for_write(sid, owner="b").writable is True


def test_close_to_gange_er_harmloest(sid):
    h = H.open_for_write(sid, owner="a")
    h.close()
    h.close()
    assert h.writable is False


def test_et_lukket_haandtag_kan_ikke_skrive(sid):
    h = H.open_for_write(sid, owner="a")
    h.close()
    with pytest.raises(H.NotWritable, match="lukket"):
        h.append(_ev("e1"))


def test_lease_gives_fra_sig_ogsaa_naar_blokken_KASTER(sid):
    with pytest.raises(ValueError):
        with H.open_for_write(sid, owner="a") as h:
            h.append(_ev("e1"))
            raise ValueError("noget gik galt")
    assert H.open_for_write(sid, owner="b").writable is True
