"""Aktive parallelle runs — sektionen der fortæller mig hvor jeg er.

BAGGRUND (målt 28/10-2026). `cross_session_arc` giver FORTIDEN, men intet gav
NUTIDEN. Kl. 17:31 skrev Jarvis «skal jeg skrive til ham?» om en agent der
lukkede side-opgaver — men «ham» var Jarvis selv i en code-session der kørte
samtidig. Brugeren måtte spørge «hvem er ham?» to gange.

TESTENE VÆRNER TRE TING, og den tredje er den vigtigste:

1. Ingen støj når der ikke kører noget (`None`, ikke "" og ikke «0 runs»).
2. Egen session nævnes ikke — jeg ved godt at jeg kører.
3. `active`-flaget alene er ALDRIG nok. Et flag uden `visible_runs.status =
   'running'` er en lækage og må ikke nævnes som aktiv. Målt: et flag fra
   27/10 kl. 20:47 stod stadig `active: true` 1241 minutter senere.

MODPRØVE: `test_aktiv_run_i_egen_session_naevnes_ikke` fejler hvis nogen
fjerner ekskluderingen af egen session. Det er verificeret ved at fjerne den
med vilje og se testen fejle — en grøn test der ikke kan fejle værner intet.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from core.services.prompt_sections import active_runs

EGEN = "chat-egen0000000000000000000000000000"
ANDEN = "chat-anden000000000000000000000000000"


def _nu_minus(minutter: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter)).isoformat()


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Ægte SQLite i en tmp-fil — ikke en mock der svarer det samme uanset SQL."""
    sti = tmp_path / "aktiv.db"
    conn = sqlite3.connect(sti)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE runtime_state_kv (key TEXT PRIMARY KEY, "
        "value_json TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE visible_runs (run_id TEXT PRIMARY KEY, status TEXT, "
        "started_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE chat_sessions (session_id TEXT PRIMARY KEY, title TEXT, "
        "updated_at TEXT)"
    )
    conn.commit()

    @contextmanager
    def _connect():
        yield conn

    # Patchet på forbrugsstedet: modulet har `from core.runtime.db import
    # connect`, så det er HER navnet faktisk slås op.
    monkeypatch.setattr(active_runs, "connect", _connect)
    return conn


def _session(conn, sid: str, titel: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO chat_sessions (session_id, title, updated_at) "
        "VALUES (?,?,?)",
        (sid, titel, _nu_minus(0)),
    )
    conn.commit()


def _run(
    conn,
    run_id: str,
    session_id: str,
    *,
    active: bool = True,
    status: str = "running",
    alder_min: float = 1.0,
    lane: str = "primary",
) -> None:
    start = _nu_minus(alder_min)
    payload = {
        "active": active,
        "run_id": run_id,
        "session_id": session_id,
        "lane": lane,
        "started_at": start,
    }
    conn.execute(
        "INSERT OR REPLACE INTO runtime_state_kv (key, value_json, updated_at) "
        "VALUES (?,?,?)",
        (f"visible_runs.control.{run_id}", json.dumps(payload), start),
    )
    conn.execute(
        "INSERT OR REPLACE INTO visible_runs (run_id, status, started_at) "
        "VALUES (?,?,?)",
        (run_id, status, start),
    )
    conn.commit()


# ── 1. Ingen støj når der ikke kører noget ────────────────────────────────


def test_ingen_aktive_runs_giver_none(base) -> None:
    """`None` — ikke "" og ikke «0 runs». En sektion der altid er der bliver
    støj jeg lærer at springe over."""
    _session(base, EGEN, "min egen")
    assert active_runs.active_runs_section(EGEN) is None


def test_uden_session_id_giver_none(base) -> None:
    """Uden at vide hvor jeg er, kan jeg ikke sige hvad der er «andre»."""
    _session(base, ANDEN, "en anden")
    _run(base, "visible-aaa", ANDEN)
    assert active_runs.active_runs_section(None) is None
    assert active_runs.active_runs_section("") is None


def test_prewarm_er_ikke_en_session(base) -> None:
    _session(base, ANDEN, "en anden")
    _run(base, "visible-aaa", ANDEN)
    assert active_runs.active_runs_section("__prewarm__") is None


# ── 2. En anden session nævnes; min egen gør ikke ─────────────────────────


def test_aktiv_run_i_anden_session_naevnes(base) -> None:
    _session(base, ANDEN, "code-session om noget")
    _run(base, "visible-aaa", ANDEN, alder_min=7)
    tekst = active_runs.active_runs_section(EGEN)
    assert tekst is not None
    assert "code-session om noget" in tekst
    assert "primary" in tekst
    assert "7 min" in tekst


def test_aktiv_run_i_egen_session_naevnes_ikke(base) -> None:
    """MODPRØVE. Fejler hvis ekskluderingen af egen session fjernes."""
    _session(base, EGEN, "min egen")
    _run(base, "visible-mig", EGEN)
    assert active_runs.active_runs_section(EGEN) is None


def test_begge_sessioner_aktive_naevner_kun_den_anden(base) -> None:
    _session(base, EGEN, "min egen")
    _session(base, ANDEN, "den anden")
    _run(base, "visible-mig", EGEN)
    _run(base, "visible-anden", ANDEN)
    tekst = active_runs.active_runs_section(EGEN)
    assert tekst is not None
    assert "den anden" in tekst
    assert "min egen" not in tekst


# ── 3. Flaget alene er aldrig nok ─────────────────────────────────────────


def test_gammelt_flag_uden_running_status_naevnes_ikke(base) -> None:
    """LÆKAGEN. Målt 28/10-2026: `active: true` fra 27/10 kl. 20:47 — 1241
    minutter gammelt — på et run der for længst var væk. Det er ikke et run,
    det er et levn."""
    _session(base, ANDEN, "forladt session")
    _run(base, "visible-laekage", ANDEN, status="completed", alder_min=1241)
    assert active_runs.active_runs_section(EGEN) is None


def test_active_false_naevnes_ikke(base) -> None:
    _session(base, ANDEN, "afsluttet")
    _run(base, "visible-faerdig", ANDEN, active=False)
    assert active_runs.active_runs_section(EGEN) is None


def test_for_gammelt_men_running_naevnes_ikke(base) -> None:
    """Over agent-loopets eget budget (4 timer) = sandsynligvis hængt, ikke «nu»."""
    _session(base, ANDEN, "hængt")
    _run(base, "visible-haengt", ANDEN, alder_min=300)
    assert active_runs.active_runs_section(EGEN) is None


def test_frisk_running_inden_for_budget_naevnes(base) -> None:
    """Modstykket: et legitimt langt autonomt run må ikke skjules."""
    _session(base, ANDEN, "langt autonomt run")
    _run(base, "visible-langt", ANDEN, alder_min=200)
    tekst = active_runs.active_runs_section(EGEN)
    assert tekst is not None
    assert "langt autonomt run" in tekst


# ── 4. Loftet ─────────────────────────────────────────────────────────────


def test_hoejst_tre_runs_vises(base) -> None:
    for i in range(5):
        sid = f"chat-x{i}"
        _session(base, sid, f"session {i}")
        _run(base, f"visible-{i}", sid, alder_min=float(i + 1))
    tekst = active_runs.active_runs_section(EGEN)
    assert tekst is not None
    assert "Andre sessioner kører nu (5)" in tekst
    assert tekst.count("\n- «") == 3
    assert "…og 2 mere" in tekst


def test_lang_titel_klippes(base) -> None:
    _session(base, ANDEN, "x" * 200)
    _run(base, "visible-lang", ANDEN)
    tekst = active_runs.active_runs_section(EGEN)
    assert tekst is not None
    assert "…" in tekst
    assert len(tekst) <= active_runs._MAX_CHARS


# ── 5. Self-safe ──────────────────────────────────────────────────────────


def test_kaster_ikke_naar_basen_svigter(monkeypatch) -> None:
    def _boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr(active_runs, "connect", _boom)
    assert active_runs.active_runs_section(EGEN) is None


def test_ugyldig_value_json_springes_over(base) -> None:
    base.execute(
        "INSERT INTO runtime_state_kv (key, value_json, updated_at) VALUES (?,?,?)",
        ("visible_runs.control.visible-skb", "ikke json", _nu_minus(1)),
    )
    base.commit()
    assert active_runs.active_runs_section(EGEN) is None
