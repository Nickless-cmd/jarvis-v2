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
from uuid import uuid4

_lock = threading.Lock()
# run_id -> {session_id, frames: list[str], done: bool, last_append_at: float, created_at: float}
_RUNS: dict[str, dict] = {}
_MAX_FRAMES = 4000   # runaway-værn pr. run


def _is_terminal_frame(frame: str) -> bool:
    """Er denne SSE-frame en TERMINAL-frame (message_stop)? Klienterne forlader kun
    'working' på message_stop — derfor MÅ den ALDRIG falde for frame-cap'en (F11)."""
    return "event: message_stop" in frame or '"type": "message_stop"' in frame \
        or '"type":"message_stop"' in frame


def _is_ephemeral_frame(frame: str) -> bool:
    """ping/retry-frames er KEEPALIVE-støj på den direkte stream — de er irrelevante
    at replaye til en sen re-subscriber og må ikke æde cap-budgettet på lange runs
    (F11). last_append_at opdateres uanset, så liveness-detektion er upåvirket."""
    return "event: ping" in frame or '"type": "ping"' in frame \
        or '"type":"ping"' in frame or frame.startswith("retry:")
_LIVE_IDLE_S = 20.0  # pings hver ~5s holder live under tool-runder
_KEEP_DONE_PER_SESSION = 1  # behold seneste afsluttede log pr. session til sen reconnect
_CREATE_GRACE_S = 60.0  # nyt run uden appends taelles live i assembly-vinduet (sync assembly blokerer ping-loop)


# Eksakt samme SSE-form som anthropic_sse_emitter.message_stop — klienterne
# (desk/mobil) forlader KUN 'working' på message_stop. Vi opfinder ikke et nyt event.
SYNTHETIC_MESSAGE_STOP = 'event: message_stop\ndata: {"type": "message_stop"}\n\n'


def synthetic_terminal_frame(
    run_id: str = "", session_id: str = "", reason: str = "subscriber_timeout"
) -> str:
    """H1/G6: byg en syntetisk terminal-SSE-frame til en subscriber der GIVER OP uden
    at have set 'done'. Fyrer samtidig den (ellers døde) subscriber_timeout-nerve.
    SELV-SIKKER: kaster ALDRIG — en fejl her må ikke ramme den hotte SSE-generator;
    værst-fald returneres frame'en alligevel så klienten stadig forlader 'working'."""
    try:
        from core.services import stream_sentinel
        stream_sentinel.note_event(
            run_id, "subscriber_timeout", session_id, reason=reason,
        )
    except Exception:
        pass
    return SYNTHETIC_MESSAGE_STOP


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
            "subscribers": 0,
            "consumed": False,
            "cap_hit": False,  # F11: har vi allerede emitteret truncation-nerven for runnet?
        }


def append(run_id: str, frame: str) -> None:
    rid = (run_id or "").strip()
    if not rid or not frame:
        return
    cap_just_hit = False
    with _lock:
        st = _RUNS.get(rid)
        if st is None:
            return
        st["last_append_at"] = time.monotonic()
        # Ephemeral keepalive (ping/retry): opdater liveness men persistér IKKE i
        # replay-bufferen — så de ikke æder cap-budgettet (F11).
        if _is_ephemeral_frame(frame):
            return
        terminal = _is_terminal_frame(frame)
        if len(st["frames"]) < _MAX_FRAMES:
            st["frames"].append(frame)
        elif terminal:
            # F11: TERMINAL-frame ankom EFTER cap'en. Den MÅ aldrig droppes —
            # ellers ser hver re-subscriber intet 'done' → H1 bare-break → hæng.
            # Reservér en hale-plads: tilføj den uanset cap (det er højst én frame
            # i praksis, så bufferen vokser ikke ubegrænset).
            st["frames"].append(frame)
        else:
            # F11: ikke-terminal frame over cap → DROPPES. Emit truncation-nerven
            # ÉN gang pr. run, FØR vi taber den første over-cap frame.
            if not st.get("cap_hit"):
                st["cap_hit"] = True
                cap_just_hit = True
    if cap_just_hit:
        _emit_cap_nerve(rid)


def _emit_cap_nerve(run_id: str) -> None:
    """Observe (cluster='stream', nerve='relay_frame_cap') at relay-bufferen ramte
    cap'en og begynder at droppe ikke-terminale frames. Selv-sikker."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream", "nerve": "relay_frame_cap",
            "run_id": str(run_id or ""), "max_frames": _MAX_FRAMES,
            "detail": "relay-buffer over cap — dropper ikke-terminale frames; terminal-frame reserveres",
        })
    except Exception:
        pass


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
        now = time.monotonic()
        # Live hvis nylig append ELLER for nyligt oprettet (assembly-grace).
        return ((now - st["last_append_at"]) < _LIVE_IDLE_S
                or (now - st["created_at"]) < _CREATE_GRACE_S)


def live_run_ids() -> list[str]:
    now = time.monotonic()
    with _lock:
        return [
            rid for rid, st in _RUNS.items()
            if not st["done"] and (
                (now - st["last_append_at"]) < _LIVE_IDLE_S
                or (now - st["created_at"]) < _CREATE_GRACE_S
            )
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


def subscriber_opened(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["subscribers"] = int(st.get("subscribers", 0)) + 1


def subscriber_closed(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["subscribers"] = max(0, int(st.get("subscribers", 0)) - 1)


def mark_consumed(run_id: str) -> None:
    """En subscriber yieldede message_stop -> nogen saa runnet til ende."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["consumed"] = True


def was_consumed_or_active(run_id: str) -> bool:
    """True hvis en levende subscriber saa/ser runnet til ende -> undertryk push."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return False
        return bool(st.get("consumed")) or int(st.get("subscribers", 0)) > 0


def claim_or_create(session_id: str, stale_cap_s: float = 150.0) -> tuple[str, bool]:
    """Atomisk find-eller-opret pr. session — under én laas, saa samtidige POSTs
    (hurtige gen-sends) ikke begge opretter et run (rod-aarsag til hard-block).
    Stale-cap: et ikke-done run aeldre end stale_cap_s antages doedt/haengt og
    claimes IKKE -> ny besked starter et frisk run. Returnerer (run_id, is_new)."""
    sid = (session_id or "").strip()
    now = time.monotonic()
    with _lock:
        existing = None
        newest = -1.0
        for rid, st in _RUNS.items():
            if (st["session_id"] == sid and not st["done"]
                    and (now - st["created_at"]) < stale_cap_s):
                if st["created_at"] > newest:
                    newest = st["created_at"]
                    existing = rid
        if existing is not None:
            return existing, False
        rid = f"visible-{uuid4().hex}"
        _RUNS[rid] = {
            "session_id": sid,
            "frames": [],
            "done": False,
            "last_append_at": now,
            "created_at": now,
            "subscribers": 0,
            "consumed": False,
            "cap_hit": False,
        }
        return rid, True
