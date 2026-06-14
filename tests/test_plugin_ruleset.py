from __future__ import annotations

T0 = 1_700_000_000


def _ctx(channel="general", role="member", hour=12, now=T0):
    return {"channel": channel, "role": role, "hour": hour, "now": now}


def test_empty_ruleset_allows_all() -> None:
    from core.services.plugin_ruleset import is_allowed

    ok, _ = is_allowed(_ctx(), {})
    assert ok is True


def test_channel_allowlist_blocks_others() -> None:
    from core.services.plugin_ruleset import is_allowed

    rs = {"allowed_channels": ["general", "support"]}
    assert is_allowed(_ctx(channel="general"), rs)[0] is True
    ok, reason = is_allowed(_ctx(channel="random"), rs)
    assert ok is False and "random" in reason


def test_role_blocklist() -> None:
    from core.services.plugin_ruleset import is_allowed

    rs = {"blocked_roles": ["støj"]}
    assert is_allowed(_ctx(role="member"), rs)[0] is True
    ok, reason = is_allowed(_ctx(role="støj"), rs)
    assert ok is False and "støj" in reason


def test_quiet_hours_wraparound() -> None:
    from core.services.plugin_ruleset import is_allowed

    rs = {"quiet_hours": [22, 8]}
    assert is_allowed(_ctx(hour=23), rs)[0] is False   # nat
    assert is_allowed(_ctx(hour=2), rs)[0] is False    # tidlig morgen
    assert is_allowed(_ctx(hour=12), rs)[0] is True    # dag


def test_rate_limit_per_channel() -> None:
    from core.services.plugin_ruleset import is_allowed

    rs = {"rate_limits": {"random": 3}}
    for i in range(3):
        assert is_allowed(_ctx(channel="random", now=T0 + i), rs)[0] is True
    # 4. svar inden for timen → blokeret
    ok, reason = is_allowed(_ctx(channel="random", now=T0 + 4), rs)
    assert ok is False and "rate" in reason.lower()
    # Anden kanal upåvirket
    assert is_allowed(_ctx(channel="general", now=T0 + 4), rs)[0] is True
    # Efter timen → tilladt igen
    assert is_allowed(_ctx(channel="random", now=T0 + 3700), rs)[0] is True


def test_owner_override_cannot_bypass_ruleset() -> None:
    from core.services.plugin_ruleset import is_allowed

    rs = {"allowed_channels": ["general"]}
    # Selv med aktiv owner-override er plugin-regelsæt et hardblock
    ok, _ = is_allowed(_ctx(channel="random"), rs, override_active=True)
    assert ok is False
