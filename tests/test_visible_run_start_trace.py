"""Start-sporet i `visible_runs` — 12/9-2026.

Baggrund (målt, ikke gættet): `wake-b3eb3b45fc` blev dispatchet 18:45:33 af den
ægte scheduler, og dispatcheren startede sit autonome run 18:45:34. Api'en
genstartede 16 sekunder senere, daemon-tråden døde — og der var INTET spor:
ingen række i `visible_runs`, ingen post i `in_flight_runs`. `dispatched: True`
stod tilbage og sagde «kørt», mens der ikke kom noget svar. Bjørns spørgsmål
«men den fyret ikke i denne session?» kunne kun besvares ved at grave i
event-loggen i hånden.

Årsagen: rækken blev KUN skrevet ved afslutning (`_persist_visible_run_outcome`
kræver `finished_at`). Nu skrives den ved START, og de to steder der allerede ved
at et run blev dræbt stempler den `interrupted`.
"""
from __future__ import annotations

import contextlib
import sqlite3

import pytest

from core.runtime import db_visible
from core.services import session_boot_reconciler as sbr
from core.services import visible_runs_outcomes as vro

_SCHEMA = (
    "CREATE TABLE visible_runs ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "run_id TEXT NOT NULL UNIQUE, lane TEXT, provider TEXT, model TEXT, "
    "status TEXT, started_at TEXT, finished_at TEXT, text_preview TEXT, "
    "error TEXT, capability_id TEXT)",
    # Outcome-stien skriver tre tabeller i ÉT write-lock. Uden dem her fejler
    # `_persist_visible_run_outcome` midtvejs, og testen ville måle en fejl der
    # ikke findes i produktion.
    "CREATE TABLE visible_work_units ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, work_id TEXT NOT NULL UNIQUE, "
    "run_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, lane TEXT NOT NULL, "
    "provider TEXT NOT NULL, model TEXT NOT NULL, started_at TEXT, "
    "finished_at TEXT NOT NULL, user_message_preview TEXT, "
    "capability_id TEXT, work_preview TEXT)",
    "CREATE TABLE visible_work_notes ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT NOT NULL UNIQUE, "
    "work_id TEXT NOT NULL, run_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL, "
    "lane TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, "
    "user_message_preview TEXT, capability_id TEXT, work_preview TEXT, "
    "projection_source TEXT, created_at TEXT NOT NULL, "
    "finished_at TEXT NOT NULL)",
)
_KOLONNER = ("run_id, lane, provider, model, status, started_at, "
             "finished_at, text_preview, error, capability_id")


def _db(tmp_path, rows: list[tuple] = ()) -> str:
    sti = str(tmp_path / "v.db")
    con = sqlite3.connect(sti)
    for _stmt in _SCHEMA:
        con.execute(_stmt)
    con.executemany(
        f"INSERT INTO visible_runs ({_KOLONNER}) VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows)
    con.commit()
    con.close()
    return sti


def _forbind(monkeypatch, modul, sti: str) -> None:
    @contextlib.contextmanager
    def _c():
        con = sqlite3.connect(sti)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()          # runtimeens connect committer ved succes —
        finally:                  # uden dette ruller sqlite skrivningen tilbage
            con.close()
    monkeypatch.setattr(modul, "connect", _c)


class _Run:
    run_id = "autonomous-abc"
    lane = "primary"
    provider = "ollama"
    model = "glm-5.2:cloud"
    user_message = "verificér genstarten"


# ── start-rækken ────────────────────────────────────────────────────────────

def test_start_raekken_skrives_og_taeller_ikke_som_terminal(tmp_path, monkeypatch):
    sti = _db(tmp_path)
    _forbind(monkeypatch, vro, sti)
    vro.persist_visible_run_start(_Run())
    con = sqlite3.connect(sti)
    row = con.execute(
        "SELECT status, finished_at, text_preview FROM visible_runs "
        "WHERE run_id='autonomous-abc'").fetchone()
    con.close()
    assert row[0] == "running"
    assert row[1] == ""          # idiom for «ikke afsluttet» i denne fil
    assert row[2]              # preview findes, ikke NULL
    # Og den skal læses som IKKE-terminal, ellers rydder sweepen en levende tur.
    assert vro.run_er_terminal("autonomous-abc") is False


def test_start_raekken_overskriver_ikke_en_eksisterende(tmp_path, monkeypatch):
    """ON CONFLICT DO NOTHING: et genkald må ikke nulstille started_at."""
    sti = _db(tmp_path, [("autonomous-abc", "primary", "ollama", "m",
                          "running", "2026-09-12T16:45:34", "", "gammel",
                          None, None)])
    _forbind(monkeypatch, vro, sti)
    vro.persist_visible_run_start(_Run())
    con = sqlite3.connect(sti)
    row = con.execute("SELECT started_at, text_preview FROM visible_runs").fetchone()
    con.close()
    assert row[0] == "2026-09-12T16:45:34"
    assert row[1] == "gammel"


# ── stemplet ────────────────────────────────────────────────────────────────

def test_stempel_saetter_interrupted_paa_en_igangvaerende(tmp_path, monkeypatch):
    sti = _db(tmp_path, [("r1", "primary", "p", "m", "running",
                          "2026-09-12T16:45:34", "", "x", None, None)])
    _forbind(monkeypatch, vro, sti)
    assert vro.stamp_visible_run_interrupted("r1", reason="api-nedlukning") is True
    con = sqlite3.connect(sti)
    row = con.execute("SELECT status, finished_at, error FROM visible_runs").fetchone()
    con.close()
    assert row[0] == "interrupted"
    assert row[1]                    # nu afsluttet
    assert row[2] == "api-nedlukning"


def test_stempel_rorer_ALDRIG_en_afsluttet_raekke(tmp_path, monkeypatch):
    """Et rigtigt udfald må ikke kunne overskrives af en sweep der kommer bagefter."""
    sti = _db(tmp_path, [("r1", "primary", "p", "m", "completed",
                          "2026-09-12T16:45:34", "2026-09-12T16:45:40", "svar",
                          None, None)])
    _forbind(monkeypatch, vro, sti)
    assert vro.stamp_visible_run_interrupted("r1", reason="api-nedlukning") is False
    con = sqlite3.connect(sti)
    row = con.execute("SELECT status, text_preview FROM visible_runs").fetchone()
    con.close()
    assert row[0] == "completed"
    assert row[1] == "svar"


def test_stempel_er_self_safe_ved_ingen_sti(tmp_path, monkeypatch):
    _forbind(monkeypatch, vro, str(tmp_path / "findes-ikke" / "umuligt.db"))
    assert vro.stamp_visible_run_interrupted("r1") is False
    assert vro.stamp_visible_run_interrupted("") is False


# ── recent_visible_runs ─────────────────────────────────────────────────────

def test_recent_visible_runs_skjuler_running_som_default(tmp_path, monkeypatch):
    """De 43 kaldere skal se PRÆCIS det samme som før: kun afsluttede ture."""
    sti = _db(tmp_path, [
        ("gammel", "p", "p", "m", "completed", "2026-09-12T10:00:00",
         "2026-09-12T10:00:05", "svar", None, None),
        ("igang", "p", "p", "m", "running", "2026-09-12T16:45:34", "", "x", None, None),
    ])
    _forbind(monkeypatch, db_visible, sti)
    ids = [r["run_id"] for r in db_visible.recent_visible_runs(limit=5)]
    assert ids == ["gammel"]


def test_recent_visible_runs_kan_tilvaelge_running(tmp_path, monkeypatch):
    sti = _db(tmp_path, [
        ("igang", "p", "p", "m", "running", "2026-09-12T16:45:34", "", "x", None, None),
    ])
    _forbind(monkeypatch, db_visible, sti)
    ids = [r["run_id"] for r in db_visible.recent_visible_runs(
        limit=5, include_running=True)]
    assert ids == ["igang"]


# ── boot-reconcileren ───────────────────────────────────────────────────────

def test_boot_reconciler_stempler_baade_post_og_raekke(tmp_path, monkeypatch):
    sti = _db(tmp_path, [("zombie-1", "p", "p", "m", "running",
                          "2026-09-12T10:00:00", "", "x", None, None)])
    _forbind(monkeypatch, vro, sti)

    stemplet: list[tuple] = []
    monkeypatch.setattr(
        sbr.in_flight_runs, "list_running_orphans",
        lambda stale_after_s: [{"run_id": "zombie-1", "kind": "autonomous"}])
    monkeypatch.setattr(
        sbr.in_flight_runs, "mark_interrupted",
        lambda rid, reason="": stemplet.append(("post", rid)))

    import core.services.session_persistence_flag as spf
    monkeypatch.setattr(spf, "session_persistence_enabled", lambda: True)

    summary = sbr.reconcile_on_boot()
    assert summary["enforced"] is True
    assert stemplet == [("post", "zombie-1")]

    con = sqlite3.connect(sti)
    row = con.execute("SELECT status FROM visible_runs").fetchone()
    con.close()
    assert row[0] == "interrupted", "rækken skal spejle stemplet"


def test_boot_reconciler_shadow_skriver_INTET(tmp_path, monkeypatch):
    """Kill-switch OFF = observe-only. Så må hverken post eller række røres."""
    sti = _db(tmp_path, [("zombie-1", "p", "p", "m", "running",
                          "2026-09-12T10:00:00", "", "x", None, None)])
    _forbind(monkeypatch, vro, sti)
    monkeypatch.setattr(
        sbr.in_flight_runs, "list_running_orphans",
        lambda stale_after_s: [{"run_id": "zombie-1", "kind": "autonomous"}])
    monkeypatch.setattr(
        sbr.in_flight_runs, "mark_interrupted",
        lambda rid, reason="": pytest.fail("shadow må ikke skrive"))

    import core.services.session_persistence_flag as spf
    monkeypatch.setattr(spf, "session_persistence_enabled", lambda: False)

    sbr.reconcile_on_boot()
    con = sqlite3.connect(sti)
    row = con.execute("SELECT status FROM visible_runs").fetchone()
    con.close()
    assert row[0] == "running", "shadow må ikke stemple rækken"


# ── kildetjek: rækkefølgen ER pointen ───────────────────────────────────────

def test_autonom_vej_skriver_sporet_FOER_traaden():
    """Tråden kan dø midt i turen. Skrives sporet inde i tråden, er det væk."""
    src = open("core/services/autonomous_stream_run.py", encoding="utf-8").read()
    i_spor = src.index('kind="autonomous"')
    i_traad = src.index("threading.Thread(")
    assert i_spor < i_traad, "sporet skal skrives før tråden starter"
    assert "persist_visible_run_start" in src
    assert "begin_follow" in src  # kæden er ellers uændret


def test_nedluknings_sweepen_stempler_ogsaa_raekken():
    src = open("apps/api/jarvis_api/app.py", encoding="utf-8").read()
    i = src.index("list_running_orphans(0.0)")
    vindue = src[i:i + 2200]
    # KALDET, ikke bare navnet: import-linjen står der uanset, så et navnetjek
    # bestod selv da kaldet var fjernet. (Mutationstest 12/9-2026.)
    assert "stamp_visible_run_interrupted(_rid" in vindue
    # Og det skal komme EFTER terminal-spørgsmålet, ellers stemples en
    # afsluttet tur.
    assert vindue.index("run_er_terminal") < vindue.index(
        "stamp_visible_run_interrupted(_rid")


def test_visible_runs_laeser_kind_igennem():
    """Uden kind stod ALLE in-flight-poster som `visible` — også autonome."""
    src = open("core/services/visible_runs.py", encoding="utf-8").read()
    i = src.index("_mark_run_started(")
    vindue = src[i:i + 700]
    assert 'kind="autonomous"' in vindue
    assert "provider=run.provider" in vindue


# ── den synlige vej (lukket 12/9-2026) ──────────────────────────────────────

class _SynligRun:
    run_id = "visible-synlig-1"
    lane = "primary"
    provider = "deepseek"
    model = "deepseek-v4-flash"
    user_message = "hej fra en synlig tur"
    session_id = "chat-synlig"
    trust_all = False


def _register_uden_state(monkeypatch):
    """`register_visible_run` skriver også kontrol-tilstand til `runtime_state`.
    Den del er ikke under test her — vi vil kun se på `visible_runs`-rækken."""
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "_set_visible_run_control", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_set_active_visible_run", lambda *a, **k: None)
    return vr


def test_synlig_vej_skriver_start_raekken(tmp_path, monkeypatch):
    """Den synlige vej skrev KUN en række ved afslutning — nu også ved START.

    Uden dette var `stamp_visible_run_interrupted` en no-op for alle synlige
    runs: der var ingen `running`-række at stemple.
    """
    sti = _db(tmp_path)
    _forbind(monkeypatch, vro, sti)
    vr = _register_uden_state(monkeypatch)
    vr.register_visible_run(_SynligRun())
    con = sqlite3.connect(sti)
    row = con.execute(
        "SELECT status, finished_at, text_preview FROM visible_runs "
        "WHERE run_id='visible-synlig-1'").fetchone()
    con.close()
    assert row is not None, "en synlig tur skal efterlade en start-række"
    assert row[0] == "running"
    assert row[1] == ""
    assert row[2]


def test_synlig_vej_kalder_start_sporet_i_register():
    """KALDET skal stå i `register_visible_run` — ikke bare navnet i importen."""
    src = open("core/services/visible_runs.py", encoding="utf-8").read()
    i = src.index("def register_visible_run(")
    j = src.index("\ndef ", i + 10)
    krop = src[i:j]
    assert "persist_visible_run_start(run)" in krop, \
        "den synlige vej skal skrive start-sporet i register_visible_run"
    assert "persist_visible_run_start" in src, "navnet skal være importeret"


def test_outcome_overskriver_start_raekken(tmp_path, monkeypatch):
    """Ved normal afslutning skal outcome-rækken ERSTATTE running-rækken.

    Ellers ville en færdig synlig tur stå `running` for evigt — værre end at
    mangle rækken. (ON CONFLICT DO UPDATE i `_persist_visible_run_outcome`.)
    """
    sti = _db(tmp_path)
    _forbind(monkeypatch, vro, sti)
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "get_visible_run_controller", lambda rid: None)
    monkeypatch.setattr(vr, "_get_visible_run_control", lambda rid: {})
    monkeypatch.setattr(vro, "write_private_terminal_layers", lambda **k: None)
    run = _SynligRun()
    vro.persist_visible_run_start(run)
    vro._persist_visible_run_outcome(
        run, status="completed",
        finished_at="2026-09-12T19:00:05+00:00",
        text_preview="her er svaret")
    con = sqlite3.connect(sti)
    row = con.execute(
        "SELECT status, finished_at, text_preview FROM visible_runs "
        "WHERE run_id='visible-synlig-1'").fetchone()
    con.close()
    assert row[0] == "completed", "outcome skal overskrive running-rækken"
    assert row[1] == "2026-09-12T19:00:05+00:00"
    assert row[2] == "her er svaret"
