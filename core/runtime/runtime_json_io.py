"""Safe read/merge/write helpers for runtime.json.

The old write path (RuntimeSettings.to_dict → write_text) was technically
key-preserving via `extra`, but had two weaknesses:
  1. Not atomic — a crash mid-write leaves runtime.json corrupt/truncated.
     Next load_settings falls back to defaults for typed fields, and the
     NEXT save then persists those defaults permanently.
  2. All writes go through the RuntimeSettings dataclass — any field drift
     between Python and JSON (e.g. a new typed field added to the dataclass
     after existing runtime.json was written) risks resetting values.

This module bypasses the dataclass entirely for writes: reads the raw dict,
merges updates on top, writes atomically via tmp+rename, and keeps a
rolling set of timestamped backups.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from core.runtime.config import CONFIG_DIR, SETTINGS_FILE

_BACKUP_PREFIX = "runtime.json.autobackup-"
_MAX_BACKUPS = 10


def read_runtime_raw() -> dict[str, Any]:
    """Return current runtime.json as a plain dict. Empty dict if file missing."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _prune_old_backups() -> None:
    try:
        backups = sorted(
            CONFIG_DIR.glob(f"{_BACKUP_PREFIX}*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[_MAX_BACKUPS:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass


def _write_backup(payload: bytes) -> None:
    if not payload:
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = CONFIG_DIR / f"{_BACKUP_PREFIX}{stamp}"
    try:
        backup_path.write_bytes(payload)
    except Exception:
        return
    _prune_old_backups()


def write_runtime_merged(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge `updates` into runtime.json, writing atomically.
    Takes a timestamped backup of the existing file first. Returns the
    full merged dict that was written.
    """
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_bytes = b""
    if SETTINGS_FILE.exists():
        try:
            existing_bytes = SETTINGS_FILE.read_bytes()
        except Exception:
            existing_bytes = b""
    _write_backup(existing_bytes)

    current = read_runtime_raw()
    merged = {**current, **updates}

    tmp_path = SETTINGS_FILE.with_suffix(SETTINGS_FILE.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(merged, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_path, SETTINGS_FILE)
    return merged
