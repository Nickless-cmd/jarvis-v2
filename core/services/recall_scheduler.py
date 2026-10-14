"""core/services/recall_scheduler.py

Baggrunds-scheduler for associativ recall — flytter det tunge relevans-scoring-
LLM-kald UD af den kritiske sti (prompt-assembly → første token) og ind i
post-tur-processeringen, kædet på den FAKTISKE brugerbesked.

Baggrund (12. jul, målt): ``recall_for_message`` scorede historisk imod
``get_latest_cognitive_user_emotional_state()`` = den globalt-seneste
emotionelle-tilstand-række. Den række (a) skrives FØRST efter svaret er sendt
(altid mindst én tur bagud) og (b) på den første besked efter stilhed er den
forurenet af autonome runs (fx "morgenbrief"-opgavetekst). Recall laggede altså
ALLEREDE én tur — og kostede samtidig ~2-4,6s blokerende ventetid på den kritiske
sti (cache er ``sha256(hele prompten)`` med 120s TTL → miss næsten hver rigtig tur).

Ved at køre recall i baggrunden lige EFTER hver tur, kædet på turens rigtige
besked, bevares NØJAGTIGT samme ét-turs-kadence (tur N injicerer stadig minder
relevante for besked N-1) og samme LLM-dommer, samme kandidater, samme tærskler —
men ventetiden forsvinder fra TTFT og autonom-forureningen fjernes. Samme
hukommelse, korrekt kædet, uden ventetiden.

Kill-switch: runtime-state ``background_recall_enabled`` (default ON). Når OFF
falder ``cognitive_state_assembly`` tilbage til inline-recall (gammel opførsel).
Self-safe: kaster ALDRIG, blokerer aldrig den kaldende tur.
"""
from __future__ import annotations

import logging
import threading
import contextvars
from typing import Any

from core.services.scoped_recall_policy import recall_enabled, require_private_scope

logger = logging.getLogger(__name__)

_FLAG = "background_recall_enabled"     # default ON — owner kill-switch
_recall_lock = threading.Lock()
_recall_running_users: set[str] = set()


def background_recall_enabled() -> bool:
    """Er baggrunds-recall aktiv? Default True. Self-safe → True (den nye, hurtige sti)."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_FLAG, True)
        return True if v is None else bool(v)
    except Exception:  # Runtime-state outages preserve the legacy scheduler switch only.
        return True


def _build_emotional_state() -> dict[str, Any]:
    """Byg emotionel baseline til scoringen (samme kilde som cognitive_state_assembly)."""
    try:
        from core.services.affective_meta_state import build_affective_meta_state
        aff = build_affective_meta_state()
        baseline = aff.get("emotional_baseline") or {}
        if isinstance(baseline, dict):
            return {k: float(v) for k, v in baseline.items() if isinstance(v, (int, float))}
    except Exception:  # Emotional enrichment is optional for background recall.
        pass
    return {}


def _run_recall(user_id: str, message_text: str, emotional_state: dict[str, Any]) -> None:
    try:
        from core.services.associative_recall import recall_for_message
        recall_for_message(message_text, emotional_state)
    except Exception:  # Scheduler failures are logged and never escape the request path.
        logger.debug("recall_scheduler: background recall failed", exc_info=True)
    finally:
        with _recall_lock:
            _recall_running_users.discard(user_id)


def trigger_background_recall(
    user_message: str, emotional_state: dict[str, Any] | None = None
) -> bool:
    """Kør ``recall_for_message`` i en baggrundstråd, kædet på den rigtige besked.

    Returnerer True hvis en tråd blev startet, ellers False (flag off / tom besked /
    en recall kører allerede). Blokerer ALDRIG den kaldende tur; kaster aldrig.
    """
    try:
        if not recall_enabled() or not background_recall_enabled():
            return False
        user_id = require_private_scope()
        msg = str(user_message or "").strip()
        if not msg:
            return False
        with _recall_lock:
            if user_id in _recall_running_users:
                return False               # en recall er i gang — spring over, ingen stakning
            _recall_running_users.add(user_id)
        emo = emotional_state if isinstance(emotional_state, dict) else _build_emotional_state()
        ctx = contextvars.copy_context()
        t = threading.Thread(
            target=lambda: ctx.run(_run_recall, user_id, msg, emo),
            name=f"background-recall-{hash(user_id) & 0xffff:x}", daemon=True,
        )
        t.start()
        return True
    except Exception:
        logger.debug("recall_scheduler: trigger failed", exc_info=True)
        with _recall_lock:
            try:
                _recall_running_users.discard(user_id)
            except Exception:  # Cleanup is best-effort when setup failed before user_id existed.
                pass
        return False
