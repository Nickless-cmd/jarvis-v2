"""Cartographer'ens dark-edge-måling (rettet 7/11-2026).

To fejl blev målt og rettet samme dag:

1. **Markøren var for snæver.** `_SURFACE_RE` krævede `build_*_surface`, så en
   offentlig `identity_sketch_surface()` blev ikke set — og `identity_sketch`
   stod som systemets #1 dark edge (score 100) på en teknikalitet. Målt: den er
   registreret dynamisk i `cluster_daemon.py:1365`, altså nåbar.

2. **Tallet var klippet, men rapporteret som en total.** `_rank_dark_edges`
   returnerede `ranked[:80]`, og `summary["dark_edges"]` blev læst som det
   faktiske antal. Det uklippede tal var **382** — problemet blev underdrevet
   4,8× i hver rapport der brugte tallet.

Testene her fejler hvis nogen af de to skrider tilbage.
"""

from __future__ import annotations


def test_surface_markoer_ser_offentlig_surface() -> None:
    """En offentlig `*_surface` er en flade — også når den ikke hedder `build_*`."""
    from core.services.system_cartographer import _SURFACE_RE

    fundet = _SURFACE_RE.findall(
        "def identity_sketch_surface() -> dict:\n"
        "def build_identity_composer_surface() -> dict:\n"
    )

    assert "identity_sketch_surface" in fundet
    assert "build_identity_composer_surface" in fundet


def test_surface_markoer_ser_ikke_private_hjaelpere() -> None:
    """Private hjælpere er ikke flader — de må ikke tælle som observabilitet."""
    from core.services.system_cartographer import _SURFACE_RE

    assert _SURFACE_RE.findall("def _embodied_state_surface() -> dict:\n") == []


def test_dark_edges_total_er_adskilt_fra_vist_antal() -> None:
    """Total og vist antal skal være to tal — ellers skjuler loftet problemets størrelse."""
    from core.services.system_cartographer import build_system_cartographer_surface

    surface = build_system_cartographer_surface()
    summary = surface["summary"]

    assert "dark_edges_shown" in summary, "det viste antal skal stå eksplicit"
    assert summary["dark_edges"] >= summary["dark_edges_shown"]
    assert len(surface["darkEdges"]) == summary["dark_edges_shown"]
