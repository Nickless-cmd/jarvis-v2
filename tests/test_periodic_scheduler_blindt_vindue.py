"""Schedulerens vindue skar halen af — og halen var hele svaret.

MAALT paa runtime 13/9-2026:

    jobs i filen          2.007
    schedulerens vindue     200
    quarterly_arc         157 jobs, 156 koert — NUL i vinduet

`quarterly_arc` HAVDE koert 156 gange. Scheduleren kunne bare ikke se det,
konkluderede «last seen never» og lagde et KVARTALS-job i koe hvert 30. sekund:
221 gange paa to timer. Og hver ny raekke skubbede de gamle koersler laengere
ud af vinduet — selvforstaerkende.

Samme familie som `decision_review_blind_tail`, hvor et `limit=20` mod 45
aktive gjorde plads 21-45 usynlige.
"""
from datetime import datetime, timedelta, timezone

import core.services.periodic_jobs_scheduler as sched


def _job(jt: str, alder_dage: float, status: str = "ok") -> dict:
    t = datetime.now(timezone.utc) - timedelta(days=alder_dage)
    return {"job_type": jt, "status": status, "completed_at": t.isoformat()}


def _koer(monkeypatch, jobs, enqueued_ud):
    # Begge importeres DOVENT inde i funktionen, saa de skal patches paa
    # kildemodulet — ikke paa scheduleren.
    import core.services.jobs_engine as je
    monkeypatch.setattr(je, "all_jobs", lambda: jobs, raising=False)
    monkeypatch.setattr(
        je, "enqueue_job",
        lambda **kw: (enqueued_ud.append(kw.get("job_type")), "job-test")[1])
    return sched.check_and_enqueue_due_periodic_jobs()


def test_et_nyligt_koert_job_laegges_IKKE_i_koe_igen(monkeypatch):
    jt = next(iter(sched._SCHEDULE))
    ud = []
    _koer(monkeypatch, [_job(jt, alder_dage=0.0)], ud)
    assert jt not in ud


def test_halen_taeller_ogsaa_naar_der_ligger_tusinder_af_nyere_jobs(monkeypatch):
    """DEN fejl. Jobbet koerte for en time siden, men 2.000 nyere raekker
    skubbede det ud af de 200 scheduleren saa."""
    jt = next(iter(sched._SCHEDULE))
    gammel = _job(jt, alder_dage=0.02)                 # ~30 min siden
    stoej = [_job("noget_andet", alder_dage=0.001) for _ in range(2000)]
    ud = []
    _koer(monkeypatch, [gammel, *stoej], ud)
    assert jt not in ud, "jobbet blev koe-sat igen selvom det lige har koert"


def test_et_job_der_ER_forfaldent_laegges_stadig_i_koe(monkeypatch):
    """Vagten maa ikke koebe sin praecision ved at holde op med at planlaegge."""
    jt = next(iter(sched._SCHEDULE))
    cadence = sched._SCHEDULE[jt]
    ud = []
    _koer(monkeypatch, [_job(jt, alder_dage=cadence.total_seconds() / 86400 * 3)], ud)
    assert jt in ud


def test_scheduleren_bruger_IKKE_et_afkortet_vindue(monkeypatch):
    """Kilde-vagt: gaar nogen tilbage til `list_jobs(limit=...)`, er den
    selvforstaerkende loekke tilbage — og den er ikke til at se i drift,
    for jobbene koerer jo."""
    import inspect
    k = inspect.getsource(sched.check_and_enqueue_due_periodic_jobs)
    assert "all_jobs()" in k
    assert "list_jobs(limit=" not in k
