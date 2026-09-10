"""Runde-kaeden skal pege paa SIN EGEN event — Fase 10.

Telemetri maa registrere arbejde, ikke forveksle det. Opslaget hentede foer
«nyeste event af sin slags», og BEGGE units koerer samme app — saa en samtidig
runde i den anden proces kunne blive kaedens foraelder.

MAALT i produktion foer rettelsen: 240 af 5.457
`runtime.agentic_round_start`-events (4,4 %) har en soeskende inden for ét
sekund. Cirka hver tyvende runde kunne altsaa kaede sig til en fremmed koersel.

Testen rammer det der blev aendret — FORESPOERGSLEN — med en haandlavet
events-tabel. At gaa gennem event-bussen ville maale bussens bootstrap, ikke
udvaelgelsen.
"""
from __future__ import annotations

import sqlite3


def _db(tmp_path):
    sti = tmp_path / "e.db"
    conn = sqlite3.connect(str(sti))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "kind TEXT, payload_json TEXT, created_at TEXT)")
    conn.commit()
    return sti, conn


def _laeg(conn, run_id, runde):
    import json
    conn.execute("INSERT INTO events (kind, payload_json, created_at) "
                 "VALUES (?, ?, datetime('now'))",
                 ("runtime.agentic_round_start",
                  json.dumps({"run_id": run_id, "round": runde})))
    conn.commit()
    return int(conn.execute("SELECT last_insert_rowid() i").fetchone()["i"])


def test_vaelger_sin_egen_og_ikke_naboens(tmp_path, monkeypatch):
    import contextlib

    import core.services.visible_runs as vr

    sti, conn = _db(tmp_path)
    min_id = _laeg(conn, "visible-MIN", 3)
    _laeg(conn, "visible-FREMMED", 1)          # naboprocessens runde, NYERE

    @contextlib.contextmanager
    def _forbind():
        c = sqlite3.connect(str(sti))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    monkeypatch.setattr("core.runtime.db.connect", _forbind)
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish",
                        lambda *a, **kw: None)

    fik = vr._publish_agentic_round_start(run_id="visible-MIN", round_num=3)
    assert fik == min_id, (
        "kaeden pegede paa den NYESTE event af sin slags — altsaa en fremmed "
        "koersels runde")


def test_samme_run_forskellige_runder_forveksles_ikke(tmp_path, monkeypatch):
    import contextlib

    import core.services.visible_runs as vr

    sti, conn = _db(tmp_path)
    runde1 = _laeg(conn, "visible-X", 1)
    _laeg(conn, "visible-X", 2)

    @contextlib.contextmanager
    def _forbind():
        c = sqlite3.connect(str(sti))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    monkeypatch.setattr("core.runtime.db.connect", _forbind)
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda *a, **kw: None)

    assert vr._publish_agentic_round_start(run_id="visible-X", round_num=1) == runde1


def test_falder_tilbage_naar_nyttelasten_ikke_kan_laeses(tmp_path, monkeypatch):
    """Aeldre raekker uden brugbar payload maa ikke tabe kaeden helt — da er
    den gamle adfaerd bedre end ingenting."""
    import contextlib

    import core.services.visible_runs as vr

    sti, conn = _db(tmp_path)
    conn.execute("INSERT INTO events (kind, payload_json, created_at) "
                 "VALUES (?, ?, datetime('now'))",
                 ("runtime.agentic_round_start", "ikke-json"))
    conn.commit()
    gammel = int(conn.execute("SELECT last_insert_rowid() i").fetchone()["i"])

    @contextlib.contextmanager
    def _forbind():
        c = sqlite3.connect(str(sti))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    monkeypatch.setattr("core.runtime.db.connect", _forbind)
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda *a, **kw: None)

    assert vr._publish_agentic_round_start(run_id="visible-Y", round_num=1) == gammel
