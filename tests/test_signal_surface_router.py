"""Tests for signal_surface_router — name resolution and error handling."""
from __future__ import annotations


def test_all_registered_names_resolve_to_callables():
    from apps.api.jarvis_api.services.signal_surface_router import (
        get_surface_names,
        resolve_surface,
    )
    for name in get_surface_names():
        fn = resolve_surface(name)
        assert callable(fn), f"{name} did not resolve to a callable"


def test_unknown_name_returns_error_with_valid_list():
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    result = read_surface("definitely_not_a_real_surface")
    assert "error" in result
    assert "valid" in result
    assert isinstance(result["valid"], list)
    assert len(result["valid"]) > 10


def test_known_surface_returns_dict():
    from apps.api.jarvis_api.services.signal_surface_router import read_surface
    result = read_surface("autonomy_pressure")
    assert isinstance(result, dict)
    assert "error" not in result


def test_list_all_returns_all_surfaces():
    from apps.api.jarvis_api.services.signal_surface_router import (
        get_surface_names,
        list_all_surfaces,
    )
    result = list_all_surfaces()
    assert isinstance(result, dict)
    assert len(result) == len(get_surface_names())
    for name in get_surface_names():
        assert name in result
