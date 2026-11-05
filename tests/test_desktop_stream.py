"""Tests for /ws/desktop-ruten — at den faktisk er monteret og kræver ejer.

Enhedstestene for selve X-sessionen ligger i tests/test_x_session.py.
"""
from __future__ import annotations


def test_router_har_desktop_ruten():
    """Ruten skal være registreret, ellers er panelet dødt uanset koden."""
    from apps.api.jarvis_api.routes.desktop_stream import router

    stier = {getattr(r, "path", "") for r in router.routes}
    assert "/ws/desktop" in stier


def test_routeren_er_monteret_i_app():
    """Appen skal inkludere routeren — import alene gør ingenting."""
    import inspect

    from apps.api.jarvis_api import app as app_mod

    kilde = inspect.getsource(app_mod)
    assert "desktop_stream_router" in kilde
    assert "include_router(desktop_stream_router)" in kilde
