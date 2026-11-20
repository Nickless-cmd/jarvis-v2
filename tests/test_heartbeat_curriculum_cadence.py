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

    import core.runtime.db_core as db_core

    db = tmp_path / "kadence.db"
    monkeypatch.setattr(db_core, "DB_PATH", db)  # db_path skal matche db_core
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


# ---------------------------------------------------------------------------
# side-58f35cc7cf — `db_path` maa aldrig styre kun LAESNINGEN.
# ---------------------------------------------------------------------------


def _to_baser(tmp_path, monkeypatch):
    """To skema-komplette baser: `aktiv` er den db_core peger paa, `fremmed`
    er den kalderen angiver som `db_path`. Curriculum-planen er stubbet til
    ét item, saa kun skrive-stien afproeves."""
    import core.runtime.db_core as db_core
    from core.runtime.db_schema import init_db
    from core.services import self_experiments as se

    aktiv = tmp_path / "aktiv.db"
    fremmed = tmp_path / "fremmed.db"
    for sti in (aktiv, fremmed):
        monkeypatch.setattr(db_core, "DB_PATH", sti)
        init_db()
    monkeypatch.setattr(db_core, "DB_PATH", aktiv)
    monkeypatch.setattr(
        se,
        "generate_learning_curriculum",
        lambda: {
            "candidates": [
                {"focus": "f", "suggestion": "s", "priority": 0.5, "domain": "testdomaene-x"}
            ]
        },
    )
    return aktiv, fremmed


def _antal_curriculum_tasks(sti) -> int:
    import sqlite3 as _sql

    with _sql.connect(f"file:{sti}?mode=ro", uri=True) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM runtime_tasks WHERE origin='heartbeat:curriculum-cadence'"
        ).fetchone()[0]


def test_eksplicit_db_path_skriver_aldrig_i_en_anden_base(tmp_path, monkeypatch):
    """Maalt 20/11-2026 04:24Z: et kald med teststi skrev tre tasks i den
    levende base. Nu: db_path != db_core's base -> afvist, intet skrevet."""
    from datetime import UTC, datetime

    from core.services import heartbeat_curriculum_cadence as cad

    aktiv, fremmed = _to_baser(tmp_path, monkeypatch)
    res = cad.tick_curriculum_cadence(
        now=datetime(2026, 11, 20, 4, 0, tzinfo=UTC), db_path=str(fremmed)
    )
    assert res is not None and res.get("refused") == "db_path_mismatch"
    assert _antal_curriculum_tasks(aktiv) == 0, "skrev i db_core's base trods anden db_path"
    assert _antal_curriculum_tasks(fremmed) == 0


def test_matchende_db_path_skriver_i_den_laeste_base(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    from core.services import heartbeat_curriculum_cadence as cad

    aktiv, _ = _to_baser(tmp_path, monkeypatch)
    res = cad.tick_curriculum_cadence(
        now=datetime(2026, 11, 20, 4, 0, tzinfo=UTC), db_path=str(aktiv)
    )
    assert res is not None and res["created"] == 1
    assert _antal_curriculum_tasks(aktiv) == 1


# ---------------------------------------------------------------------------
# side-695d95f252 — desk-maalingen skal fyres af kadencen, ikke af hånden.
# ---------------------------------------------------------------------------


def test_desk_kadencen_kalder_record_uden_manuelt_kald(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    import core.runtime.db_core as db_core
    from core.services import desk_render_capability as drc
    from core.services import heartbeat_curriculum_cadence as cad

    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "x.db")
    monkeypatch.setattr(cad, "_spawn", lambda fn: fn())  # synkront i testen
    kald: list[int] = []
    monkeypatch.setattr(drc, "record", lambda **kw: kald.append(1) or {"measured": True, "ok": True})

    t0 = datetime(2026, 11, 20, 4, 0, tzinfo=UTC)
    assert cad.tick_desk_measurement_cadence(now=t0) == {"started": True, "at": t0.isoformat(timespec="seconds")}
    assert kald == [1], "kadencen kaldte ikke record()"

    # Inden for intervallet: ingen ny maaling.
    assert cad.tick_desk_measurement_cadence(now=t0 + timedelta(hours=1)) is None
    assert kald == [1]

    # Efter intervallet: igen.
    cad.tick_desk_measurement_cadence(
        now=t0 + timedelta(seconds=cad.DESK_MEASUREMENT_INTERVAL_SECONDS + 1)
    )
    assert kald == [1, 1]


def test_hjerteslaget_kalder_desk_kadencen():
    import ast
    import inspect
    import textwrap

    import core.services.heartbeat_runtime as hr

    trae = ast.parse(textwrap.dedent(inspect.getsource(hr._run_heartbeat_tick_locked)))
    assert any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "tick_desk_measurement_cadence"
        for n in ast.walk(trae)
    )
