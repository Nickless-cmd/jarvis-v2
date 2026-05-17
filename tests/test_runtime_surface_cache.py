from core.services.runtime_surface_cache import (
    get_cached_runtime_surface,
    get_timed_runtime_surface,
    peek_cached_runtime_surface,
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


def test_runtime_surface_cache_can_peek_existing_value() -> None:
    with runtime_surface_cache():
        cached = get_cached_runtime_surface("demo", lambda: {"ok": True})
        peeked = peek_cached_runtime_surface("demo")

    assert peeked == cached


def test_runtime_surface_cache_peek_returns_none_when_missing() -> None:
    with runtime_surface_cache():
        assert peek_cached_runtime_surface("missing") is None


def test_timed_runtime_surface_reuses_value_across_calls_within_ttl() -> None:
    calls = {"count": 0}

    def builder() -> dict[str, object]:
        calls["count"] += 1
        return {"count": calls["count"]}

    first = get_timed_runtime_surface("timed-demo", 60.0, builder)
    second = get_timed_runtime_surface("timed-demo", 60.0, builder)

    assert first == {"count": 1}
    assert second == {"count": 1}
    assert calls["count"] == 1


def test_timed_runtime_surface_returns_same_object_on_hit() -> None:
    """Cache-hits skal returnere samme objekt (ingen per-read deepcopy).

    Surface'en er 140KB+ og deepcopy ved hver read koster ~1.6ms/call —
    målt til ~20% af runtime-worker CPU under load. Kontrakten er nu:
    callers skal behandle surface som read-only. Audit (2026-05-17):
    alle produktions-call-sites læser kun, muterer ikke.
    """
    def builder() -> dict[str, object]:
        return {"nested": {"value": 42}, "list": [1, 2, 3]}

    first = get_timed_runtime_surface("readonly-demo", 60.0, builder)
    second = get_timed_runtime_surface("readonly-demo", 60.0, builder)

    assert first is second, "cache hit skal returnere SAMME objekt, ikke deepcopy"
    assert first["nested"] is second["nested"]


def test_timed_runtime_surface_isolates_builder_from_external_mutation() -> None:
    """Builder-returværdi gemmes som deepcopy så ekstern mutation af
    builder's lokale state ikke poisoner cachen."""
    source = {"live": True, "items": [1, 2]}

    def builder() -> dict[str, object]:
        return source  # builder returnerer ref til ekstern state

    cached = get_timed_runtime_surface("isolation-demo", 60.0, builder)
    source["live"] = False
    source["items"].append(99)

    # Cachen er isoleret fra builder's eksterne mutation
    assert cached["live"] is True
    assert cached["items"] == [1, 2]
