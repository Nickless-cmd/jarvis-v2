import json
from pathlib import Path

from core.runtime.config import (
    AUTH_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    JARVIS_HOME,
    LOG_DIR,
    SESSIONS_DIR,
    SETTINGS_FILE,
    STATE_DIR,
    WORKSPACES_DIR,
)
from core.runtime.settings import RuntimeSettings

RUNTIME_DIRS = [
    JARVIS_HOME,
    CONFIG_DIR,
    STATE_DIR,
    LOG_DIR,
    CACHE_DIR,
    SESSIONS_DIR,
    AUTH_DIR,
    WORKSPACES_DIR,
]

def ensure_runtime_dirs() -> None:
    for path in RUNTIME_DIRS:
        Path(path).mkdir(parents=True, exist_ok=True)
    ensure_settings_file()


def ensure_settings_file() -> None:
    if SETTINGS_FILE.exists():
        return

    SETTINGS_FILE.write_text(
        json.dumps(RuntimeSettings().to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
