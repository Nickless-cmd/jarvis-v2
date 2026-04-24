"""Tests for the TTL-based cognitive state cache in cognitive_state_assembly."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC


def test_cache_roundtrip_and_invalidation(isolated_runtime) -> None:
    from core.services import cognitive_state_assembly as csa

    csa.invalidate_cognitive_state_cache()

    csa._set_cached_state("visible_full", "FRESH STATE", ["src_a"])
    assert csa._get_cached_state("visible_full") == "FRESH STATE"

    csa.invalidate_cognitive_state_cache()
    assert csa._get_cached_state("visible_full") is None


def test_cache_ttl_reads_settings_field(isolated_runtime) -> None:
    """The TTL helper must read the real settings field (not a typoed one)."""
    from core.services import cognitive_state_assembly as csa
    from core.runtime.settings import load_settings

    s = load_settings()
    ttl = csa._cache_ttl_seconds()
    assert ttl == float(s.cognitive_state_cache_ttl)


def _fake_settings(enabled: bool, ttl: int):
    from core.runtime.settings import RuntimeSettings

    s = RuntimeSettings()
    s.cognitive_state_cache_enabled = enabled
    s.cognitive_state_cache_ttl = ttl
    return s


def test_cache_enabled_respects_toggle(isolated_runtime, monkeypatch) -> None:
    import core.runtime.settings as settings_mod
    from core.services import cognitive_state_assembly as csa

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _fake_settings(True, 60))
    assert csa._cache_enabled() is True

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _fake_settings(False, 60))
    assert csa._cache_enabled() is False


def test_cache_ttl_zero_disables_cache(isolated_runtime, monkeypatch) -> None:
    import core.runtime.settings as settings_mod
    from core.services import cognitive_state_assembly as csa

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _fake_settings(True, 0))
    assert csa._cache_enabled() is False

    csa.invalidate_cognitive_state_cache()
    csa._set_cached_state("visible_full", "SHOULD NOT STICK", ["src"])
    assert csa._get_cached_state("visible_full") is None


def test_cache_expires_after_ttl_when_snapshot_changes(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import cognitive_state_assembly as csa

    csa.invalidate_cognitive_state_cache()
    csa._set_cached_state("visible_full", "OLD", ["src"])

    entry = csa._COHERENT_CACHE["visible_full"]
    old_time = (datetime.now(UTC) - timedelta(seconds=500)).isoformat().replace(
        "+00:00", "Z"
    )
    entry["cached_at"] = old_time
    entry["invalidation_snapshot"] = {"pv_version": "v-old"}

    monkeypatch.setattr(
        csa, "_build_invalidation_snapshot", lambda: {"pv_version": "v-new"}
    )

    assert csa._get_cached_state("visible_full") is None


def test_cache_status_reports_entries(isolated_runtime) -> None:
    from core.services import cognitive_state_assembly as csa

    csa.invalidate_cognitive_state_cache()
    csa._set_cached_state("visible_full", "payload", ["source_a"])

    status = csa.get_cognitive_state_cache_status()
    assert status["enabled"] is True
    assert status["ttl_seconds"] > 0
    assert "visible_full" in status["entries"]
    entry = status["entries"]["visible_full"]
    assert entry["chars"] == len("payload")
    assert entry["sources"] == ["source_a"]
