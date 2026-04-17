from __future__ import annotations

import json
import os
from pathlib import Path


SETTINGS_FILE = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
API_KEYS_BACKUP_FILE = Path.home() / ".jarvis-v2" / "config" / "api_keys.backup.json"


def read_runtime_key(key: str, env_override: str | None = None) -> str:
    """
    Read a key from ~/.jarvis-v2/config/runtime.json.

    If env_override is provided and the environment variable is set to a
    non-empty value, that value wins. Otherwise the key is read from runtime.json.
    Raises RuntimeError with a human-readable message when the key is missing.
    """
    if env_override:
        env_value = os.environ.get(env_override)
        if env_value:
            return env_value

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"{key} mangler i {SETTINGS_FILE}. "
            f"Tilfoej den som top-level key - se {API_KEYS_BACKUP_FILE} for reference."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Kunne ikke laese gyldig JSON fra {SETTINGS_FILE}. "
            f"Ret filen og tilfoej {key} som top-level key."
        ) from exc

    value = data.get(key)
    if value:
        return str(value)

    raise RuntimeError(
        f"{key} mangler i {SETTINGS_FILE}. "
        f"Tilfoej den som top-level key - se {API_KEYS_BACKUP_FILE} for reference."
    )
