"""Discord config — load/save ~/.jarvis-v2/config/discord.json."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from core.runtime.config import JARVIS_HOME

_CONFIG_PATH = Path(JARVIS_HOME) / "config" / "discord.json"

_REQUIRED_KEYS = {"bot_token", "guild_id", "allowed_channel_ids", "owner_discord_id"}


def load_discord_config() -> dict | None:
    """Return config dict or None if missing/invalid."""
    try:
        if not _CONFIG_PATH.exists():
            return None
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if not _REQUIRED_KEYS.issubset(data):
            return None
        return data
    except Exception:
        return None


def save_discord_config(config: dict) -> None:
    """Write config with chmod 600. Creates parent dir if needed."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(_CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)


def is_discord_configured() -> bool:
    """Return True if config exists and has all required keys."""
    return load_discord_config() is not None
