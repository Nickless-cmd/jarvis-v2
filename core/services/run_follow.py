"""Follow-stream for autonome runs → jarvis-desk kan token-streame dem live.

Et autonomt run (fx operator-wakeup) streamer SSE-frames server-side, men ingen
lytter — desk'en åbnede ikke SSE'en. Resultatet "dumpes" ind når runnet er
færdigt (via refresh). Denne modul lader runnet PUBLICERE sine v2-frames til en
in-memory buffer pr. session, som et `GET /chat/sessions/{id}/follow`-endpoint
poller og streamer videre til desk'en — der fodrer dem ind i den SAMME
streamReducer og renderer token-for-token, præcis som et normalt run.

CROSS-PROCES: virker fordi operator-wakeup-runnet kører i jarvis-api-processen
(start_autonomous_run kaldes fra operator_wakeup_fired), samme proces som
follow-endpointet. --workers 1 → én proces → delt in-memory buffer. (Runtime-
processens heartbeat-runs er IKKE followbare; det er kun desk-wakeups vi vil
streame.)

Tråd-sikkerhed: runnet publicerer fra sin egen tråd/event-loop; endpointet
poller fra api-loopen. Vi bruger en simpel liste + Lock og POLLING (ikke en
asyncio.Queue der ikke kan deles på tværs af event-loops) — robust og enkelt.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
# session_id → {"frames": list[str], "done": bool, "run_id": str}
_STREAMS: dict[str, dict] = {}
_MAX_FRAMES = 4000  # hård cap pr. run (sikkerhed mod runaway)


def begin_follow(session_id: str, run_id: str = "") -> None:
    """Nulstil buffer for en NY run i sessionen (catch-up starter forfra)."""
    sid = (session_id or "").strip()
    if not sid:
        return
    with _lock:
        _STREAMS[sid] = {"frames": [], "done": False, "run_id": str(run_id or "")}


def publish_follow_frame(session_id: str, frame: str) -> None:
    """Append en v2-SSE-frame til sessionens buffer (kaldt fra run-tråden)."""
    sid = (session_id or "").strip()
    if not sid or not frame:
        return
    with _lock:
        st = _STREAMS.get(sid)
        if st is None:
            st = _STREAMS[sid] = {"frames": [], "done": False, "run_id": ""}
        if len(st["frames"]) < _MAX_FRAMES:
            st["frames"].append(frame)


def end_follow(session_id: str) -> None:
    """Markér sessionens follow-stream som færdig → pollende endpoint stopper."""
    sid = (session_id or "").strip()
    if not sid:
        return
    with _lock:
        st = _STREAMS.get(sid)
        if st is not None:
            st["done"] = True


def _snapshot(session_id: str, from_idx: int) -> tuple[list[str], bool]:
    """Returnér (nye frames fra from_idx, done)."""
    with _lock:
        st = _STREAMS.get(session_id)
        if st is None:
            return ([], False)
        frames = st["frames"]
        return (frames[from_idx:], bool(st["done"]))


def has_active_follow(session_id: str) -> bool:
    """True hvis der findes en (ikke-afsluttet) follow-buffer for sessionen."""
    with _lock:
        st = _STREAMS.get((session_id or "").strip())
        return bool(st) and not st.get("done")
