"""core/services/assembly_prewarm.py

Periodisk pre-warm af HELE prompt-assemblyen så den kolde-start-pris ikke rammer
Bjørns første besked efter tomgang (fx "Godmorgen" efter en nats stilhed).

Baggrund (12. jul, målt): varm assembly = ~3,6s, kold = ~10,5s. De ~7s er IKKE
ét monster men **død ved tusind snit** — mange awareness-sektioner der hver
cacher uafhængigt og bliver kolde under tomgang (DB-sider/OS-page-cache, surface-
caches, narrativizer-fingeraftryk). Der findes allerede en ENGANGS boot-pre-warm
(app.py) af én surface, men den overlever ikke en nats tomgang. Denne loop kører
en throwaway-assembly-build på en kadence, så caches aldrig når at blive kolde.

Sikkerhed: build'en er READ-only for hukommelse (bg-recall skriver post-tur i
visible_runs, IKKE her). Den eneste reelle bivirkning — composition-telemetri
(observe_composition) — neutraliseres via ``is_prewarm_active()``-flaget, som
central_prompt_composer tjekker. Egen throwaway-session ("__prewarm__"), så
session-kontinuitet ikke forurenes. Self-safe: kaster aldrig, blokerer aldrig en
rigtig tur.

Governance: kill-switch ``assembly_prewarm_enabled`` (runtime-state) + tunbar
kadence ``assembly_prewarm_interval_s`` (default 240s). Sidste-kørsel-stats i
shared_cache under ``assembly_prewarm_stats`` til observability.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from typing import Any

_COSTS_DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")


def _max_created_at_real_deepseek() -> float | None:
    """Epoch seconds of the most recent NON-warmer deepseek call in costs. None if none.
    Self-safe (DB lock/error -> None); opens read-only."""
    try:
        c = sqlite3.connect(f"file:{_COSTS_DB}?mode=ro", uri=True, timeout=2)
        row = c.execute(
            "select max(created_at) from costs where provider='deepseek' "
            "and coalesce(lane,'') not like '%warm%'"
        ).fetchone()
        c.close()
        if not row or not row[0]:
            return None
        from datetime import datetime
        return datetime.fromisoformat(row[0]).timestamp()
    except Exception:
        return None


def _seconds_since_last_real_deepseek_call() -> float | None:
    ts = _max_created_at_real_deepseek()
    return None if ts is None else max(0.0, time.time() - ts)


def _max_created_at_visible() -> float | None:
    """Epoch-sek. for seneste ÆGTE bruger↔Jarvis-aktivitet (visible-lanen). None hvis
    ingen. Ekskluderer warmeren (lane=primary). Self-safe, read-only."""
    try:
        c = sqlite3.connect(f"file:{_COSTS_DB}?mode=ro", uri=True, timeout=2)
        row = c.execute(
            "select max(created_at) from costs where lane in ('visible','agent')"
        ).fetchone()
        c.close()
        if not row or not row[0]:
            return None
        from datetime import datetime
        return datetime.fromisoformat(row[0]).timestamp()
    except Exception:
        return None


def _seconds_since_last_user_activity() -> float | None:
    ts = _max_created_at_visible()
    return None if ts is None else max(0.0, time.time() - ts)


_IDLE_WINDOW_KEY = "assembly_prewarm_idle_window_s"   # >denne uden bruger-aktivitet → idle → warm ikke
_DEFAULT_IDLE_WINDOW = 900.0                           # 15 min: bygg bro over samtale-pauser, ikke idle


def _idle_window_s() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return float(get_runtime_state_value(_IDLE_WINDOW_KEY, _DEFAULT_IDLE_WINDOW)
                     or _DEFAULT_IDLE_WINDOW)
    except Exception:
        return _DEFAULT_IDLE_WINDOW

logger = logging.getLogger(__name__)

_ENABLED_FLAG = "assembly_prewarm_enabled"          # default OFF → flip via runtime-state efter verifikation
_INTERVAL_KEY = "assembly_prewarm_interval_s"       # default 600s
_DEFAULT_INTERVAL = 600.0
_MIN_INTERVAL = 300.0

_PREWARM_SESSION = "__prewarm__"
_loop_started = False
_loop_lock = threading.Lock()

# Thread-local: sat mens en pre-warm-build kører, så bivirkninger (telemetri)
# kan no-op'e. Tråd-lokal fordi kun pre-warm-tråden bygger under flaget.
_local = threading.local()


def is_prewarm_active() -> bool:
    """True hvis den aktuelle tråd i øjeblikket kører en pre-warm-build. Self-safe."""
    return bool(getattr(_local, "prewarm_active", False))


def assembly_prewarm_enabled() -> bool:
    """Kill-switch. Default OFF (shadow) — flip via runtime-state. Self-safe → False."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_ENABLED_FLAG, False)
        return False if v is None else bool(v)
    except Exception:
        return False


def _interval_s() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = float(get_runtime_state_value(_INTERVAL_KEY, _DEFAULT_INTERVAL) or _DEFAULT_INTERVAL)
        return max(_MIN_INTERVAL, v)
    except Exception:
        return _DEFAULT_INTERVAL


_SKIP_IF_RECENT_KEY = "assembly_prewarm_skip_if_recent_s"   # default 300 (DeepSeek cache-TTL)
_DEFAULT_SKIP_IF_RECENT = 300.0
_LAST_PREWARM_CACHE_KEY = "assembly_prewarm_last_ts"        # cross-process via shared_cache


def _skip_if_recent_s() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return float(get_runtime_state_value(_SKIP_IF_RECENT_KEY, _DEFAULT_SKIP_IF_RECENT)
                     or _DEFAULT_SKIP_IF_RECENT)
    except Exception:
        return _DEFAULT_SKIP_IF_RECENT


def _seconds_since_last_prewarm() -> float | None:
    """Cross-process: seconds since ANY process last prewarmed. None if never."""
    try:
        from core.services import shared_cache as _sc
        ts = _sc.get(_LAST_PREWARM_CACHE_KEY)
        return None if not ts else max(0.0, time.time() - float(ts))
    except Exception:
        return None


def _mark_prewarmed() -> None:
    try:
        from core.services import shared_cache as _sc
        _sc.set(_LAST_PREWARM_CACHE_KEY, time.time(), ttl_seconds=3600)
    except Exception:
        pass


def _should_prewarm() -> bool:
    """Event-drevet gate (15. jul — dræber 292M-tokens/13d-burnet). Warm KUN når det
    tilføjer værdi: (1) cross-process selv-throttle (en anden proces warmede < interval →
    skip; fikser 85s-over-fyring på tværs af api+runtime), (2) skip hvis rigtig deepseek-
    trafik allerede holder cachen varm, (3) IDLE-GATE: ingen bruger-aktivitet (visible/
    agent) inden for idle_window → idle → warm ALDRIG (ingen at holde cachen varm for)."""
    # (1) cross-process throttle via shared_cache (uafhængig af lease)
    since_warm = _seconds_since_last_prewarm()
    if since_warm is not None and since_warm < _interval_s():
        return False
    # (2) rigtig deepseek-trafik holder allerede cachen varm
    since_real = _seconds_since_last_real_deepseek_call()
    if since_real is not None and since_real < _skip_if_recent_s():
        return False
    # (3) idle-gate — nul brænd når ingen taler med Jarvis
    since_activity = _seconds_since_last_user_activity()
    if since_activity is None or since_activity > _idle_window_s():
        return False
    return True


def _try_acquire_prewarm_lease(interval_s: float) -> bool:
    """Atomisk cross-process: kun ÉN proces vinder retten til at warme pr. interval.
    Conditional UPDATE i jarvis.db (SQLite serialiserer writes → ingen race).
    Fail-CLOSED: kan vi ikke tage leasen, warmer vi IKKE (undgår runaway)."""
    try:
        c = sqlite3.connect(_COSTS_DB, timeout=5)
        try:
            c.execute("CREATE TABLE IF NOT EXISTS prewarm_lease (id INTEGER PRIMARY KEY CHECK(id=1), ts REAL)")
            c.execute("INSERT OR IGNORE INTO prewarm_lease (id, ts) VALUES (1, 0)")
            now = time.time()
            cur = c.execute("UPDATE prewarm_lease SET ts=? WHERE id=1 AND ts < ?", (now, now - interval_s))
            c.commit()
            return cur.rowcount == 1
        finally:
            c.close()
    except Exception:
        return False


def _record_stats(elapsed_s: float | None, error: str | None = None) -> None:
    try:
        from core.services import shared_cache as _sc
        st = _sc.get("assembly_prewarm_stats") or {}
        st["runs"] = int(st.get("runs", 0)) + 1
        if elapsed_s is not None:
            st["last_elapsed_s"] = round(float(elapsed_s), 2)
        if error:
            st["last_error"] = str(error)[:200]
            st["errors"] = int(st.get("errors", 0)) + 1
        _sc.set("assembly_prewarm_stats", st, ttl_seconds=7 * 86400)
    except Exception:
        pass


def prewarm_once() -> float | None:
    """Byg én throwaway-assembly for at varme alle sektions-caches. Returnerer
    forløbet tid i sekunder, eller None hvis sprunget over/fejlet. Self-safe."""
    if not _should_prewarm():
        return None
    if not _try_acquire_prewarm_lease(_interval_s()):
        return None
    _local.prewarm_active = True
    try:
        from core.services.prompt_contract import build_visible_chat_prompt_assembly
        t0 = time.monotonic()
        build_visible_chat_prompt_assembly(
            provider="deepseek",            # ikke-ollama → compact=False → fuld sektions-dækning
            model="deepseek-v4-flash",
            user_message="(prewarm)",
            session_id=_PREWARM_SESSION,
        )
        elapsed = time.monotonic() - t0
        _record_stats(elapsed)
        _mark_prewarmed()   # cross-process throttle-stempel (så _should_prewarm (1) virker)
        logger.info("assembly_prewarm: build complete in %.2fs", elapsed)
        return elapsed
    except Exception as exc:
        logger.debug("assembly_prewarm: build failed", exc_info=True)
        _record_stats(None, error=str(exc))
        return None
    finally:
        _local.prewarm_active = False


def _loop() -> None:
    logger.info("assembly_prewarm: loop started")
    while True:
        try:
            interval = _interval_s()
            time.sleep(interval)
            if assembly_prewarm_enabled():
                prewarm_once()
        except Exception:
            logger.debug("assembly_prewarm: loop iteration failed", exc_info=True)
            try:
                time.sleep(_DEFAULT_INTERVAL)
            except Exception:
                return


def start_prewarm_loop() -> bool:
    """Start baggrunds-pre-warm-loopet én gang pr. proces. Idempotent. Loopet kører
    ALTID men pre-warmer kun når kill-switchen er ON (så den kan tændes uden restart).
    Returnerer True hvis en tråd blev startet nu. Self-safe."""
    global _loop_started
    try:
        with _loop_lock:
            if _loop_started:
                return False
            _loop_started = True
        threading.Thread(target=_loop, name="assembly-prewarm", daemon=True).start()
        return True
    except Exception:
        logger.debug("assembly_prewarm: failed to start loop", exc_info=True)
        return False
