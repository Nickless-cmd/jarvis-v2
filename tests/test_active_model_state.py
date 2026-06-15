"""Tests for active_model_state (per-run visible-model override-tracking)."""
from __future__ import annotations


def test_set_and_get_roundtrip(isolated_runtime) -> None:
    from core.services.active_model_state import set_active_visible_target, get_active_visible_target
    set_active_visible_target("u-bjorn", "ollama", "glm-5.1:cloud")
    rec = get_active_visible_target("u-bjorn")
    assert rec is not None
    assert rec["provider"] == "ollama"
    assert rec["model"] == "glm-5.1:cloud"


def test_per_user_isolation(isolated_runtime) -> None:
    from core.services.active_model_state import set_active_visible_target, get_active_visible_target
    set_active_visible_target("u-bjorn", "ollama", "glm-5.1:cloud")
    set_active_visible_target("u-mikkel", "deepseek", "deepseek-v4-flash")
    assert get_active_visible_target("u-bjorn")["model"] == "glm-5.1:cloud"
    assert get_active_visible_target("u-mikkel")["model"] == "deepseek-v4-flash"


def test_none_uid_maps_to_owner(isolated_runtime) -> None:
    from core.services.active_model_state import set_active_visible_target, get_active_visible_target
    set_active_visible_target(None, "ollama", "glm-5.1:cloud")
    assert get_active_visible_target(None)["provider"] == "ollama"
    assert get_active_visible_target("owner")["provider"] == "ollama"


def test_unknown_user_returns_none(isolated_runtime) -> None:
    from core.services.active_model_state import get_active_visible_target
    assert get_active_visible_target("nobody") is None


def test_latest_overwrites(isolated_runtime) -> None:
    from core.services.active_model_state import set_active_visible_target, get_active_visible_target
    set_active_visible_target("u", "deepseek", "deepseek-v4-flash")
    set_active_visible_target("u", "ollama", "glm-5.1:cloud")
    assert get_active_visible_target("u")["model"] == "glm-5.1:cloud"
