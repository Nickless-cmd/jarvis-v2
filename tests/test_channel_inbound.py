from __future__ import annotations


def test_ruleset_blocks_disallowed_channel(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import set_ruleset
    from core.services.channel_inbound import route_inbound

    set_ruleset("discord-local", {"allowed_channels": ["general"]})
    blocked = route_inbound(plugin_id="discord-local", channel="random", text="hej")
    assert blocked["allowed"] is False
    allowed = route_inbound(plugin_id="discord-local", channel="general", text="hej")
    assert allowed["allowed"] is True


def test_blocked_role_rejected(isolated_runtime) -> None:
    from core.services.plugin_ruleset_store import set_ruleset
    from core.services.channel_inbound import route_inbound

    set_ruleset("discord-local", {"blocked_roles": ["støj"]})
    r = route_inbound(plugin_id="discord-local", channel="general", author_role="støj", text="x")
    assert r["allowed"] is False


def test_no_ruleset_allows(isolated_runtime) -> None:
    from core.services.channel_inbound import route_inbound

    r = route_inbound(plugin_id="discord-local", channel="anything", text="x")
    assert r["allowed"] is True


def test_builtin_registration_idempotent(isolated_runtime) -> None:
    from core.plugins.base_plugin import available_plugins, clear_registry
    from core.services.channel_inbound import register_builtin_channel_plugins
    import core.services.channel_inbound as ci

    clear_registry()
    ci._BUILTINS_REGISTERED = False
    register_builtin_channel_plugins()
    register_builtin_channel_plugins()  # to gange → ingen dublet
    ids = [m.plugin_id for m in available_plugins()]
    assert ids.count("discord-local") == 1
    clear_registry()
    ci._BUILTINS_REGISTERED = False


# --- §18.9 mode-switch ---

def test_resolve_mode_default_chat() -> None:
    from core.services.channel_inbound import resolve_inbound_mode
    assert resolve_inbound_mode().get("mode") == "chat"
    assert resolve_inbound_mode("bogus", author_role="owner")["mode"] == "chat"


def test_resolve_mode_code_requires_owner_or_override() -> None:
    from core.services.channel_inbound import resolve_inbound_mode
    assert resolve_inbound_mode("code", author_role="member")["downgraded"] is True
    assert resolve_inbound_mode("code", author_role="member")["mode"] == "chat"
    assert resolve_inbound_mode("code", author_role="owner")["mode"] == "code"
    assert resolve_inbound_mode("code", author_role="member", override_active=True)["mode"] == "code"


def test_route_inbound_includes_resolved_mode(isolated_runtime) -> None:
    from core.services.channel_inbound import route_inbound
    # member der beder om code → nedgraderet til chat i route-resultatet
    r = route_inbound(plugin_id="discord-local", channel="general",
                      author_role="member", text="hej", mode="code")
    assert r["mode"] == "chat" and r["mode_downgraded"] is True
    # owner code → bevares
    r2 = route_inbound(plugin_id="discord-local", channel="general",
                       author_role="owner", text="kør", mode="code")
    assert r2["mode"] == "code" and r2["mode_downgraded"] is False


def test_chat_quota_blocks_free_over_limit(isolated_runtime, tmp_path, monkeypatch) -> None:
    # §21.7: gratis bruger over chat-kvote → blokeret med upgrade-besked.
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    from core.services.channel_inbound import route_inbound
    # ukendt bruger = free tier, chat-kvote 20/dag
    for _ in range(20):
        r = route_inbound(plugin_id="discord-local", channel="g", author_role="member",
                          author_user_id="gæst-x", text="hej")
        assert r["allowed"] is True
    blocked = route_inbound(plugin_id="discord-local", channel="g", author_role="member",
                            author_user_id="gæst-x", text="hej")
    assert blocked["allowed"] is False and blocked["reason"] == "quota_exceeded"
    assert "Opgradér" in blocked["quota"]["message"]


def test_chat_quota_owner_unlimited(isolated_runtime) -> None:
    from core.services.channel_inbound import route_inbound
    # ubundet author_user_id = owner = ubegrænset
    for _ in range(30):
        assert route_inbound(plugin_id="discord-local", channel="g",
                             author_role="owner", author_user_id="", text="x")["allowed"] is True
