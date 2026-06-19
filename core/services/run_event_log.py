"""In-memory, append-only, offset-indekseret event-log PR. RUN.

Den autoritative sandhed om en visible-runs v2-SSE-frames. Et detached run
appender hertil fra sin baggrundstråd; HTTP-endpoints læser fra et offset og
streamer videre. Keyed pr. run_id (IKKE session — det var A3's fejl, hvor
overlappende runs i samme session klobbede hinandens buffer).

--workers 1 → delt in-memory på tværs af alle endpoints + baggrundstråde.
"""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()
# run_id -> {session_id, frames: list[str], done: bool, last_append_at: float, created_at: float}
_RUNS: dict[str, dict] = {}
_MAX_FRAMES = 4000   # runaway-værn pr. run
_LIVE_IDLE_S = 20.0  # pings hver ~5s holder live under tool-runder
_KEEP_DONE_PER_SESSION = 1  # behold seneste afsluttede log pr. session til sen reconnect


def create(run_id: str, session_id: str) -> None:
    rid = (run_id or "").strip()
    if not rid:
        return
    with _lock:
        _RUNS[rid] = {
            "session_id": (session_id or "").strip(),
            "frames": [],
            "done": False,
            "last_append_at": time.monotonic(),
            "created_at": time.monotonic(),
        }


def append(run_id: str, frame: str) -> None:
    rid = (run_id or "").strip()
    if not rid or not frame:
        return
    with _lock:
        st = _RUNS.get(rid)
        if st is None:
            return
        if len(st["frames"]) < _MAX_FRAMES:
            st["frames"].append(frame)
        st["last_append_at"] = time.monotonic()


def mark_done(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["done"] = True


def read(run_id: str, from_idx: int) -> tuple[list[str], bool]:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return ([], False)
        return (st["frames"][from_idx:], bool(st["done"]))


def active_run_for_session(session_id: str) -> str | None:
    sid = (session_id or "").strip()
    newest: tuple[float, str] | None = None
    with _lock:
        for rid, st in _RUNS.items():
            if st["session_id"] == sid and not st["done"]:
                if newest is None or st["created_at"] > newest[0]:
                    newest = (st["created_at"], rid)
    return newest[1] if newest else None


def is_live(run_id: str) -> bool:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if not st or st["done"]:
            return False
        return (time.monotonic() - st["last_append_at"]) < _LIVE_IDLE_S


def live_run_ids() -> list[str]:
    now = time.monotonic()
    with _lock:
        return [
            rid for rid, st in _RUNS.items()
            if not st["done"] and (now - st["last_append_at"]) < _LIVE_IDLE_S
        ]


def session_for_run(run_id: str) -> str | None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        return st["session_id"] if st else None


def prune() -> None:
    """Behold alle ikke-done runs + de seneste _KEEP_DONE_PER_SESSION done-runs
    pr. session; drop ældre afsluttede logs (DB har det endelige svar)."""
    with _lock:
        done_by_session: dict[str, list[tuple[float, str]]] = {}
        for rid, st in _RUNS.items():
            if st["done"]:
                done_by_session.setdefault(st["session_id"], []).append((st["created_at"], rid))
        drop: set[str] = set()
        for _sid, runs in done_by_session.items():
            runs.sort(reverse=True)
            for _ts, rid in runs[_KEEP_DONE_PER_SESSION:]:
                drop.add(rid)
        for rid in drop:
            _RUNS.pop(rid, None)
