"""Vagt: `approval_feedback_stats_by_tool` skal kunne kaldes.

MÅLT 7/11-2026: funktionen brugte `timedelta` på linje 713, men modulet
importerede kun `UTC, datetime`. Den kastede derfor `NameError` HVER gang
den blev kaldt — og den var den eneste funktion i filen med fejlen.

Konsekvensen var ikke en manglende test men en død flade:
`tool_intent_approval_runtime.build_approval_feedback_surface()` kalder
funktionen og fejlede derfor altid. Fladen så ud som om den fandtes
(`build_*_surface` var der), men enhver læser fik en exception i stedet
for godkendelses-feedback-statistik.

Testen kalder funktionen direkte. Det er nok: fejlen var en manglende
import, ikke en logisk fejl, så ethvert kald beviser at navnet er bundet.
"""
from __future__ import annotations

import pytest


def test_stats_funktionen_kan_kaldes(isolated_runtime) -> None:
    """Kaldet må ikke kaste — den gjorde før, hver gang."""
    from core.runtime.db_capability_approval import approval_feedback_stats_by_tool

    resultat = approval_feedback_stats_by_tool(days=7)
    assert isinstance(resultat, list)


def test_stats_funktionen_taaler_days_argumentet(isolated_runtime) -> None:
    """`days` bruges i cutoff-regnestykket — det er der `timedelta` indgår."""
    from core.runtime.db_capability_approval import approval_feedback_stats_by_tool

    for dage in (1, 7, 30):
        assert isinstance(approval_feedback_stats_by_tool(days=dage), list)


def test_fladen_der_kalder_den_leverer(isolated_runtime) -> None:
    """Den ægte kobling: fladen må ikke arve funktionens fejl."""
    from core.services.tool_intent_approval_runtime import (
        build_approval_feedback_surface,
    )

    flade = build_approval_feedback_surface()
    assert isinstance(flade, dict)
    assert flade, "fladen returnerede en tom dict — så svarer den ikke"
    assert "stats_7d" in flade, (
        "stats_7d mangler — det er netop det felt der kaldte den brudte funktion"
    )
    assert isinstance(flade["stats_7d"], list)


def test_stats_taeller_kun_inden_for_vinduet(isolated_runtime) -> None:
    """Cutoff'en skal faktisk filtrere — ellers er `days` kosmetik.

    Skriver to poster: én nu, én 40 dage gammel. Med `days=7` må kun den
    friske tælles. Det beviser at `timedelta`-regnestykket virker, ikke
    bare at navnet er bundet.
    """
    from datetime import UTC, datetime, timedelta

    from core.runtime.db_capability_approval import (
        approval_feedback_stats_by_tool,
        insert_approval_feedback,
    )

    nu = datetime.now(UTC)
    gammel = nu - timedelta(days=40)

    insert_approval_feedback(
        recorded_at=nu.isoformat(),
        intent_key="vagt-frisk",
        approval_state="approved",
        approval_source="test",
        tool_name="vagt_vaerktoej",
    )
    insert_approval_feedback(
        recorded_at=gammel.isoformat(),
        intent_key="vagt-gammel",
        approval_state="approved",
        approval_source="test",
        tool_name="vagt_vaerktoej",
    )

    stats = approval_feedback_stats_by_tool(days=7)
    raekke = next((r for r in stats if r["tool_name"] == "vagt_vaerktoej"), None)
    assert raekke is not None, "den friske post blev slet ikke talt"
    assert raekke["approved_count"] == 1, (
        f"vinduet på 7 dage talte {raekke['approved_count']} — den 40 dage "
        f"gamle post slap igennem, så cutoff'en virker ikke"
    )
