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

import fcntl
import json
import logging
import os
import threading
from contextlib import contextmanager
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
    try:
        save_json_strict(name, data)
    except Exception as exc:
        logger.debug("state_store: failed to save %s: %s", name, exc)


def save_json_strict(name: str, data: Any) -> None:
    """Atomically persist JSON and propagate failures to authoritative callers.

    Most state-store users are optional daemons and deliberately use
    :func:`save_json`, which is self-safe. Recovery ownership is different: a
    caller must not announce a successful settlement if the durable write
    failed. The unique temp name also prevents two threads from sharing one
    ``.tmp`` file before an outer cross-process lock is acquired.
    """
    p = _path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(
        p.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
        )
        os.replace(tmp, p)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


@contextmanager
def med_laas(name: str):
    """Serialisér read-modify-write paa én state-fil paa tvaers af processer.

    `jarvis-api` og `jarvis-runtime` koerer samme kode i hver sin proces og
    deler disse filer. Uden en laas er «laes, aendr, gem» tre skridt hvor den
    ene proces kan naa at skrive imellem — og da hver gemning skriver HELE
    filen, forsvinder den andens aendring sporloest.

    Moensteret er taget fra `in_flight_runs._med_laas`, hvor det har vaeret i
    drift siden 12/9-2026 med samme begrundelse. Det bor her nu, saa den naeste
    delte fil ikke skal opfinde det igen.
    """
    p = _path(name).with_suffix(".lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
