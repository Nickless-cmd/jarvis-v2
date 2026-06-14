from __future__ import annotations

import json

import pytest


@pytest.fixture
def _isolated_users(tmp_path, monkeypatch):
    """Isolér users.json til en tmp CONFIG_DIR."""
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    yield tmp_path


def test_new_user_has_empty_totp_and_app_id(_isolated_users) -> None:
    from core.identity.users import add_user

    u = add_user(discord_id="d1", name="Bjørn", role="owner")
    assert u is not None
    assert u.app_id == ""
    assert u.totp_seed == ""


def test_set_and_get_totp_seed_persists(_isolated_users) -> None:
    from core.identity.users import add_user, get_totp_seed, set_totp_seed

    add_user(discord_id="d1", name="Bjørn", role="owner")
    assert set_totp_seed(discord_id="d1", seed="JBSWY3DPEHPK3PXP") is True
    # Genindlæst fra disk
    assert get_totp_seed(discord_id="d1") == "JBSWY3DPEHPK3PXP"


def test_set_app_id_persists(_isolated_users) -> None:
    from core.identity.users import add_user, find_user_by_discord_id, set_app_id

    add_user(discord_id="d1", name="Bjørn", role="owner")
    assert set_app_id(discord_id="d1", app_id="uuid-abc-123") is True
    assert find_user_by_discord_id("d1").app_id == "uuid-abc-123"


def test_backward_compat_old_record_loads(_isolated_users) -> None:
    # Gammelt record uden app_id/totp_seed skal stadig loade
    from core.identity.users import find_user_by_discord_id
    (_isolated_users / "users.json").write_text(
        json.dumps({"users": [{
            "discord_id": "d9", "name": "Mikkel", "role": "member",
            "workspace": "mikkel", "created_at": "2026-01-01T00:00:00Z",
        }]}),
        encoding="utf-8",
    )
    u = find_user_by_discord_id("d9")
    assert u is not None
    assert u.app_id == "" and u.totp_seed == ""


def test_set_totp_unknown_user_returns_false(_isolated_users) -> None:
    from core.identity.users import set_totp_seed

    assert set_totp_seed(discord_id="nope", seed="x") is False
