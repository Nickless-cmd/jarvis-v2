from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.runtime.config import CONFIG_DIR


@dataclass(slots=True)
class RuntimeSettings:
    app_name: str = "jarvis-v2"
    environment: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = f"sqlite:///{CONFIG_DIR.parent / 'state' / 'jarvis.db'}"
    primary_model_lane: str = "primary"
    cheap_model_lane: str = "cheap"


def load_settings() -> RuntimeSettings:
    # Phase 1: single authority in code/defaults, later config.yaml loader plugs in here.
    return RuntimeSettings()
