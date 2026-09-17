from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def _isolate_state_store(tmp_path, monkeypatch):
    """Hold disse tests væk fra produktionens ``in_flight_runs.json``.

    ``isolated_runtime`` reloader bevidst IKKE ``core.runtime.state_store``
    (se conftest ~1092: et reload ville desynkronisere moduler der importerer
    ``load_json``/``save_json`` ved navn). Men ``state_store._STATE_DIR`` bindes
    til ``Path.home()/".jarvis-v2"/"state"`` ved import — altså den RIGTIGE
    sti. Uden denne fixture læste og SKREV testene produktionens fil.

    Målt 13/9-2026: en ægte ``running``-post ældre end ``STALE_AFTER_SECONDS``
    blev et ekstra orphan, så ``test_enabled_zombie_...`` gav ``count == 2``
    afhængigt af hvad der tilfældigvis kørte i produktionen — og hver kørsel
    efterlod sine egne poster i den rigtige fil.

    Vi reloader ikke (det er den desync conftest advarer om). Vi flytter blot
    stien for disse tests; ``load_json``/``save_json`` læser ``_STATE_DIR``
    ved kald, så det er nok.
    """
    from core.runtime import state_store

    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path / "state")


def _fresh_modules():
    runs = importlib.reload(importlib.import_module("core.services.in_flight_runs"))
    importlib.reload(importlib.import_module("core.services.session_persistence_flag"))
    rec = importlib.reload(importlib.import_module("core.services.session_boot_reconciler"))
    return runs, rec


def _seed(runs, *, status="running", age_s=1000, run_id="run-z", kind="visible"):
    started = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    records = runs._load()
    records[run_id] = {
        "run_id": run_id, "session_id": "s1", "status": status,
        "kind": kind, "provider": "", "model": "",
        "excerpt": "arbejde", "started_at": started, "last_tool": "",
    }
    runs._save(records)


def _enable(on: bool):
    from core.runtime.db import set_runtime_state_value
    set_runtime_state_value("session_persistence", "on" if on else "off")


def test_flag_default_off(isolated_runtime):
    _, rec = _fresh_modules()
    from core.services.session_persistence_flag import session_persistence_enabled
    assert session_persistence_enabled() is False


def test_enabled_zombie_marked_interrupted_and_nerve_fired(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-z")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    # Opgave 4 (17/9-2026): en SYNLIG tur der døde med processen er
    # genoptagelig, ikke bare afbrudt — ellers er der intet forfaldent for
    # dispatcheren at tage, og opgaven forsvinder med processen.
    assert runs._load()["run-z"]["status"] == "recovering"
    assert runs._load()["run-z"]["exit_reason"] == "afbrudt af container-genstart"
    assert summary["count"] == 1
    assert summary["enforced"] is True
    assert observed and observed[0]["count"] == 1
    assert observed[0]["enforced"] is True
    assert "visible" in observed[0]["kinds"]


def test_fresh_running_untouched(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=5, run_id="run-fresh")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    summary = rec.reconcile_on_boot()

    assert runs._load()["run-fresh"]["status"] == "running"
    assert summary["count"] == 0


def test_already_interrupted_untouched(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="interrupted", age_s=1000, run_id="run-i")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    summary = rec.reconcile_on_boot()

    assert runs._load()["run-i"]["status"] == "interrupted"
    assert summary["count"] == 0


def test_disabled_observe_only_no_writes(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(False)
    _seed(runs, status="running", age_s=1000, run_id="run-z")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    # Nothing written: still 'running'.
    assert runs._load()["run-z"]["status"] == "running"
    # But we counted what WOULD happen.
    assert summary["count"] == 1
    assert summary["enforced"] is False
    assert observed and observed[0]["count"] == 1
    assert observed[0]["enforced"] is False


def test_idempotent_second_run_finds_nothing(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-z")
    monkeypatch.setattr(rec, "_observe", lambda payload: None)

    first = rec.reconcile_on_boot()
    second = rec.reconcile_on_boot()

    assert first["count"] == 1
    assert second["count"] == 0
    assert runs._load()["run-z"]["status"] == "recovering"


def test_reconciler_swallows_exceptions(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)

    def _boom(_):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(rec.in_flight_runs, "list_running_orphans", _boom)

    # Must not raise; returns a safe empty-ish summary.
    summary = rec.reconcile_on_boot()
    assert summary["count"] == 0
    assert summary.get("error") is True


def test_kinds_aggregated_across_orphans(isolated_runtime, monkeypatch):
    runs, rec = _fresh_modules()
    _enable(True)
    _seed(runs, status="running", age_s=1000, run_id="run-v", kind="visible")
    _seed(runs, status="running", age_s=1000, run_id="run-a", kind="autonomous")

    observed = []
    monkeypatch.setattr(rec, "_observe", lambda payload: observed.append(payload))

    summary = rec.reconcile_on_boot()

    assert summary["count"] == 2
    assert set(observed[0]["kinds"]) == {"visible", "autonomous"}


# ── visible_drift: rækker reconcileren ellers aldrig ser ────────────────────
#
# `list_running_orphans` itererer over `in_flight_runs`. En række der findes i
# `visible_runs` men aldrig blev skrevet — eller blev ryddet — i det andet lager
# er derfor usynlig for reconcileren for altid. Målt 13/9-2026: en kørsel stod
# `running` i ~20 timer mens reconcileren rapporterede `count: 0` ved hver
# opstart. Begge dele var sande; de så på hvert sit lager.


def _vis_row(run_id, *, age_s=1000, status="running", finished_at=""):
    """Skriv én række direkte i `visible_runs` (den isolerede DB)."""
    from core.runtime.db import connect
    from core.runtime.db_visible import ensure_visible_tables

    started = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    with connect() as conn:
        ensure_visible_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO visible_runs "
            "(run_id, lane, provider, model, status, started_at, finished_at, "
            " text_preview, error, capability_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, "primary", "ollama", "glm-5.2:cloud", status, started,
             finished_at, "arbejde", None, None),
        )


def _vis_status(run_id):
    from core.runtime.db import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT status FROM visible_runs WHERE run_id=?", (run_id,)
        ).fetchone()
    return row["status"] if row else None


def test_visible_ukendt_lager_stempler_ikke(isolated_runtime, monkeypatch, caplog):
    """Kan vi ikke læse det andet lager, kan vi ikke vide at posten er ukendt.

    Et gæt er ikke et fravær — så vi stempler ikke. Men fejlen skal SES.
    """
    import logging

    runs, rec = _fresh_modules()
    _vis_row("visible-zombie", age_s=20 * 3600)

    def _boom():
        raise RuntimeError("lageret svarer ikke")

    monkeypatch.setattr(rec.in_flight_runs, "_load", _boom)

    with caplog.at_level(logging.WARNING):
        n = rec._ryd_visible_drift(enforced=True)

    assert n == 0
    assert _vis_status("visible-zombie") == "running"
    assert any("kunne ikke laese in_flight_runs" in r.message
               for r in caplog.records)


def test_visible_stemplingsfejl_logges_ikke_sluges(isolated_runtime, monkeypatch, caplog):
    """En fejlende stempling må ikke forsvinde lydløst.

    Importen af `visible_runs_outcomes` er cirkulær og kan fejle hvis
    `visible_runs` endnu ikke er importeret. Lå fejlen bag `except: pass`, stod
    rækken bare `running` igen — uden et ord nogen steder.
    """
    import logging

    import core.services.visible_runs_outcomes as vro

    runs, rec = _fresh_modules()
    _vis_row("visible-zombie", age_s=20 * 3600)

    def _boom(*_a, **_k):
        raise RuntimeError("cirkulaer import")

    monkeypatch.setattr(vro, "stamp_visible_run_interrupted", _boom)

    with caplog.at_level(logging.WARNING):
        n = rec._ryd_visible_drift(enforced=True)

    assert n == 1                       # den tæller stadig driften
    assert _vis_status("visible-zombie") == "running"   # men kunne ikke stemple
    assert any("kunne ikke stemple" in r.message for r in caplog.records)
