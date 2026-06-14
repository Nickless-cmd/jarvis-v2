from __future__ import annotations


def test_empty_ruleset_default(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import get_ruleset

    assert get_ruleset("discord") == {}


def test_set_and_get_roundtrip(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import get_ruleset, set_ruleset

    rs = {"allowed_channels": ["general"], "quiet_hours": [22, 8]}
    set_ruleset("discord", rs)
    got = get_ruleset("discord")
    assert got["allowed_channels"] == ["general"]
    assert got["quiet_hours"] == [22, 8]


def test_unknown_fields_stripped(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import get_ruleset, set_ruleset

    set_ruleset("discord", {"allowed_channels": ["x"], "evil": "rm -rf", "role": "owner"})
    got = get_ruleset("discord")
    assert "evil" not in got and "role" not in got
    assert got["allowed_channels"] == ["x"]


def test_multiple_plugins_isolated(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import get_ruleset, list_rulesets, set_ruleset

    set_ruleset("discord", {"blocked_roles": ["støj"]})
    set_ruleset("telegram", {"rate_limits": {"main": 3}})
    assert get_ruleset("discord") == {"blocked_roles": ["støj"]}
    assert get_ruleset("telegram") == {"rate_limits": {"main": 3}}
    assert set(list_rulesets().keys()) == {"discord", "telegram"}


def test_stored_ruleset_drives_is_allowed(isolated_runtime) -> None:
    # Ende-til-ende: gemt regelsæt → plugin_ruleset.is_allowed håndhæver det.
    from core.services.plugin_ruleset import is_allowed
    from core.services.plugin_ruleset_store import get_ruleset, set_ruleset

    set_ruleset("discord", {"allowed_channels": ["general"]})
    rs = get_ruleset("discord")
    assert is_allowed({"channel": "general"}, rs)[0] is True
    assert is_allowed({"channel": "random"}, rs)[0] is False
