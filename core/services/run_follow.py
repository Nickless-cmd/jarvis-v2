"""Follow-stream for runs → klienter kan token-streame dem live + liveness-kilde.

Et run (autonomt wakeup ELLER afkoblet bruger-run, A3) streamer SSE-frames
server-side. Denne modul lader runnet PUBLICERE sine v2-frames til en in-memory
buffer pr. session, som `GET /chat/sessions/{id}/follow` poller og streamer
videre. Klienten fodrer dem ind i SAMME streamReducer → token-for-token.

CROSS-PROCES: virker fordi både de afkoblede bruger-runs (start_user_run_
detached) OG operator-wakeup-runs kører i jarvis-api-processen — samme proces
som follow-endpointet OG /chat/active-runs. --workers 1 → én proces → delt
in-memory buffer.

LIVENESS-KILDE (2026-06-18): bufferen er ogsaa den autoritative "kører et run i
denne session lige nu?"-kilde for /chat/active-runs (desktop-aktivitetsprikker).
Et levende run publicerer frames (mindst en ping hvert ~5s fra translate_to_v2),
saa `last_frame_at` holdes frisk; `end_follow` saetter done → øjeblikkeligt ikke-
live. Det er paalideligt fordi alt er SAMME proces (modsat det DELTE active-run-
heartbeat, der opdateres cross-proces og halter for detached runs).

Tråd-sikkerhed: runnet publicerer fra sin egen tråd; endpointet poller fra
api-loopen. Simpel liste + Lock + polling (ingen asyncio.Queue på tværs af
event-loops).
"""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()
# session_id → {"frames": list[str], "done": bool, "run_id": str, "last_frame_at": float}
_STREAMS: dict[str, dict] = {}
_MAX_FRAMES = 4000  # hård cap pr. run (sikkerhed mod runaway)
# Et run regnes som live hvis dets buffer ikke er done OG sidste frame er
# nyere end dette (pings hvert ~5s → 20s giver rigelig margin mod falsk-negativ).
_LIVE_IDLE_S = 20.0


def begin_follow(session_id: str, run_id: str = "") -> None:
    """Nulstil buffer for en NY run i sessionen (catch-up starter forfra)."""
    sid = (session_id or "").strip()
    if not sid:
        return
    with _lock:
        _STREAMS[sid] = {
            "frames": [],
            "done": False,
            "run_id": str(run_id or ""),
            "last_frame_at": time.monotonic(),
        }


def publish_follow_frame(session_id: str, frame: str) -> None:
    """Append en v2-SSE-frame til sessionens buffer (kaldt fra run-tråden)."""
    sid = (session_id or "").strip()
    if not sid or not frame:
        return
    with _lock:
        st = _STREAMS.get(sid)
        if st is None:
            st = _STREAMS[sid] = {"frames": [], "done": False, "run_id": "", "last_frame_at": 0.0}
        if len(st["frames"]) < _MAX_FRAMES:
            st["frames"].append(frame)
        st["last_frame_at"] = time.monotonic()


def end_follow(session_id: str) -> None:
    """Markér sessionens follow-stream som færdig → pollende endpoint stopper
    + session regnes øjeblikkeligt som ikke-live."""
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


def session_is_live(session_id: str, max_idle_s: float = _LIVE_IDLE_S) -> bool:
    """Autoritativ: kører der et run i denne session LIGE NU? (ikke done OG
    frisk frame-aktivitet). Bruges af /chat/active-runs."""
    sid = (session_id or "").strip()
    with _lock:
        st = _STREAMS.get(sid)
        if not st or st.get("done"):
            return False
        return (time.monotonic() - float(st.get("last_frame_at") or 0.0)) < max_idle_s


def live_sessions(max_idle_s: float = _LIVE_IDLE_S) -> list[str]:
    """Alle sessioner med et run der aktivt streamer lige nu (desktop-prikker +
    cross-device liveness). Øjeblikkeligt tomt naar runs afsluttes (done)."""
    now = time.monotonic()
    out: list[str] = []
    with _lock:
        for sid, st in _STREAMS.items():
            if st.get("done"):
                continue
            if (now - float(st.get("last_frame_at") or 0.0)) < max_idle_s:
                out.append(sid)
    return out
