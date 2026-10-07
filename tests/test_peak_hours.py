"""Tests for core/services/peak_hours.py (30/9-2026).

Dækker de tre badge-tilstande, weekend-adfærd, og at vinduerne regnes i UTC —
så badgen ikke driver når DST skifter mellem dansk sommer- og vintertid.

Referencedatoer (weekday verificeret i testen selv):
  2026-10-05 = mandag · 2026-10-03 = lørdag · 2026-10-02 = fredag
"""

from datetime import UTC, datetime

import pytest

from core.services.peak_hours import (
    VARSEL_MINUTTER,
    aktuelt_vindue_slut,
    naeste_vindue_start,
    peak_badge,
    peak_state,
)


def _u(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def test_referencedatoer_er_som_antaget():
    """Hvis ugedagene driver, er resten af testene meningsløse."""
    assert _u(2026, 10, 5, 12).weekday() == 0, "2026-10-05 skal være mandag"
    assert _u(2026, 10, 3, 12).weekday() == 5, "2026-10-03 skal være lørdag"
    assert _u(2026, 10, 2, 12).weekday() == 4, "2026-10-02 skal være fredag"


def test_i_myldretid_giver_stor_badge():
    st = peak_state(_u(2026, 10, 5, 8))          # mandag 08:00 UTC = 10:00 dansk
    assert st["in_peak"] is True
    assert st["minutes_left"] == 120             # 08:00 → 10:00 UTC
    assert st["peak_starts_danish"] == "08:00"   # vinduets start, dansk (CEST)
    assert st["peak_ends_danish"] == "12:00"     # vinduets slut, dansk (CEST)
    badge = peak_badge(_u(2026, 10, 5, 8))
    assert badge is not None
    assert "MYLDRETID" in badge
    assert "08:00" in badge                       # dansk starttid
    assert "12:00" in badge                       # dansk sluttid
    assert "2 t" in badge                         # resterende varighed


def test_varsel_inden_vinduet():
    badge = peak_badge(_u(2026, 10, 5, 5, 45))   # 15 min før 06:00 UTC
    assert badge is not None
    assert "OM 15 MIN" in badge
    assert "08:00" in badge                       # vinduets START, dansk (CEST)


def test_off_peak_midt_paa_dagen_er_tavs():
    assert peak_badge(_u(2026, 10, 5, 12)) is None


def test_weekend_er_altid_tavs():
    assert peak_badge(_u(2026, 10, 3, 8)) is None
    assert peak_badge(_u(2026, 10, 4, 8)) is None


def test_naeste_vindue_springer_weekenden_over():
    naeste = naeste_vindue_start(_u(2026, 10, 2, 11))   # fredag efter formiddag
    assert naeste == _u(2026, 10, 5, 1), f"ventede mandag 01:00 UTC, fik {naeste}"


def test_aktuelt_vindue_slut_er_none_i_off_peak():
    assert aktuelt_vindue_slut(_u(2026, 10, 5, 12)) is None
    assert aktuelt_vindue_slut(_u(2026, 10, 5, 7)) == _u(2026, 10, 5, 10)


def test_dst_driver_ikke_visningen():
    """Samme UTC-time skal give forskellig dansk visning sommer vs. vinter."""
    sommer = peak_state(_u(2026, 10, 5, 8))      # CEST (UTC+2)
    vinter = peak_state(_u(2026, 1, 5, 8))       # CET  (UTC+1) — mandag
    assert sommer["in_peak"] is True
    assert vinter["in_peak"] is True, "08:00 UTC er i vinduet uanset DST"
    assert sommer["now_danish"] == "10:00"
    assert vinter["now_danish"] == "09:00"
    assert sommer["now_danish"] != vinter["now_danish"]


def test_vinduets_start_viser_rigtig_dansk_tid_baade_sommer_og_vinter():
    """Regression (30/9-2026): badgen hardcodede '08:00' som start.

    Vinduet åbner 06:00 UTC. Det er 08:00 dansk om sommeren og 07:00 om
    vinteren. Den hardcodede visning var altså rigtig halvdelen af året — og
    fejlen var usynlig i al den tid testene kun kørte sommerdatoer.
    """
    sommer = peak_badge(_u(2026, 10, 5, 8))      # CEST
    vinter = peak_badge(_u(2026, 1, 5, 8))       # CET — mandag 5. januar
    assert sommer is not None and vinter is not None
    assert "08:00" in sommer, "sommer: vinduet åbner 08:00 dansk"
    assert "07:00" in vinter, "vinter: vinduet åbner 07:00 dansk"
    assert "12:00" in sommer, "sommer: vinduet lukker 12:00 dansk"
    assert "11:00" in vinter, "vinter: vinduet lukker 11:00 dansk"


def test_naivt_tidspunkt_laeses_som_utc():
    """Et naivt datetime må ikke forskubbe vinduet — huset er faldet i den fælde før."""
    naiv = datetime(2026, 10, 5, 8)
    assert peak_state(naiv)["in_peak"] is True


def test_varsel_graense_er_praecis():
    """Ved præcis VARSEL_MINUTTER før skal varslet vise; ét minut før er tavst.

    1/10-2026: tidspunkterne var hardkodet til 05:30/05:29 — altså 30 minutter
    før vinduet åbner kl. 06 UTC. Da konstanten blev 15, målte testen ikke
    længere sin egen overskrift. Nu regnes graensen UD af konstanten, så den
    følger med næste gang tallet ændrer sig.
    """
    from datetime import timedelta
    aabner = _u(2026, 10, 5, 6)
    paa_graensen = aabner - timedelta(minutes=VARSEL_MINUTTER)
    assert peak_badge(paa_graensen) is not None
    assert peak_badge(paa_graensen - timedelta(minutes=1)) is None


@pytest.mark.parametrize("time_utc", [1, 2, 3, 6, 7, 8, 9])
def test_begge_vinduer_taelles(time_utc):
    """Begge MYLDRE_VINDUER-vinduer skal give badge — det halve ligger i det andet."""
    assert peak_badge(_u(2026, 10, 5, time_utc)) is not None


def test_varsel_minutter_er_dokumenteret_konstant():
    assert isinstance(VARSEL_MINUTTER, int)
    assert VARSEL_MINUTTER > 0
