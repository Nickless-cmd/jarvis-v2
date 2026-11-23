"""Kadence-registeret er en FALLBACK — ikke en autoritativ kilde.

MAALT 23/11-2026, da registeret blev indfoert: `test_old_chronicle_enqueued`
begyndte at fejle, men KUN naar den koerte efter `test_recent_chronicle_skipped`
i samme proces. Aarsagen var registeret selv:

    test_recent_chronicle_skipped  -> chronicle_refresh (2 t siden) skrives
    test_old_chronicle_enqueued    -> chronicle_refresh (48 t siden) laeses
                                      fra registeret og springes over

Altsaa: to kald i samme proces blev raekkefoelgeafhaengige, fordi registeret
overskrev friskere data fra job-koen. Det er praecis den slags skjult global
tilstand der goer en scheduler umulig at maale paa.

RETTELSEN — to graenser, begge testet her:
1. Registeret bruges KUN for kadencer laengere end trimningsvinduet (~27 t
   ved 2000 terminale poster). Kortere kadence kan koen altid selv svare paa.
2. Registeret maa kun SUPPLERE naar koen ikke selv har en nyere observation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.runtime.workspace_paths as wp
from core.services.periodic_jobs_scheduler import check_and_enqueue_due_periodic_jobs


def _job(job_type: str, hours_ago: float, status: str = "completed") -> dict:
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "job_type": job_type,
        "status": status,
        "completed_at": ts if status == "completed" else None,
        "enqueued_at": ts,
    }


def _koer(jobs: list[dict]) -> dict:
    with patch("core.services.jobs_engine.all_jobs", side_effect=lambda *a, **k: jobs), \
         patch("core.services.jobs_engine.enqueue_job", side_effect=lambda **kw: "job-test"):
        return check_and_enqueue_due_periodic_jobs()


def _register() -> "object":
    return wp.shared_dir() / "runtime" / "periodic_last_run.json"


def test_kort_kadence_roerer_ikke_registeret() -> None:
    """chronicle_refresh har 24 t — under trimningsvinduet, saa koen er
    paalidelig og registeret skal slet ikke bruges."""
    p = _register()
    if p.exists():
        p.unlink()
    _koer([_job("chronicle_refresh", hours_ago=2)])
    assert not p.exists(), "en 24-timers kadence skal ikke skrive til registeret"


def test_to_kald_i_samme_proces_er_uaftaengige_af_raekkefoelgen() -> None:
    """DEN fejl, maalt 23/11-2026 i `test_periodic_jobs_scheduler.py`.

    `test_recent_chronicle_skipped` koerte foerst og skrev et frisk
    `chronicle_refresh`-tidsstempel. Derefter sprang
    `test_old_chronicle_enqueued` et 48 timer gammelt job over — fordi den
    laeste registeret i stedet for koen. To kald i samme proces blev
    raekkefoelgeafhaengige af skjult global tilstand.

    BEMAERK — denne test fanger IKKE fejlen alene. Maalt 23/11-2026: paa den
    oprindelige kode bestod den, fordi den version slet ikke fik skrevet
    registeret i pytest-miljoeet (mappen findes ikke foer foerste skrivning).
    Den er en vagt mod at rettelsen gaar tabt, ikke et bevis for at fejlen
    fandtes. Beviset for fejlen er `test_lang_kadence_skrives_til_registeret`,
    som fejler paa originalen og bestaar her.
    """
    p = _register()
    if p.exists():
        p.unlink()
    # Foerste kald: chronicle_refresh koerte for 2 timer siden.
    _koer([_job("chronicle_refresh", hours_ago=2)])
    # Andet kald: samme job, men nu 48 timer gammelt -> skal koes.
    resultat = _koer([_job("chronicle_refresh", hours_ago=48)])
    assert "chronicle_refresh" in resultat["enqueued"], (
        "registeret overskrev friskere data fra koen — kaldene blev "
        "raekkefoelgeafhaengige"
    )


def test_lang_kadence_skrives_til_registeret() -> None:
    """goal_reporter har 7 doegn — over trimningsvinduet. Uden registeret
    forsvinder den ur af koen og bliver aldrig koert igen."""
    p = _register()
    if p.exists():
        p.unlink()
    _koer([_job("goal_reporter", hours_ago=2)])
    assert p.exists(), "en 7-doegns kadence skal skrives til registeret"
    assert "goal_reporter" in p.read_text(encoding="utf-8")


def test_registeret_kan_baere_en_kadence_koen_har_glemt() -> None:
    """Det oprindelige formaal: jobbet er trimmet ud af koen, men registeret
    husker det — og en forfaldent kadence skal stadig fyres."""
    p = _register()
    p.parent.mkdir(parents=True, exist_ok=True)
    gammel = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    p.write_text('{"goal_reporter": "%s"}' % gammel, encoding="utf-8")
    # Koen er TOM — den kan slet ikke svare.
    resultat = _koer([])
    assert "goal_reporter" in resultat["enqueued"], (
        "registeret skulle baere kadencen naar koen ikke kan"
    )
