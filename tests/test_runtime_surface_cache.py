from apps.api.jarvis_api.services.runtime_surface_cache import (
    get_cached_runtime_surface,
    runtime_surface_cache,
)


def test_runtime_surface_cache_reuses_builder_within_context() -> None:
    calls = {"count": 0}

    def builder() -> dict[str, object]:
        calls["count"] += 1
        return {"ok": True}

    with runtime_surface_cache():
        first = get_cached_runtime_surface("demo", builder)
        second = get_cached_runtime_surface("demo", builder)

    assert first == {"ok": True}
    assert second == first
    assert calls["count"] == 1


def test_runtime_surface_cache_resets_after_context() -> None:
    calls = {"count": 0}

    def builder() -> dict[str, object]:
        calls["count"] += 1
        return {"count": calls["count"]}

    with runtime_surface_cache():
        first = get_cached_runtime_surface("demo", builder)
    with runtime_surface_cache():
        second = get_cached_runtime_surface("demo", builder)

    assert first == {"count": 1}
    assert second == {"count": 2}
