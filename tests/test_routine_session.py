"""Rutinens samtale — sessionen der gør en baggrundskørsel læsbar.

Målt 15/11-2026: 190 rutine-kørsler, nul med en session. Resultatet lå kun i
``routine_runs.result``, så rutinefladen var blind for hvad der var sket — og der
fandtes intet sted at svare rutinen.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services import routine_session as rs


def _beskeder(session_id: str) -> list[tuple[str, str, str]]:
    from core.runtime.db_core import connect

    with connect() as conn:
        rows = conn.execute(
            "SELECT message_id, role, content FROM chat_messages "
            "WHERE session_id=? ORDER BY created_at, rowid",
            (session_id,),
        ).fetchall()
    return [(str(r[0]), str(r[1]), str(r[2])) for r in rows]


def test_session_id_er_deterministisk():
    assert rs.routine_session_id("abc") == "routine-abc"
    assert rs.routine_session_id("abc") == rs.routine_session_id("abc")
    assert rs.routine_session_id("") == "routine-"


@pytest.mark.parametrize(
    "routine_id,config,forventet",
    [
        ("x", {"producer": "heartbeat"}, "heartbeat"),
        ("x", {"producer": "Dream"}, "dream"),
        # De tre system-rutiner blev oprettet FØR `producer` fandtes — id'et bærer
        # oprindelsen, og uden fallback ville de pege på en tom session.
        ("routine_system_heartbeat", None, "heartbeat"),
        ("routine_system_dream", {}, "dream"),
        ("routine_system_wakeup", {}, "wakeup"),
        ("routine_migrated_abc", {"producer": ""}, ""),
        ("routine_migrated_abc", None, ""),
    ],
)
def test_origin_for_routine(routine_id, config, forventet):
    assert rs.origin_for_routine(routine_id, config) == forventet


def test_en_koersel_skrives_som_opgave_og_svar(isolated_runtime):
    sid = rs.ensure_routine_session("r1", title="Morgenbrief")
    assert rs.append_run(sid, run_id="run1", instruction="Kig på vejret", result="Det regner.") is True

    rows = _beskeder(sid)
    assert [r[1] for r in rows] == ["user", "assistant"]
    assert rows[0][2] == "Kig på vejret"
    assert rows[1][2] == "Det regner."


def test_samme_koersel_skrives_kun_en_gang(isolated_runtime):
    """En genoptaget kørsel (lease-tab) må ikke give to svar i transcripten."""
    sid = rs.ensure_routine_session("r2", title="Nat")
    assert rs.append_run(sid, run_id="run2", instruction="Opgave", result="Svar") is True
    assert rs.append_run(sid, run_id="run2", instruction="Opgave", result="Svar") is False
    assert len(_beskeder(sid)) == 2


def test_tomt_svar_bliver_stadig_en_raekke(isolated_runtime):
    """En kørsel der ikke gav tekst skal ikke forsvinde — den skal SES."""
    sid = rs.ensure_routine_session("r3", title="Tom")
    assert rs.append_run(sid, run_id="run3", instruction="Opgave", result="   ") is True
    rows = _beskeder(sid)
    assert rows[-1][2] == "(kørslen gav intet svar)"


def test_backfill_skriver_de_seneste_koersler_i_raekkefoelge(isolated_runtime):
    sid = rs.ensure_routine_session("r4", title="Historik")
    runs = [
        {"run_id": "g1", "result": "første", "created_at": "2026-11-01T05:00:00+00:00"},
        {"run_id": "g2", "result": b"anden", "created_at": "2026-11-02T05:00:00+00:00"},
    ]
    assert rs.backfill(sid, runs, instruction="Rutinens opgave") == 2
    rows = _beskeder(sid)
    # bytes afkodes (resultatet gemmes som bytes i `routine_runs`)
    assert [r[2] for r in rows] == [
        "Rutinens opgave", "første", "Rutinens opgave", "anden",
    ]
    # …og den er idempotent: samme historik to gange giver ikke fire kørsler mere.
    assert rs.backfill(sid, runs, instruction="Rutinens opgave") == 0
    assert len(_beskeder(sid)) == 4


def test_tom_koerselsliste_roerer_intet(isolated_runtime):
    sid = rs.ensure_routine_session("r5", title="Ingen")
    assert rs.backfill(sid, []) == 0
    assert rs.backfill(sid, None) == 0
    assert _beskeder(sid) == []
