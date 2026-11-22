"""En tur der venter på et menneske må ikke erklæres hængt.

Målt 22/11-2026: `should_clear_hung` brugte `age_s > 600` — ALDER, ikke
stilhed. Det var harmløst så længe approval-vinduet var 300 sekunder. Men da
vinduet blev udledt af kortets levetid (3600s, `413cb9079`), kunne en tur
lovligt sidde og vente i op til en time — og så cancellerede rydde-grenen dens
egen controller midt i ventetiden.

Reglen er den samme som `run_event_log.last_activity_at` fik 17/10-2026 for
`stream_sentinel`: mål STILHED, ikke alder. Et virkelig dødt run holder også op
med at røre sig, så zombie-værnet består.

Prøverne kalder beslutningen direkte. Den lå tidligere inline i en 7.000-linjers
generator, hvor ingen prøve kunne nå den — og netop derfor kunne fejlen leve.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_core
from core.services.visible_runs import _stilhed_siden_aktivitet, _stuck_run_dom
from core.services.visible_runs_sections.run_control_state import (
    _set_visible_run_control,
)


@pytest.fixture(autouse=True)
def _ren(isolated_runtime):
    db_core.clear_runtime_state_cache()
    yield
    db_core.clear_runtime_state_cache()


def _dom(**kw):
    args = dict(age_s=1000.0, stilhed_s=10.0, still_alive=True,
                relay_open=False, levende_ude=False)
    args.update(kw)
    return _stuck_run_dom(**args)


# ── regressionen: den ventende tur ───────────────────────────────────────
def test_ventende_tur_paa_tredive_minutter_ryddes_ikke():
    # Præcis scenariet fra 22/11: kortet lever en time, turen venter pænt, og
    # heartbeat skriver last_activity_at hvert 10. sekund.
    ryd, grund = _dom(age_s=1800.0, stilhed_s=10.0, still_alive=True)

    assert ryd is False
    assert grund == ""


def test_ventende_tur_paa_naesten_en_time_ryddes_ikke():
    ryd, _ = _dom(age_s=3500.0, stilhed_s=10.0, still_alive=True)

    assert ryd is False


# ── zombie-værnet skal stadig virke ──────────────────────────────────────
def test_lang_stilhed_rydder_selv_naar_controlleren_findes():
    # Controlleren lever i hukommelsen, men generatoren har ikke rørt sig i 15
    # minutter → den ER hængt, og det skal vi stadig fange.
    ryd, grund = _dom(age_s=1000.0, stilhed_s=900.0, still_alive=True)

    assert ryd is True
    assert grund == "hung_too_long"


def test_ingen_controller_rydder_efter_fem_minutter():
    ryd, grund = _dom(age_s=400.0, stilhed_s=400.0, still_alive=False)

    assert ryd is True
    assert grund == "no_controller"


def test_ingen_controller_men_frisk_rydder_ikke():
    ryd, _ = _dom(age_s=100.0, stilhed_s=5.0, still_alive=False)

    assert ryd is False


def test_relay_aaben_rydder_aldrig():
    ryd, _ = _dom(age_s=9999.0, stilhed_s=9999.0, still_alive=False, relay_open=True)

    assert ryd is False


def test_levende_i_anden_proces_rydder_aldrig():
    ryd, _ = _dom(age_s=9999.0, stilhed_s=9999.0, still_alive=False,
                  levende_ude=True)

    assert ryd is False


# ── stilheds-beregningen ─────────────────────────────────────────────────
def test_uden_aktivitet_falder_den_tilbage_paa_alderen():
    # Ingen kontrol-state → vi ved intet om aktivitet, og så er alderen det
    # konservative svar (bevarer zombie-værnet).
    assert _stilhed_siden_aktivitet("ukendt-run", 1234.0) == 1234.0


def test_frisk_aktivitet_giver_naesten_nul_stilhed():
    nu = datetime.now(UTC).isoformat()
    _set_visible_run_control("r-frisk", {"last_activity_at": nu})

    stilhed = _stilhed_siden_aktivitet("r-frisk", 5000.0)

    assert stilhed < 60.0, f"forventede frisk aktivitet, fik {stilhed}s"


def test_gammel_aktivitet_giver_stor_stilhed():
    gammel = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    _set_visible_run_control("r-gammel", {"last_activity_at": gammel})

    stilhed = _stilhed_siden_aktivitet("r-gammel", 100.0)

    assert stilhed > 1100.0, f"forventede ~1200s stilhed, fik {stilhed}s"


def test_ulaesbar_tid_falder_tilbage_paa_alderen():
    _set_visible_run_control("r-broken", {"last_activity_at": "ikke-en-tid"})

    assert _stilhed_siden_aktivitet("r-broken", 777.0) == 777.0
