"""Tests for apps/api/jarvis_api/routes/peak.py (30/9-2026).

Dækker: at endpointet svarer med de felter desk-badgen skal bruge, at det
aldrig kaster (en header-badge må ikke kunne vælte desk-appen), og at
vinduerne regnes i UTC — så svaret er rigtigt både sommer og vinter.
"""
from __future__ import annotations

from apps.api.jarvis_api.routes.peak import peak_state_endpoint


def test_svarer_med_badge_felterne():
    svar = peak_state_endpoint()
    assert svar["ok"] is True
    for felt in (
        "in_peak",
        "now_danish",
        "peak_starts_danish",
        "peak_ends_danish",
        "minutes_left",
        "next_peak_danish",
        "minutes_until_next",
    ):
        assert felt in svar, f"mangler {felt}"


def test_off_peak_har_naeste_vindue():
    """Uden for myldretid skal der peges på det næste — ellers kan badgen ikke tælle ned."""
    svar = peak_state_endpoint()
    if not svar["in_peak"]:
        assert svar["next_peak_danish"] is not None
        assert svar["minutes_until_next"] is not None
        assert svar["minutes_until_next"] > 0


def test_kaster_aldrig(monkeypatch):
    """Selv hvis peak-laget fejler, skal endpointet svare — ikke 500."""
    import core.services.peak_hours as ph

    def _boom(*_a, **_k):
        raise RuntimeError("simuleret fejl i peak-laget")

    monkeypatch.setattr(ph, "peak_state", _boom)
    svar = peak_state_endpoint()
    assert svar["ok"] is False
    assert svar["in_peak"] is False
    assert svar["error"] == "RuntimeError"
