"""Periodic jobs scheduler — enqueues overdue background jobs.

Background: governance_bootstrap registers handlers (chronicle_refresh,
memory_decay_sweep, dream_distillation_sweep, weekly_manifest_refresh)
but historically nothing periodically *enqueued* them. The handlers
slept; chronicle stalled at 17. april (9 days idle); manifest never
got the weekly refresh that was always intended.

This module fixes that with a single idempotent function:
``check_and_enqueue_due_periodic_jobs``. It looks at the most recent
job of each scheduled type and enqueues a new one when the cadence
threshold is exceeded. Safe to call frequently — duplicate-suppressed
by both pending-job check and cadence threshold.

Hooked into ``poll_heartbeat_schedule`` so it runs naturally with the
~30s heartbeat poll. Cheap: a JSON load + a few timestamp comparisons.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# job_type → cadence (timedelta between scheduled enqueues)
_SCHEDULE: dict[str, timedelta] = {
    "chronicle_refresh": timedelta(hours=24),
    "weekly_manifest_refresh": timedelta(days=7),
    # 15/11-2026: goal_reporter havde kun et CLI-script og en promptet
    # recurring-task. Den skrev 5/10, 12/10 og 19/10 og forsvandt derefter,
    # fordi ingen deterministisk runtime-path ejede kadencen.
    "goal_reporter": timedelta(days=7),
    "goal_synthesis": timedelta(days=7),
    "personality_snapshot": timedelta(hours=4),  # 6x/day for stable baseline
    "provider_health_check": timedelta(minutes=5),  # 12x/hour proactive ping
    "auto_improvement_proposals": timedelta(hours=24),  # daily check + propose
    "agent_observation_decay": timedelta(hours=24),  # daily stale-marking
    # Sikkerhedsnet: vækninger fyres primært af `wakeup_ticker` (5 s-tråd, 12/11-2026).
    "wakeup_dispatch": timedelta(seconds=60),
    # Identity formation infrastructure (2026-04-27)
    "crisis_scan": timedelta(hours=24),  # daily — find friction moments
    "identity_drift_proposal": timedelta(days=7),  # weekly — file proposal if drifted
    "monthly_arc": timedelta(days=28),  # monthly narrative
    "quarterly_arc": timedelta(days=91),  # quarterly arc
    "annual_arc": timedelta(days=365),  # annual transformation doc
    # System-intelligence growth (2026-04-27)
    "skill_distillation": timedelta(days=7),  # weekly principle extraction per role
    "arc_rule_extraction": timedelta(days=7),  # weekly rule extraction from new arcs
    "signal_surface_gc": timedelta(hours=1),   # hourly trim of stale/old signal surfaces
    "decision_review": timedelta(hours=24),    # daily LLM-led self-review of active decisions
    # 2/10-2026: hoerte foer paa `_HEARTBEAT_TICK_COUNTER % 60`, og den taeller
    # nulstilles ved genstart — maalt 9 tik/6t betyder ~40 TIMER til 60, saa med
    # tre genstarter paa ét doegn fyrede den aldrig. Her ligger den paa en durabel
    # «last seen». Pollen er hyppigere end selve paamindelsen (registret har sin
    # egen 24-timers klokke), saa en forfalden review meldes inden for 6 timer
    # uden at kunne naevnes to gange paa en dag.
    "shadow_review_reminder": timedelta(hours=6),
    # 12/10-2026: TRE af governance_bootstraps 21 handlers stod uden kadence.
    # `chronicle_refresh` og `weekly_manifest_refresh` fik deres i maj, men
    # `memory_decay_sweep`, `dream_distillation_sweep` og
    # `concept_baseline_evaluation` blev glemt — deres handlers sov for evigt,
    # praecis det docstringen ovenfor advarede om. Alle tre er daglige:
    # memory_decay self-throttler selv paa 24t, dream-distillation har sin egen
    # kill-switch + min-content-gate (billig uden materiale), og
    # concept_baseline_evaluation skriver sin egen docstring «Daily».
    "memory_decay_sweep": timedelta(hours=24),
    "dream_distillation_sweep": timedelta(hours=24),
    "concept_baseline_evaluation": timedelta(hours=24),
    # 13/10-2026: sessionstitlerne stod som den raa foerste besked — «hey»,
    # «yo», «Godmorgen» — fordi titlen saettes ÉN gang fra besked nummer ét
    # og aldrig samles op igen. 608 sessioner, maalt. Sweepet navngiver 3 pr.
    # gang, saa kadencen bestemmer hvor hurtigt efterslaebet forsvinder:
    # 15 min = 12 i timen.
    "session_titling_sweep": timedelta(minutes=15),
}


def _extract_last_time(item: dict[str, Any]) -> datetime | None:
    """Pick the most relevant timestamp from a job record."""
    for key in ("completed_at", "started_at", "enqueued_at"):
        v = item.get(key)
        if not v:
            continue
        try:
            return datetime.fromisoformat(str(v))
        except ValueError:
            continue
    return None


def _report_goal_reporter_liveness(
    *, last_run: datetime | None, now: datetime,
) -> None:
    """Gør en aldrig kørt eller otte dage gammel reporter ejer-synlig.

    Alarmen har en stabil kilde-id og deduplikeres derfor af
    ``background_attention``. Selve job-handleren lukker posten efter næste
    vellykkede ``goal_update``.
    """
    if last_run is not None and (now - last_run) <= timedelta(days=8):
        return
    try:
        from core.services.background_attention import report_background_outcome

        alder = "aldrig" if last_run is None else last_run.isoformat()
        report_background_outcome(
            source_kind="goal-reporter",
            source_id="weekly-run",
            status="failed",
            severity="high",
            summary=f"Goal-reporteren har ikke leveret sin ugentlige måling; seneste kørsel: {alder}.",
            suggested_next_step="Kontrollér goal_reporter-jobbet og det aktive pålidelighedsmål.",
            requires_attention=True,
            safe_to_continue=True,
        )
    except Exception as exc:
        logger.warning("periodic_jobs_scheduler: goal_reporter liveness-alarm fejlede: %s", exc)


def check_and_enqueue_due_periodic_jobs() -> dict[str, Any]:
    """Idempotent — enqueue any periodic jobs whose cadence is exceeded.

    Returns {"enqueued": [job_types]}. Empty list = nothing was due.
    Skips a job_type if there's already a pending one (avoid pile-up).

    2026-05-17 perf fix: tidligere blev jobs_engine._load() (16 MB JSON-parse,
    ~235 ms) kaldt op til 36× pr. 30s heartbeat-poll — 2× pr. job_type via
    _has_pending + _last_job_time. py-spy viste 76-79% inclusive CPU på den
    path. Daemons "kogede" fordi scheduleren ikke nåede at enqueue dem
    rettidigt. Fix: ÉN list_jobs() øverst, in-memory filtering bagefter.
    """
    enqueued: list[str] = []
    skipped: list[str] = []
    now = datetime.now(UTC)

    try:
        from core.services.jobs_engine import _TERMINAL_STATUSES, all_jobs, enqueue_job
    except Exception as exc:
        logger.debug("periodic_jobs_scheduler: jobs_engine import failed: %s", exc)
        try:
            from core.services.background_attention import report_background_outcome
            report_background_outcome(
                source_kind="periodic-scheduler", source_id="jobs-engine-import",
                status="failed", severity="high",
                summary=f"Periodic scheduler kunne ikke indlæse jobs engine ({type(exc).__name__}).",
                suggested_next_step="Kontrollér jobs-engine import og runtime-log.",
                requires_attention=True, safe_to_continue=False,
            )
        except Exception:  # the next scheduler tick retries durable reporting
            pass
        return {"enqueued": [], "skipped": [], "error": str(exc)}

    # Load ONE gang — herfra arbejder vi på in-memory data
    try:
        # ALLE jobs, ikke de seneste 200. Vinduet skar netop de gamle koersler
        # af — og det er dem der afgoer om et kvartals-job har koert. Se
        # jobs_engine.all_jobs for maalingen.
        all_items = all_jobs()
    except Exception as exc:
        logger.warning("periodic_jobs_scheduler: kunne ikke laese jobs: %s", exc)
        try:
            from core.services.background_attention import report_background_outcome
            report_background_outcome(
                source_kind="periodic-scheduler", source_id="job-list-read",
                status="failed", severity="high",
                summary=f"Periodic scheduler kunne ikke læse joblisten ({type(exc).__name__}).",
                suggested_next_step="Kontrollér joblageret før næste scheduler-runde.",
                requires_attention=True, safe_to_continue=False,
            )
        except Exception:  # the next scheduler tick retries durable reporting
            pass
        all_items = []

    # Byg pending-set + last-time map i én pass
    pending_types: set[str] = set()
    last_times: dict[str, datetime] = {}
    terminal_times: dict[str, datetime] = {}
    for item in all_items:
        jt = item.get("job_type")
        if not jt:
            continue
        if item.get("status") == "pending":
            pending_types.add(jt)
        ts = _extract_last_time(item)
        if ts is not None:
            existing = last_times.get(jt)
            if existing is None or ts > existing:
                last_times[jt] = ts
            # MAALT 23/11-2026: her stod en LOKAL kopi af listen
            # ({"completed","failed","cancelled","lost"}) — og den manglede netop
            # `ok` og `error`, som er dem jobs_engine faktisk skriver. 1999 af
            # 2000 poster i koeen havde status `ok`, saa registeret kunne kun
            # nogensinde indeholde det ene job der tilfaeldigt var `completed`.
            # Otte af ni lange kadencer (inkl. quarterly_arc 91 dage og
            # annual_arc 365 dage) blev derfor ALDRIG skrevet — praecis den fejl
            # registeret skulle loese. Brug den autoritative liste i stedet for
            # en kopi der driver.
            if str(item.get("status") or "") in _TERMINAL_STATUSES:
                prev = terminal_times.get(jt)
                if prev is None or ts > prev:
                    terminal_times[jt] = ts

    # 22/11-2026: kadence-hukommelsen boede UDELUKKENDE i job-køen, som trimmes
    # til 2000 terminale poster (jobs_engine._KEEP_TERMINAL). wakeup_dispatch
    # fylder ~1526 af dem i døgnet, så vinduet er ~27 timer. Målt 22/11:
    # goal_reporter (kadence 7 døgn) skrev 15., 16., 18., 19., 20. og 21/11 med
    # ~27,2 t mellemrum — og vagten nedenfor (8 døgn) kunne ALDRIG fyre, fordi
    # den læste samme forkortede vindue. Registeret her overlever trimning.
    import json as _json  # lokal import: holder ændringen i ét sammenhængende stykke

    def _durable_path():
        from core.runtime.workspace_paths import shared_dir
        return shared_dir() / "runtime" / "periodic_last_run.json"

    durable_path = _durable_path()

    def _load_durable() -> dict[str, datetime]:
        try:
            with durable_path.open("r", encoding="utf-8") as f:
                raw = _json.load(f)
        except (FileNotFoundError, ValueError, OSError) as exc:  # foerste koersel eller korrupt fil — tomt register er den aerlige tilstand
            logger.debug("periodic_jobs_scheduler: register kunne ikke laeses: %s", exc)
            return {}
        out: dict[str, datetime] = {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                try:
                    out[str(key)] = datetime.fromisoformat(str(value))
                except ValueError:  # en enkelt daarlig raekke maa ikke kaste hele registeret ud
                    continue
        return out

    def _save_durable(data: dict[str, datetime]) -> None:
        try:
            durable_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = durable_path.with_suffix(".json.tmp")
            tmp.write_text(
                _json.dumps({k: v.isoformat() for k, v in data.items()}, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(durable_path)
        except OSError as exc:  # en fejlet skrivning maa ikke vaere tavs — saa forsvinder kadencen uden spor
            logger.warning("periodic_jobs_scheduler: kunne ikke skrive sidst-koert: %s", exc)

    # Registeret er en FALLBACK, ikke en autoritativ kilde. Det maa kun bruges
    # naar job-koen ikke selv kan svare — ellers overskriver det friskere data
    # fra koen, og to kald i samme proces bliver raekkefoelgeafhaengige
    # (maalt 23/11-2026: en `chronicle_refresh` der koerte for 2 timer siden
    # blev skrevet til registeret, hvorefter et 48 timer gammelt job i naeste
    # kald blev sprunget over).
    #
    # Derfor: kun kadencer LAENGERE end trimningsvinduet (~27 timer ved 2000
    # terminale poster) har et reelt behov. Kortere kadence kan koen altid
    # selv svare paa, og de skal hverken laeses eller skrives her.
    _DUREBAR_MIN_KADENCE = timedelta(hours=27)

    def _har_reelt_behov(jt: str) -> bool:
        kadence = _SCHEDULE.get(jt)
        return kadence is not None and kadence > _DUREBAR_MIN_KADENCE

    durable = _load_durable()
    merged = dict(durable)
    for jt, ts in terminal_times.items():
        if _har_reelt_behov(jt) and (jt not in merged or ts > merged[jt]):
            merged[jt] = ts
    if merged != durable:
        _save_durable(merged)
    for jt, ts in merged.items():
        if not _har_reelt_behov(jt):
            continue
        # Kun naar koen SLET IKKE har en observation for typen. Har koen en
        # post — ogsaa en gammel — er den den sande kilde: den er jobbets
        # faktiske historik, mens registeret er en erindring om det.
        if jt in last_times:
            continue
        last_times[jt] = ts

    _report_goal_reporter_liveness(last_run=last_times.get("goal_reporter"), now=now)

    for job_type, cadence in _SCHEDULE.items():
        if job_type in pending_types:
            skipped.append(f"{job_type} (already pending)")
            continue
        last = last_times.get(job_type)
        if last is not None and (now - last) < cadence:
            continue
        try:
            jid = enqueue_job(
                job_type=job_type,
                payload={"reason": "periodic-scheduled", "cadence_hours": int(cadence.total_seconds() / 3600)},
                priority=8,  # low — these are background self-maintenance
                max_requests=1,
            )
            enqueued.append(job_type)
            logger.info("periodic_jobs_scheduler: enqueued %s (job %s, last seen %s)",
                        job_type, jid, last.isoformat() if last else "never")
        except Exception as exc:
            logger.warning("periodic_jobs_scheduler: enqueue %s failed: %s", job_type, exc)
            try:
                from core.services.background_attention import report_background_outcome
                report_background_outcome(
                    source_kind="periodic-scheduler", source_id=job_type,
                    status="failed", severity="high",
                    summary=(
                        f"Periodic scheduler kunne ikke køsætte {job_type} "
                        f"({type(exc).__name__})."
                    ),
                    suggested_next_step="Undersøg jobtypen og jobs-engine før genforsøg.",
                    requires_attention=True, safe_to_continue=True,
                )
            except Exception:  # the next scheduler tick retries durable reporting
                pass

    return {"enqueued": enqueued, "skipped": skipped}
