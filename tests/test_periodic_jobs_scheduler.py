"""Unit tests for periodic_jobs_scheduler — chronicle/manifest cadence."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.periodic_jobs_scheduler import (
    check_and_enqueue_due_periodic_jobs,
)


def _job(job_type: str, hours_ago: float, status: str = "completed"):
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "job_type": job_type,
        "status": status,
        "completed_at": ts if status == "completed" else None,
        "enqueued_at": ts,
    }


def test_no_history_enqueues_all():
    enq_calls = []
    def fake_list(*a, **kw):
        return []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return f"job-{kw['job_type']}-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" in result["enqueued"]
    assert "weekly_manifest_refresh" in result["enqueued"]


def test_recent_chronicle_skipped():
    # 2026-05-17 perf fix: scheduler nu loader job-listen ÉN gang og filtrerer
    # in-memory. fake_list returnerer derfor det fulde sæt, ikke pre-filtreret.
    def fake_list(*a, **kw):
        return [_job("chronicle_refresh", hours_ago=2)]
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" not in result["enqueued"]
    assert "weekly_manifest_refresh" in result["enqueued"]


def test_pending_chronicle_skipped():
    def fake_list(*a, **kw):
        return [_job("chronicle_refresh", hours_ago=0.1, status="pending")]
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" not in result["enqueued"]
    assert any("chronicle_refresh" in s for s in result["skipped"])


def test_old_chronicle_enqueued():
    def fake_list(*a, **kw):
        return [_job("chronicle_refresh", hours_ago=48)]
    enq_calls = []
    def fake_enqueue(**kw):
        enq_calls.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    assert "chronicle_refresh" in result["enqueued"]


def test_recent_weekly_manifest_skipped():
    def fake_list(*a, **kw):
        return [_job("weekly_manifest_refresh", hours_ago=24)]
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", return_value="job-x") as enq:
        result = check_and_enqueue_due_periodic_jobs()
    assert "weekly_manifest_refresh" not in result["enqueued"]


def test_job_listen_laeses_hoejst_ÉN_gang_pr_kald():
    """Performance contract: scheduler loader job-listen ÉN gang pr. call.

    Tidligere blev _load() kaldt op til 36× pr. 30s heartbeat-poll (18 job_types
    × 2 checks: _has_pending + _last_job_time). Med jobs_queue.json på 16 MB =
    235 ms/load = 8.4 sekunder af brændt CPU pr. poll. py-spy viste 76-79%
    inclusive samples på _load. Daemons "kogede" fordi scheduleren ikke nåede
    at enqueue dem i tide.

    Fix: ÉN læsning øverst, in-memory filter for pending + last_time.

    13/9-2026: `list_jobs(limit=200)` blev til `all_jobs()`, fordi vinduet skar
    de gamle kørsler af og gjorde et kvartals-job «last seen never». Prisen er
    NUL: `list_jobs` kaldte selv `_load()` og klippede bagefter. Kontrakten om
    ét kald er derfor uændret — kun navnet skiftede.
    """
    call_count = {"n": 0}
    def counting_fake_list(*a, **kw):
        call_count["n"] += 1
        return [
            _job("chronicle_refresh", hours_ago=48),
            _job("weekly_manifest_refresh", hours_ago=24),
            _job("provider_health_check", hours_ago=0.1, status="pending"),
        ]
    with patch("core.services.jobs_engine.all_jobs", side_effect=counting_fake_list), \
         patch("core.services.jobs_engine.enqueue_job", return_value="job-x"):
        check_and_enqueue_due_periodic_jobs()
    assert call_count["n"] <= 1, (
        f"list_jobs blev kaldt {call_count['n']} gange — forventet højst 1"
    )


def test_hver_registreret_handler_har_en_kadence():
    """12/10-2026: `governance_bootstrap` registrerer 21 handlers, men TRE af
    dem — `memory_decay_sweep`, `dream_distillation_sweep` og
    `concept_baseline_evaluation` — havde INGEN kadence i `_SCHEDULE`. Deres
    handlers sov derfor for evigt.

    Fejlen var usynlig: et job der aldrig bliver lagt i koe fejler heller
    aldrig, saa intet raabte op. Modulens egen docstring advarede om praecis
    dette («historically nothing periodically enqueued them»), og alligevel
    blev de tre glemt da de to andre fik deres kadence.

    Denne test binder de to ender sammen: en registreret handler uden kadence
    er en fil ingen laeser.
    """
    import re
    from pathlib import Path

    from core.services.periodic_jobs_scheduler import _SCHEDULE

    rod = Path(__file__).resolve().parents[1]
    src = (rod / "core/services/governance_bootstrap.py").read_text(encoding="utf-8")
    blok = re.search(r"handlers = \{(.*?)\n    \}", src, re.S)
    assert blok, "fandt ikke handlers-dict'en i governance_bootstrap"
    jobtyper = set(re.findall(r'"([a-z_]+)":', blok.group(1)))
    assert jobtyper, "handlers-dict'en var tom"

    uden_kadence = sorted(jobtyper - set(_SCHEDULE))
    assert not uden_kadence, (
        f"registrerede handlers UDEN kadence i _SCHEDULE: {uden_kadence} — "
        "deres handlers vil sove for evigt"
    )


def test_de_tre_glemte_cyklusser_lægges_i_koe_nar_de_er_forfaldne():
    """Ingen historik = alle tre er forfaldne og skal i koe."""
    glemte = {
        "memory_decay_sweep",
        "dream_distillation_sweep",
        "concept_baseline_evaluation",
    }
    ud = []
    def fake_list(*a, **kw):
        return []
    def fake_enqueue(**kw):
        ud.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    mangler = sorted(glemte - set(result["enqueued"]))
    assert not mangler, f"disse blev IKKE lagt i koe: {mangler}"


def test_de_tre_glemte_cyklusser_gentages_ikke_nar_de_lige_har_koert():
    """En daglig kadence skal respektere en frisk koersel — ellers fyrer de
    hvert 30. sekund."""
    glemte = [
        "memory_decay_sweep",
        "dream_distillation_sweep",
        "concept_baseline_evaluation",
    ]
    def fake_list(*a, **kw):
        return [_job(jt, hours_ago=2) for jt in glemte]
    ud = []
    def fake_enqueue(**kw):
        ud.append(kw["job_type"])
        return "job-x"
    with patch("core.services.jobs_engine.all_jobs", side_effect=fake_list), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=fake_enqueue):
        result = check_and_enqueue_due_periodic_jobs()
    for jt in glemte:
        assert jt not in result["enqueued"], (
            f"{jt} blev lagt i koe trods en frisk koersel for 2 timer siden"
        )
