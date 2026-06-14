"""Tests for quota_store (§21)."""
from __future__ import annotations

import pytest


@pytest.fixture
def _users(isolated_runtime, tmp_path, monkeypatch):
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    from core.identity.users import add_user
    add_user(discord_id="d-bjorn", name="Bjørn", role="owner", workspace="bjorn")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")
    return tmp_path


def test_tier_resolution(_users) -> None:
    from core.services.quota_store import get_tier
    assert get_tier("d-bjorn") == "owner"
    assert get_tier("d-mikkel") == "plus"      # member → plus
    assert get_tier("ukendt") == "free"
    assert get_tier("") == "owner"             # ubundet = owner


def test_owner_unlimited(_users) -> None:
    from core.services.quota_store import check_quota, consume_quota
    s = check_quota("d-bjorn", "code")
    assert s["allowed"] is True and s["limit"] is None
    for _ in range(5):
        assert consume_quota("d-bjorn", "code", 100)["consumed"] is True


def test_free_chat_quota(_users) -> None:
    from core.services.quota_store import check_quota, consume_quota
    # free chat = 20/dag
    s = check_quota("gæst", "chat")
    assert s["tier"] == "free" and s["limit"] == 20
    for _ in range(20):
        assert consume_quota("gæst", "chat")["consumed"] is True
    blocked = consume_quota("gæst", "chat")
    assert blocked["consumed"] is False and blocked["allowed"] is False


def test_free_no_code_access(_users) -> None:
    from core.services.quota_store import check_quota
    s = check_quota("gæst", "code")          # free code = 0
    assert s["allowed"] is False and s["limit"] == 0


def test_warn_at_80pct(_users) -> None:
    from core.services.quota_store import consume_quota, check_quota
    # plus code = 180 min; warn ved 144
    consume_quota("d-mikkel", "code", 144)
    assert check_quota("d-mikkel", "code")["warn"] is True
    assert check_quota("d-mikkel", "code")["allowed"] is True


def test_plus_agent_quota(_users) -> None:
    from core.services.quota_store import consume_quota
    # plus agent = 2/dag
    assert consume_quota("d-mikkel", "agent")["consumed"] is True
    assert consume_quota("d-mikkel", "agent")["consumed"] is True
    assert consume_quota("d-mikkel", "agent")["consumed"] is False
