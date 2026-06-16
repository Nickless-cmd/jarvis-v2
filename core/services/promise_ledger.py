"""Promise-ledger (Bjørn-gate) — 16. jun 2026.

Bjørn lie-crisis: Jarvis siger gang på gang "jeg gør det / jeg går i gang" og
leverer ikke. unfinished_intent FANGER løftet (continuation), claim_scanner +
diagnosis_gate §8 fanger FALSKE completion-claims. Det manglende stykke var
ANSVARLIGHED på tværs af ture: husk hvad han lovede, og konfrontér ham med det
NÆSTE tur ("du sagde du ville X — gjorde du det?").

Denne ledger registrerer fremtids-løfter per session og lader
`prompt_contract._pending_promises_section` rejse dem prominent i prompten.
Backes af runtime_state (cross-proces), TTL + cap. Fail-soft hele vejen.
"""
from __future__ import annotations

import time

_KEY = "pending_promises"
_TTL_SECONDS = 1800  # 30 min — efter det regnes løftet som forældet/glemt
_MAX_PER_SESSION = 5


def record_promise(session_id: str, text: str, *, now: float | None = None) -> None:
    """Notér at Jarvis lovede en handling i `session_id`. Capper til de seneste N."""
    sid = (session_id or "").strip()
    body = (text or "").strip()
    if not sid or not body:
        return
    try:
        from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
        store = get_runtime_state_value(_KEY, {}) or {}
        if not isinstance(store, dict):
            store = {}
        lst = [p for p in store.get(sid, []) if isinstance(p, dict)]
        lst.append({"text": body[:200], "ts": float(now if now is not None else time.time())})
        store[sid] = lst[-_MAX_PER_SESSION:]
        set_runtime_state_value(_KEY, store)
    except Exception:
        pass


def pending_promises(
    session_id: str, *, within_s: int = _TTL_SECONDS, now: float | None = None,
) -> list[dict]:
    """Ikke-forældede løfter for `session_id` (nyeste sidst). [] ved fejl/tomt."""
    sid = (session_id or "").strip()
    if not sid:
        return []
    try:
        from core.runtime.db_core import get_runtime_state_value
        store = get_runtime_state_value(_KEY, {}) or {}
        if not isinstance(store, dict):
            return []
        cutoff = float(now if now is not None else time.time()) - within_s
        return [
            p for p in store.get(sid, [])
            if isinstance(p, dict) and float(p.get("ts", 0)) >= cutoff
        ]
    except Exception:
        return []


def clear_promises(session_id: str) -> None:
    """Ryd løfterne for en session (fx når Bjørn bekræfter de er indfriet)."""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
        store = get_runtime_state_value(_KEY, {}) or {}
        if isinstance(store, dict) and sid in store:
            store.pop(sid, None)
            set_runtime_state_value(_KEY, store)
    except Exception:
        pass
