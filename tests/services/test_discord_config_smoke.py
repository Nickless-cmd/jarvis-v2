"""Smoke test for core.services.discord_config.

Saving and loading the Discord config should preserve the required keys and
make the configuration read as available.
"""

from core.services import discord_config


def test_save_and_load_discord_config_roundtrip(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "discord.json"
    monkeypatch.setattr(discord_config, "_CONFIG_PATH", config_path)

    config = {
        "bot_token": "token",
        "guild_id": "guild",
        "allowed_channel_ids": ["123"],
        "owner_discord_id": "owner",
    }
    discord_config.save_discord_config(config)

    assert discord_config.load_discord_config() == config
    assert discord_config.is_discord_configured() is True
