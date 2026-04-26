"""Tiny JSON-file state store for module-globals that must survive restart.

Pattern matches the one used by ``calm_anchor`` and ``valence_trajectory``
(commit 5ca8488): module loads its globals from disk on import, saves them
back after every mutation. Files live under ``~/.jarvis-v2/state/`` and are
small (<100 KB worst case), so atomic write-then-rename is fine.

Why exists: prior to this helper every daemon that fixed the same problem
re-implemented load/save inline. Five more daemons (desire, curiosity,
thought_action_proposal, user_model, visible_runs._PENDING_APPROVALS)
needed the same treatment, so the pattern is now centralized.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_DIR = Path.home() / ".jarvis-v2" / "state"


def _path(name: str) -> Path:
    return _STATE_DIR / f"{name}.json"


def load_json(name: str, default: Any) -> Any:
    """Read ``state/<name>.json``; return ``default`` if missing/corrupt.

    Never raises — callers want a usable value, not an exception. A debug
    log fires on parse failure so corruption is visible without crashing
    the daemon at import time.
    """
    p = _path(name)
    try:
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("state_store: failed to load %s: %s", name, exc)
        return default


def save_json(name: str, data: Any) -> None:
    """Atomically persist ``data`` to ``state/<name>.json``.

    Write-temp-then-rename so a crash mid-write can't leave a half-file.
    """
    p = _path(name)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(tmp, p)
    except Exception as exc:
        logger.debug("state_store: failed to save %s: %s", name, exc)
