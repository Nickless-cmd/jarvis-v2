"""Dispatcher-adoption: koblingen mellem en hentning og det senere kald (14/11-2026).

Baggrunden er en målefejl, ikke en manglende funktion. `scripts/dispatcher_adoption.py`
har kunnet læse sporet hele tiden, men delte dispatcher-kald med antal hentede
navne over hele vinduet: 230 / 614 = «37 %». Det er ikke en rate. `db_query`
stod med 87 kald mod 37 hentninger — 235 % for ét navn, hvilket en rate ikke kan
være. Raten skal regnes PR. RUN, og det kræver run-id på BEGGE sider.

Disse vagter holder tre ting fast:

1. hentningen bærer `run_id` — på eventet OG i tabellen;
2. et ukendt run gemmes som TOMT, ikke som ``UKENDT``. En join-nøgle der hedder
   «UKENDT» ville smelte alle ukendte runs sammen til ét fiktivt run og opfinde
   en adoption der ikke findes;
3. scriptet regner run-dækning, og en hentning uden run-id tælles som ukobbelig
   — hverken for eller imod.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from core.tools import load_more_tools as lmt


class _FakeConn:
    """Nok af sqlite-forbindelsen til at se hvad der bliver skrevet."""

    def __init__(self) -> None:
        self.kald: list[tuple[str, tuple]] = []
        self.committed = False

    def execute(self, sql: str, params: tuple) -> None:
        self.kald.append((sql, params))

    def commit(self) -> None:
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture()
def opsamling(monkeypatch):
    """Fanger eventet og INSERT'en uden at røre den levende base."""
    events: list[tuple[str, dict]] = []
    conn = _FakeConn()

    import core.eventbus.bus as bus_mod
    import core.runtime.db as db_mod

    monkeypatch.setattr(
        bus_mod.event_bus, "publish",
        lambda kind, payload: events.append((kind, payload)),
    )
    monkeypatch.setattr(db_mod, "connect", lambda: conn)
    return events, conn


def _hent(run_id: str | None, navne: list[str] | None = None) -> dict:
    """Kald hentningen med et givet run-id — eller uden noget som helst."""
    args: dict = {"names": navne or ["db_query"]}
    if run_id is not None:
        args["_runtime_turn_id"] = run_id
        # Uden dette slaar `identitet` op i den levende base for at finde ejeren.
        args["_runtime_user_id"] = "test-bruger"
    return lmt._tool_load_more_tools(args)


def test_hentningen_baerer_run_id_paa_eventet(opsamling) -> None:
    """Uden run-id paa hentesiden kan «hentede dette run et vaerktoej?» ikke besvares."""
    events, _ = opsamling
    _hent("run-abc")

    hændelser = [p for k, p in events if k == "tool_router.load_more_fired"]
    assert hændelser, "hentningen udgav intet spor — saa er der intet at maale"
    assert hændelser[-1].get("run_id") == "run-abc", (
        f"run_id landede som {hændelser[-1].get('run_id')!r} — koblingen til "
        "dispatcher_brugt kan ikke laves"
    )


def test_hentningen_baerer_run_id_i_tabellen(opsamling) -> None:
    """Tabellen er den anden læser; en kolonne der ikke fyldes er en tom kolonne."""
    _, conn = opsamling
    _hent("run-tabel")

    inserts = [(s, p) for s, p in conn.kald if "INSERT INTO tool_router_load_more" in s]
    assert inserts, "der blev ikke skrevet en raekke"
    sql, params = inserts[-1]
    assert "run_id" in sql, "kolonnen er ikke med i INSERT'en"
    assert params[0] == "run-tabel", f"foerste parameter var {params[0]!r}"
    assert conn.committed


def test_ukendt_run_gemmes_som_tomt_ikke_UKENDT(opsamling, monkeypatch) -> None:
    """Et ukendt run maa ikke blive en join-noegle.

    ``UKENDT`` som vaerdi ville laegge ALLE hentninger uden run-id i samme
    fiktive run — og et saadant run ville se ud som om det hentede alt og
    kaldte intet, eller omvendt. Hullet skal kunne ses, ikke fyldes.
    """
    events, conn = opsamling
    # Ingen run-id i argumenterne; konteksten ryddes saa reservevejen ogsaa er tom.
    import core.tools.tool_call_telemetry as tct

    monkeypatch.setattr(
        tct, "identitet",
        lambda a: {"user_id": "u", "session_id": "s", "run_id": tct.UKENDT},
    )
    _hent(None)

    hændelser = [p for k, p in events if k == "tool_router.load_more_fired"]
    assert hændelser[-1].get("run_id") == "", (
        "et ukendt run blev skrevet som "
        f"{hændelser[-1].get('run_id')!r} — det smelter ukendte runs sammen"
    )
    sql, params = [x for x in conn.kald if "INSERT INTO tool_router_load_more" in x[0]][-1]
    assert params[0] == "", f"tabellen fik {params[0]!r}"


def _bygg_db(sti: Path) -> None:
    con = sqlite3.connect(sti)
    con.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, created_at TEXT, "
        "payload_json TEXT)"
    )
    rækker = [
        # run-1: hentede db_query, kaldte den via dispatcheren  -> adopteret
        ("tool_router.load_more_fired", "2026-11-14T10:00:00", {"resolved_names": ["db_query"], "run_id": "run-1"}),
        ("tool_router.dispatcher_brugt", "2026-11-14T10:00:05", {"vaerktoej": "db_query", "run_id": "run-1"}),
        # run-2: hentede to navne, kaldte et ANDET vaerktoej     -> ikke adopteret
        ("tool_router.load_more_fired", "2026-11-14T11:00:00", {"resolved_names": ["bash", "web_search"], "run_id": "run-2"}),
        ("tool_router.dispatcher_brugt", "2026-11-14T11:00:05", {"vaerktoej": "read_file", "run_id": "run-2"}),
        # run-3: hentet FOER run_id kom paa hentesiden            -> ukobbelig
        ("tool_router.load_more_fired", "2026-11-13T09:00:00", {"resolved_names": ["get_weather"], "run_id": ""}),
    ]
    con.executemany(
        "INSERT INTO events(kind, created_at, payload_json) VALUES (?,?,?)",
        [(k, t, json.dumps(p)) for k, t, p in rækker],
    )
    con.commit()
    con.close()


def test_scriptet_regner_run_daekning(tmp_path: Path) -> None:
    """1 af 2 kobbelige runs kaldte et hentet navn — og den ukobbelige taeller ikke med."""
    db = tmp_path / "adoption.db"
    _bygg_db(db)

    ud = subprocess.run(
        [sys.executable, "scripts/dispatcher_adoption.py",
         "--siden", "2026-11-01T00:00:00", "--db", str(db)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=60,
    )
    assert ud.returncode == 0, ud.stderr
    tekst = ud.stdout

    assert "kobbelige runs (havde run_id):    2" in tekst, tekst
    assert "ukobbelige hentninger:            1" in tekst, tekst
    assert "50 %" in tekst, f"run-dækningen blev ikke 50 %:\n{tekst}"
    assert "1 af 2 hentende runs" in tekst, tekst
    # Kaldet i run-2 gik til et navn run-2 IKKE hentede — det maa ikke taelle.
    assert "read_file" not in tekst.split("hentede navne")[1].split("hentet men")[0], (
        "et kald til et ikke-hentet navn blev talt som adoption"
    )
