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
    booking_varsel,
    gentagelse_rammer_vindue,
    naeste_vindue_start,
    peak_badge,
    peak_state,
    tilfoej_booking_varsel,
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


# ── Booking-værnet (7/10-2026) ──────────────────────────────────────────────
#
# Badgen siger hvad der sker NU. Værnet her siger hvad der sker når et LØFTE
# falder — og det er to forskellige spørgsmål: bookingen kan ske i off-peak og
# lande midt i vinduet. Præcis det skete 7/10, da jeg bookede en vækning til
# 08:59 dansk uden at noget i svaret sagde det.


def test_booking_ind_i_vinduet_varsler():
    v = booking_varsel(_u(2026, 10, 5, 8))       # midt i 06-10-vinduet
    assert v is not None
    assert "MYLDRETIDEN" in v
    assert "08:00" in v and "12:00" in v, "vinduets danske rammer skal med"


def test_booking_i_natvinduet_varsler_ogsaa():
    """Natvinduet (01-04 UTC) er også myldretid — ikke kun dagvinduet."""
    v = booking_varsel(_u(2026, 10, 5, 2))
    assert v is not None
    assert "MYLDRETIDEN" in v


def test_booking_lige_foer_vinduet_varsler_om_at_arbejdet_loeper_ind():
    """En booking 10 min før vinduet åbner løber ind i det. Det skal siges."""
    v = booking_varsel(_u(2026, 10, 5, 5, 50))
    assert v is not None
    assert "LIGE FØR" in v
    assert "10 min" in v


def test_booking_i_off_peak_er_tavs():
    assert booking_varsel(_u(2026, 10, 5, 12)) is None      # efter dagvinduet
    assert booking_varsel(_u(2026, 10, 5, 4, 30)) is None   # mellem de to vinduer


def test_booking_i_weekenden_er_tavs():
    assert booking_varsel(_u(2026, 10, 3, 8)) is None
    assert booking_varsel(_u(2026, 10, 4, 8)) is None


def test_booking_graense_foelger_varsel_minutter():
    """Værnet og badgen skal være enige om hvornår vinduet åbner.

    1/10-2026 kostede to konstanter med samme navn (30 og 15) en runde. Testen
    regner grænsen ud af konstanten, så den ikke kan blive enig med sig selv om
    et tal ingen andre bruger.
    """
    from datetime import timedelta
    aabner = _u(2026, 10, 5, 6)
    assert booking_varsel(aabner - timedelta(minutes=VARSEL_MINUTTER)) is not None
    assert booking_varsel(aabner - timedelta(minutes=VARSEL_MINUTTER + 1)) is None


def test_gentagelse_der_er_hurtigere_end_vinduet_rammer_det():
    """Et vindue er 4 t = 240 min. Alt derunder kan ikke undgå myldretiden."""
    assert gentagelse_rammer_vindue(10) is True
    assert gentagelse_rammer_vindue(60) is True
    assert gentagelse_rammer_vindue(239) is True
    assert gentagelse_rammer_vindue(240) is False
    assert gentagelse_rammer_vindue(1440) is False, "én gang i døgnet kan ligge frit"


def test_gentagelse_med_nul_eller_negativ_er_ikke_et_ramm():
    assert gentagelse_rammer_vindue(0) is False
    assert gentagelse_rammer_vindue(-5) is False


def test_tilfoej_booking_varsel_roerer_kun_ok_svar():
    ok = tilfoej_booking_varsel({"status": "ok", "wakeup_id": "w1"}, _u(2026, 10, 5, 8))
    assert "peak_varsel" in ok
    assert ok["wakeup_id"] == "w1", "svaret skal ellers stå uberørt"

    fejl = tilfoej_booking_varsel({"status": "error", "error": "loft"}, _u(2026, 10, 5, 8))
    assert "peak_varsel" not in fejl, "et afvist forsøg fik aldrig et tidspunkt"


def test_tilfoej_booking_varsel_uden_varsel_tilfoejer_intet():
    svar = tilfoej_booking_varsel({"status": "ok"}, _u(2026, 10, 5, 12))
    assert "peak_varsel" not in svar


def test_tilfoej_booking_varsel_uden_tidspunkt_tier():
    """Mangler fire_at, ved jeg ikke hvornår bookingen falder — så sig intet.

    Ellers ville værnet varsle om NU, og det er en påstand svaret ikke bærer.
    """
    svar = tilfoej_booking_varsel({"status": "ok", "wakeup_id": "w2"}, None)
    assert "peak_varsel" not in svar
    tomt = tilfoej_booking_varsel({"status": "ok", "wakeup_id": "w3"}, "")
    assert "peak_varsel" not in tomt
