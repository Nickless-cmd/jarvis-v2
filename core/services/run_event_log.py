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
# run_id -> {session_id, frames: list[str], base: int, done: bool,
#            last_append_at: float, created_at: float}
# `base` = globalt indeks for frames[0] (ring-buffer-offset, se _MAX_FRAMES).
_RUNS: dict[str, dict] = {}
# RING-VINDUE pr. run (2026-08-19, Bjørn: "streaming stopper pludselig i chatview,
# liveness fortsætter… klipper gerne midt i runde 5"). FØR var dette en HÅRD cap:
# frame 4001+ blev DROPPET (kun terminal reserveret) — og da den LIVE subscriber
# læser fra SAMME buffer som replay, frøs chatview midt i runden mens routens egne
# pings holdt liveness kørende. Lange agentiske runs rammer 4000 omkring runde 4-6
# fordi thinking-deltas (deepseek reasoning), text-deltas og tool-frames alle
# tæller. NU: ring-buffer — ældste frames rulles ud (base rykker), live læsere ved
# hovedet sultes ALDRIG, hukommelsesværnet består (samme vindue). En efternøler
# under base får en gap-markør i stedet for tavshed (read_from).
_MAX_FRAMES = 4000   # runaway-VINDUE pr. run (ring, ikke hård cap)
_ROLL_CHUNK = 256    # rul i klumper så del-operationen amortiseres


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
# Liveness-loft: et run regnes live så længe en frame (inkl. 5s-pings) er kommet
# inden for dette vindue. Hævet 20→45s (2026-06-29): ping-loopet kører på det
# detached event-loop og SULTES når en tool-runde udfører synkront/blokerende
# arbejde der ikke giver kontrol tilbage til loopet (jf. reference_async_blocking_
# worker) → last_append_at fryser i hele tool-runden. Med 20s droppede et langt
# tool-run ud af live_run_ids midt i runden → desk-klienten aborterede sin EGEN
# stadig-levende stream ("mobil tog over / desk hænger"). 45s er et sikkert gulv
# der dækker realistiske blokerende tool-runder uden at forsinke død-detektion
# nævneværdigt (klientens 90s ping-watchdog er den egentlige død-garanti).
_LIVE_IDLE_S = 45.0
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
            "base": 0,
            "done": False,
            "last_append_at": time.monotonic(),
            "created_at": time.monotonic(),
            "subscribers": 0,
            "consumed": False,
            "cap_hit": False,  # har vi allerede emitteret ring-roll-nerven for runnet?
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
        # RING: appender ALTID (live læsere må aldrig sultes — det frøs chatview
        # midt i runde 5). Over vinduet rulles de ÆLDSTE frames ud i klumper og
        # base rykker tilsvarende; globale indekser forbliver monotone.
        st["frames"].append(frame)
        if len(st["frames"]) > _MAX_FRAMES:
            st["frames"][:_ROLL_CHUNK] = []
            st["base"] = int(st.get("base", 0)) + _ROLL_CHUNK
            if not st.get("cap_hit"):
                st["cap_hit"] = True
                cap_just_hit = True
    if cap_just_hit:
        _emit_cap_nerve(rid)
        # Synlig i journald (trace-sinken er in-memory og forsvinder ved restart —
        # dét skjulte denne bug i månedsvis). Én linje pr. run.
        print(f"[run_event_log] ring-roll: run={rid[:24]} vindue={_MAX_FRAMES} "
              f"(ældste frames beskæres; live stream upåvirket)", flush=True)


def _emit_cap_nerve(run_id: str) -> None:
    """Observe (cluster='stream', nerve='relay_frame_cap') at ring-vinduet begyndte
    at rulle (ældste frames beskæres). Live stream er UPÅVIRKET — nerven er nu
    ren telemetri om lange runs, ikke et tab. Selv-sikker."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream", "nerve": "relay_frame_cap",
            "run_id": str(run_id or ""), "max_frames": _MAX_FRAMES,
            "detail": "ring-vindue ruller — ældste frames beskåret; live stream upåvirket",
        })
    except Exception:
        pass


def touch_liveness(run_id: str) -> None:
    """Opdatér et runs liveness (last_append_at) UDEN at persistere en frame.

    Til en tool-eksekverings-heartbeat der vil holde runnet i live_run_ids mens en
    lang tool-runde kører, men ikke har en SSE-frame at appende. Selv-sikker: gør
    intet hvis runnet ikke findes eller allerede er done. Bemærk: hjælper KUN hvis
    den kaldes fra en tråd der faktisk kører mens tool'et arbejder — et heartbeat
    på det samme blokerede event-loop sultes ligesom ping-loopet, og da er
    _LIVE_IDLE_S-gulvet det reelle værn."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None and not st["done"]:
            st["last_append_at"] = time.monotonic()


def mark_done(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["done"] = True


# Gap-markør til en efternøler-læser hvis position er rullet ud af ring-vinduet.
# system_event — klienterne ignorerer ukendte kinds; bedre et hul med besked end
# frossen tavshed. DB har altid det endelige svar.
GAP_FRAME = (
    'event: system_event\n'
    'data: {"type": "system_event", "kind": "relay_gap", '
    '"detail": "tidlig del af streamen beskaaret (ring-vindue) - fortsaetter live"}\n\n'
)


def read(run_id: str, from_idx: int) -> tuple[list[str], bool]:
    """Bagudkompatibel læser (globalt from_idx). For ikke-rullede runs (base=0)
    identisk med før. En efternøler under base får vinduet fra base — brug
    read_from() i stream-loops for korrekt indeks-bogføring + gap-markør."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return ([], False)
        start = max(int(from_idx) - int(st.get("base", 0)), 0)
        return (st["frames"][start:], bool(st["done"]))


def read_from(run_id: str, from_idx: int) -> tuple[list[str], bool, int]:
    """Ring-bevidst læser: returnerer (frames, done, next_idx) hvor next_idx er det
    GLOBALE indeks læseren skal fortsætte fra. Hvis from_idx er rullet ud af
    vinduet (efternøler/re-subscriber), prependes GAP_FRAME så klienten ved at der
    mangler et stykke — i stedet for stille duplikater eller tavshed."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return ([], False, int(from_idx))
        base = int(st.get("base", 0))
        done = bool(st["done"])
        if from_idx < base:
            frames = list(st["frames"])
            return ([GAP_FRAME] + frames, done, base + len(frames))
        start = int(from_idx) - base
        frames = st["frames"][start:]
        return (frames, done, int(from_idx) + len(frames))


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
            "base": 0,
            "done": False,
            "last_append_at": now,
            "created_at": now,
            "subscribers": 0,
            "consumed": False,
            "cap_hit": False,
        }
        return rid, True
