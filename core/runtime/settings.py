from __future__ import annotations

import json
from dataclasses import dataclass

from core.runtime.config import CONFIG_DIR, SETTINGS_FILE


@dataclass(slots=True)
class RuntimeSettings:
    app_name: str = "jarvis-v2"
    environment: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = f"sqlite:///{CONFIG_DIR.parent / 'state' / 'jarvis.db'}"
    primary_model_lane: str = "primary"
    cheap_model_lane: str = "cheap"

    def to_dict(self) -> dict[str, str | int]:
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "host": self.host,
            "port": self.port,
            "database_url": self.database_url,
            "primary_model_lane": self.primary_model_lane,
            "cheap_model_lane": self.cheap_model_lane,
        }


def load_settings() -> RuntimeSettings:
    defaults = RuntimeSettings()
    if not SETTINGS_FILE.exists():
        return defaults

    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return RuntimeSettings(
        app_name=str(data.get("app_name", defaults.app_name)),
        environment=str(data.get("environment", defaults.environment)),
        host=str(data.get("host", defaults.host)),
        port=int(data.get("port", defaults.port)),
        database_url=str(data.get("database_url", defaults.database_url)),
        primary_model_lane=str(
            data.get("primary_model_lane", defaults.primary_model_lane)
        ),
        cheap_model_lane=str(data.get("cheap_model_lane", defaults.cheap_model_lane)),
    )
