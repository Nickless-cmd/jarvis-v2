"""The Woman in the Red Dress — opmærksomheds-fælden.

Målt 13/11-2026: `build_red_dress_surface()` kaldte `_observe` ved hvert kald.
Matrix-ensemblet læser surfacen ved hver prompt-assembly — så prompt-bygget
fodrede den nerve-strøm karakteren selv kritiserer for at stjæle opmærksomheden.
Detektoren gjorde sig selv til den larmende nerve.

Den skal SE på volumen uden at BIDRAGE til den.
"""
from unittest import mock

from core.services import central_red_dress as rd


def test_laesning_observerer_ikke():
    with mock.patch("core.services.central_core.central") as c:
        rd.build_red_dress_surface()
    assert c.return_value.observe.call_count == 0, (
        "detektoren må ikke fodre den nerve-strøm den måler"
    )


def test_find_quiet_fire():
    """Alvorlig men lav volumen skal frem — det er den usete brand."""
    incidents = [{"id": 1, "nerve": "silent_x", "severity": "severe"}]
    with mock.patch("core.services.central_timeseries.nerves", return_value=[("c", "loud_y")]), \
            mock.patch("core.services.central_timeseries.recent", return_value=[0] * 150), \
            mock.patch("core.runtime.db_central_incidents.list_central_incidents",
                       return_value=incidents), \
            mock.patch("core.services.central_red_dress._observe"):
        out = rd.detect_attention_traps()
    assert any(f["nerve"] == "silent_x" for f in out["quiet_fires"])
    assert any(r["nerve"] == "loud_y" for r in out["red_dresses"])


def test_surface_baerer_en_aegte_laesning():
    """`felt` skal komme fra den målte fordeling, ikke fra en fast streng."""
    with mock.patch("core.services.central_timeseries.nerves", return_value=[("c", "loud_y")]), \
            mock.patch("core.services.central_timeseries.recent", return_value=[0] * 150), \
            mock.patch("core.runtime.db_central_incidents.list_central_incidents",
                       return_value=[{"id": 1, "nerve": "silent_x", "severity": "severe"}]), \
            mock.patch("core.services.central_red_dress._observe"):
        s = rd.build_red_dress_surface()
    assert "silent_x" in s.get("felt", "") or "loud_y" in s.get("felt", "")
