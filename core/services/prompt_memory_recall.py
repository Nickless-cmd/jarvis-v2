"""Supplementary non-blocking recall during visible prompt assembly.

Extracted from prompt_contract so the existing one-turn cache and background
refresh remain unchanged while current-turn decision recall can be added at
the volatile tail without enlarging the prompt composer.
"""
from __future__ import annotations

import threading
import logging

logger = logging.getLogger(__name__)

_RBA_CACHE: dict = {}
_RBA_INFLIGHT: set = set()
_RBA_LOCK = threading.Lock()
_RBA_TTL_S = 300.0
_MSR_CACHE: dict = {}
_MSR_INFLIGHT: set = set()


def append_background_recall(user_message, session_id, _dyn_memory_recall, derived_inputs, _sec_err):
    # Fix 2 (2026-04-27): recall_before_act in visible runs — was only used
    # in heartbeat phases. Surface relevant memories tied to user_message so
    # Jarvis answers from memory, not stub-context.
    try:
        from core.services.memory_hierarchy import recall_before_act_summary
        if user_message and len(user_message.strip()) >= 8:
            # Query-adaptiv recall → bruger-besked-halen (lever #4 cache-fix),
            # ikke awareness (som rendres før historikken).
            # Hård 4s deadline (29. jun, CUT-OFF-ROD): denne recall laver embed/DB-
            # kald der UNDER ollama-kontention (baggrunds frame/cognitive_state-
            # futures mætter samme ollama) kø'ede 20-26s INLINE i q3-segmentet →
            # frøs --workers 1 → cut-off for ALLE brugere (verificeret på Mikkels
            # session). Var den ENESTE uncappede recall i q3 (multi_signal har
            # allerede 4s-cap). Samme tråd-deadline-mønster; synlig i Centralen.
            import threading as _thr_rba
            import contextvars as _cv_rba
            import time as _t_rba
            _sid_rba = (session_id or "").strip()
            _now_rba = _t_rba.monotonic()
            # 1) Serve the last cached recall IMMEDIATELY — never block the turn.
            with _RBA_LOCK:
                _cached = _RBA_CACHE.get(_sid_rba)
                _busy = _sid_rba in _RBA_INFLIGHT
            if _cached and (_now_rba - _cached[0]) < _RBA_TTL_S and _cached[1]:
                _dyn_memory_recall.append(_cached[1])
                derived_inputs.append("recall-before-act (cached, non-blocking)")
            # 2) Refresh in the background for the NEXT turn (deduped per session).
            #    copy_context() so the raw thread keeps user_context (workspace source).
            if not _busy and _sid_rba:
                with _RBA_LOCK:
                    _RBA_INFLIGHT.add(_sid_rba)
                _rba_ctx = _cv_rba.copy_context()
                _rba_q = user_message

                def _refresh_rba() -> None:
                    try:
                        _v = _rba_ctx.run(recall_before_act_summary, query=_rba_q)
                        if _v:
                            with _RBA_LOCK:
                                _RBA_CACHE[_sid_rba] = (_t_rba.monotonic(), _v)
                    except Exception as exc:
                        logger.debug("recall-before-act refresh failed: %s", exc)
                    finally:
                        with _RBA_LOCK:
                            _RBA_INFLIGHT.discard(_sid_rba)

                _thr_rba.Thread(target=_refresh_rba, name="recall-before-act-bg", daemon=True).start()
    except Exception as exc:
        logger.debug("recall-before-act setup failed: %s", exc)
    # Multi-signal recall (B1, 2026-06-08) — Claude 2026-06-09: B1 module
    # (multi_signal_retrieval.py + 214 lines integration in
    # memory_recall_engine.py) was built and tested but never wired into
    # any prompt section. Now surfaced as a complementary recall using
    # BM25 + entity + embedding fusion. Lower priority than
    # recall-before-act since this is "wider net", not user-message-specific.
    try:
        from core.services.memory_recall_engine import multi_signal_recall_section
        if user_message and len(user_message.strip()) >= 8:
            import threading as _thr_msr
            import contextvars as _cv_msr
            import time as _t_msr
            _sid_msr = (session_id or "").strip()
            _now_msr = _t_msr.monotonic()
            with _RBA_LOCK:
                _c_msr = _MSR_CACHE.get(_sid_msr)
                _busy_msr = _sid_msr in _MSR_INFLIGHT
            # Serve last cached result immediately (non-blocking).
            if _c_msr and (_now_msr - _c_msr[0]) < _RBA_TTL_S and _c_msr[1]:
                # 2026-09-04 (memory repair, R2): til [HUKOMMELSE]-gruppen.
                _dyn_memory_recall.append(_c_msr[1])
                derived_inputs.append("multi-signal recall (memory group)")
            # Refresh in background for the next turn (deduped per session).
            if not _busy_msr and _sid_msr:
                with _RBA_LOCK:
                    _MSR_INFLIGHT.add(_sid_msr)
                _msr_ctx = _cv_msr.copy_context()
                _msr_q = user_message

                def _refresh_msr() -> None:
                    try:
                        _v = _msr_ctx.run(multi_signal_recall_section, _msr_q)
                        if _v:
                            with _RBA_LOCK:
                                _MSR_CACHE[_sid_msr] = (_t_msr.monotonic(), _v)
                    except Exception as exc:
                        logger.debug("multi-signal recall refresh failed: %s", exc)
                    finally:
                        with _RBA_LOCK:
                            _MSR_INFLIGHT.discard(_sid_msr)

                _thr_msr.Thread(target=_refresh_msr, name="multi-signal-recall-bg", daemon=True).start()
    except Exception as _e:
        _sec_err("multi-signal recall (BM25+entity+embedding)", _e)
