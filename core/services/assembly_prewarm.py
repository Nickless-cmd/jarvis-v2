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
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_ENABLED_FLAG = "assembly_prewarm_enabled"          # default OFF → flip via runtime-state efter verifikation
_INTERVAL_KEY = "assembly_prewarm_interval_s"       # default 240s
_DEFAULT_INTERVAL = 240.0
_MIN_INTERVAL = 60.0

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
