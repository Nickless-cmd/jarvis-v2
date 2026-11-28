"""Daemon-vagten skal have en kadence OG en kalder — ikke kun et værktøj.

28/11-2026: `daemon_health_alert` var kaldt nul gange i `tool_hooks.jsonl` og
`tools_churn.jsonl`, og `daemon_alerts.json` var urørt siden 17/5-2026. Værktøjet
var bygget med durable inbox-skrivning, 2-timers cooldown og side-task-oprettelse,
men intet heartbeat-, cadence- eller scheduler-modul gik ind i det.

Det er samme fejlklasse som `periodic_jobs_scheduler`-docstringen advarer om:
mekanismen findes, men ingen kalder den. Den eksisterende vagt
(`test_hver_registreret_handler_har_en_kadence`) fangede kun handler→kadence;
denne fil binder den omvendte vej: kadence→handler→faktisk kald.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.periodic_jobs_scheduler import (
    _SCHEDULE,
    check_and_enqueue_due_periodic_jobs,
)


def _job(job_type: str, hours_ago: float, status: str = "ok"):
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "job_type": job_type,
        "status": status,
        "completed_at": ts if status in {"completed", "ok"} else None,
        "enqueued_at": ts,
    }


def test_vagten_har_en_kadence():
    assert "daemon_health_alert" in _SCHEDULE, (
        "daemon_health_alert står ikke i _SCHEDULE — så bliver den aldrig køsat"
    )
    assert _SCHEDULE["daemon_health_alert"] <= timedelta(hours=2), (
        "kadencen er længere end værktøjets egen 2-timers cooldown; en daemon "
        "ville kunne være død i timevis uden at nogen opdagede det"
    )


def test_uden_historik_koesættes_vagten():
    ud: list[str] = []

    def fake_enqueue(**kw):
        ud.append(kw["job_type"])
        return "job-x"

    with patch("core.services.jobs_engine.all_jobs", return_value=[]), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()

    assert "daemon_health_alert" in result["enqueued"]
    assert "daemon_health_alert" in ud


def test_frisk_koersel_springes_over():
    with patch(
        "core.services.jobs_engine.all_jobs",
        return_value=[_job("daemon_health_alert", hours_ago=0.2)],
    ), patch("core.services.jobs_engine.enqueue_job", return_value="job-x"):
        result = check_and_enqueue_due_periodic_jobs()

    assert "daemon_health_alert" not in result["enqueued"]


def test_forfalden_koersel_koesættes_igen():
    with patch(
        "core.services.jobs_engine.all_jobs",
        return_value=[_job("daemon_health_alert", hours_ago=3)],
    ), patch("core.services.jobs_engine.enqueue_job", return_value="job-x"):
        result = check_and_enqueue_due_periodic_jobs()

    assert "daemon_health_alert" in result["enqueued"]


def test_handleren_er_registreret_og_kalder_vaerktoejet(monkeypatch):
    """Kadencen er værdiløs hvis jobtypen ikke har en handler."""
    from core.services import governance_bootstrap as gb

    captured: dict[str, object] = {}
    kald: list[dict] = []

    def fake_register(job_type, handler):
        captured[job_type] = handler

    def fake_alert(args):
        kald.append(args)
        return {"status": "ok", "overdue_count": 0}

    fake_jobs = type(sys)("core.services.jobs_engine")
    fake_jobs.register_handler = fake_register  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core.services.jobs_engine", fake_jobs)
    monkeypatch.setattr(
        "core.tools.daemon_alert_tools._exec_daemon_health_alert", fake_alert,
    )

    gb.ensure_default_job_handlers()

    assert "daemon_health_alert" in captured, (
        "jobtypen har en kadence men ingen handler — den ville sove for evigt"
    )
    handler = captured["daemon_health_alert"]
    result = handler({})  # type: ignore[operator]
    assert result["status"] == "ok"
    assert kald and kald[0]["notify"] is True


def test_handleren_fejler_hoejt_naar_vaerktoejet_kaster(monkeypatch):
    """En tavs fejl ville skjule at vagten står stille."""
    from core.services import governance_bootstrap as gb

    captured: dict[str, object] = {}
    fake_jobs = type(sys)("core.services.jobs_engine")
    fake_jobs.register_handler = lambda jt, h: captured.__setitem__(jt, h)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core.services.jobs_engine", fake_jobs)

    def boom(args):
        raise RuntimeError("daemon-manager nede")

    monkeypatch.setattr("core.tools.daemon_alert_tools._exec_daemon_health_alert", boom)

    gb.ensure_default_job_handlers()
    result = captured["daemon_health_alert"]({})  # type: ignore[operator]

    assert result["status"] == "error"
    assert "daemon-manager nede" in result["error"]
