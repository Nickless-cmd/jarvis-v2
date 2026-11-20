"""Tests for curriculum-kadencen — materialisering uden om action-vaelgeren.

Maalt 20/11-2026: `generate_curriculum` blev aldrig valgt som action (nul
raekker i heartbeat_runtime_ticks), saa materialiseringen var doed kode og
confidence_by_domain stod fast paa 0,32.
"""
from __future__ import annotations


def test_hjerteslaget_kalder_curriculum_kadencen():
    """Tik-funktionen skal kalde kadencen — uanset hvilken action der vaelges.

    Maalt 20/11-2026: `generate_curriculum` blev aldrig valgt som action, saa
    materialiseringen var doed kode. Denne test beviser WIRING: kaldet staar i
    `_run_heartbeat_tick_locked` selv, ikke i en action-gren.

    Den parses frem for at koere tikket: et fuldt tik kalder LLM-providers, og
    husets test-vagt standser netadgang — det ville maale nettet, ikke wiringen.
    """
    import ast
    import inspect
    import textwrap

    import core.services.heartbeat_runtime as hr

    kilde = textwrap.dedent(inspect.getsource(hr._run_heartbeat_tick_locked))
    trae = ast.parse(kilde)
    kald = [
        n
        for n in ast.walk(trae)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "tick_curriculum_cadence"
    ]
    assert kald, "tik-funktionen kalder ikke curriculum-kadencen"


def test_kadencen_fyrer_paa_tid_ikke_paa_tik(tmp_path, monkeypatch):
    """Gaten maaler TID siden sidste materialisering — ikke et tik-tal.

    Et tik tager ~8,2 min (maalt), og `_HEARTBEAT_TICK_COUNTER` nulstilles ved
    genstart. En tik-baseret gate naar derfor aldrig sin graense i drift.
    """
    import sqlite3 as _sql
    from datetime import UTC, datetime, timedelta

    from core.services import heartbeat_curriculum_cadence as cad
    from core.services import self_experiments as se

    db = tmp_path / "kadence.db"
    with _sql.connect(db) as conn:
        conn.execute(
            "CREATE TABLE runtime_tasks (id TEXT, origin TEXT, created_at TEXT)"
        )

    kald: list[dict] = []
    monkeypatch.setattr(
        se,
        "materialize_learning_curriculum_tasks",
        lambda **kw: kald.append(kw) or {"created": 1, "task_ids": ["x"]},
    )

    t0 = datetime(2026, 11, 20, 4, 0, tzinfo=UTC)

    # 1) Ingen tidligere koersel -> fyrer.
    assert cad.tick_curriculum_cadence(now=t0, db_path=str(db)) is not None
    assert len(kald) == 1

    # 2) Netop materialiseret -> fyrer IKKE, heller ikke efter 30 min.
    with _sql.connect(db) as conn:
        conn.execute(
            "INSERT INTO runtime_tasks VALUES ('a','heartbeat:curriculum-cadence',?)",
            (t0.isoformat(),),
        )
    assert cad.tick_curriculum_cadence(now=t0 + timedelta(minutes=30), db_path=str(db)) is None
    assert len(kald) == 1

    # 3) Over intervallet -> fyrer igen.
    assert cad.tick_curriculum_cadence(now=t0 + timedelta(minutes=61), db_path=str(db)) is not None
    assert len(kald) == 2
