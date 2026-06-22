"""Abuse-monitoring (spec 2026-06-21 §5): prompt-injection, manipulation,
rate-limiting, tool-output-injection.

Designprincipper:
- **First-pass filter** (§5.3): pattern matching fanger de åbenlyse forsøg. Ikke en
  komplet løsning — LLM-fallback kan lægges ovenpå senere.
- **Injection LÅSER IKKE** på første detektion (for falsk-positiv-tungt) — den logges
  som abuse_event (high) + notificerer Bjørn. Kun identity-spoof (gentaget) og
  rate-limit (gentaget) eskalerer til session-lock. Sprog-agnostisk (§11.4).
- **Rate-limit** (§10): >20 beskeder/min pr. user_id → throttle-warning; 3 throttles
  i 10 min → session-lock.
- **Fail-open**: en exception må aldrig spærre normal chat.
"""
from __future__ import annotations

import logging
import re
import time

logger = logging.getLogger(__name__)

from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services import security_guard

RATE_LIMIT_PER_MIN = security_guard.RATE_LIMIT_PER_MIN  # 20
THROTTLES_FOR_LOCK = 3

# ── prompt-injection pattern-bibliotek (§5.3) ───────────────────────────
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_previous", re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts?|messages?)", re.I)),
    ("ignore_da", re.compile(r"(ignorér|ignorer|glem)\s+(alle\s+)?(tidligere|forrige|ovenstående)\s+(instruktioner|beskeder)", re.I)),
    ("you_are_now", re.compile(r"\byou\s+are\s+now\s+(a|an|the)\b", re.I)),
    ("act_as", re.compile(r"\b(act|behave|respond)\s+as\s+(if\s+)?(a|an|though)\b", re.I)),
    ("reveal_prompt", re.compile(r"(repeat|reveal|print|show|output)\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)", re.I)),
    ("dan_jailbreak", re.compile(r"\b(DAN|do\s+anything\s+now|developer\s+mode|jailbreak)\b", re.I)),
    ("disregard_safety", re.compile(r"(disregard|bypass|override)\s+(your\s+)?(safety|guidelines|restrictions|rules)", re.I)),
    ("base64_blob", re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")),  # lang base64-streng = mistænkelig
]


def scan_for_injection(text: str) -> list[str]:
    """Returnér navne på matchede injection-mønstre (tom = rent)."""
    t = text or ""
    if len(t) > 20000:
        t = t[:20000]
    hits: list[str] = []
    for name, pat in _INJECTION_PATTERNS:
        try:
            if pat.search(t):
                hits.append(name)
        except Exception:
            continue
    return hits


# ── rate-limiting (sliding window pr. user_id) ──────────────────────────
def _rl_key(user_id: str) -> str:
    return f"abuse_rate:{(user_id or '').strip()}"


def check_rate_limit(user_id: str, *, now: float | None = None) -> bool:
    """True hvis brugeren ER inden for grænsen (må fortsætte). False = overskredet."""
    uid = (user_id or "").strip()
    if not uid:
        return True
    t = now if now is not None else time.time()
    try:
        rec = get_runtime_state_value(_rl_key(uid), None)
        stamps = [s for s in (rec.get("ts", []) if isinstance(rec, dict) else []) if t - s < 60.0]
        stamps.append(t)
        throttles = int(rec.get("throttles", 0)) if isinstance(rec, dict) else 0
        over = len(stamps) > RATE_LIMIT_PER_MIN
        if over:
            throttles += 1
        set_runtime_state_value(_rl_key(uid), {"ts": stamps[-RATE_LIMIT_PER_MIN - 5:], "throttles": throttles})
        return not over
    except Exception:
        return True  # fail-open


def _throttle_count(user_id: str) -> int:
    try:
        rec = get_runtime_state_value(_rl_key((user_id or '').strip()), None)
        return int(rec.get("throttles", 0)) if isinstance(rec, dict) else 0
    except Exception:
        return 0


# ── notifikation til Bjørn (§6) ─────────────────────────────────────────
def _notify_owner(summary: str) -> None:
    try:
        from core.identity.users import get_owner
        owner = get_owner()
        if not owner:
            return
        from core.services import notification_router
        notification_router.deliver_message(
            str(owner.discord_id), f"⚠️ Sikkerhed: {summary}", "reach_out", importance="high")
    except Exception:
        pass


# ── orkestrering (kaldes fra identity_guard.guard_incoming) ─────────────
def process_incoming(message: str, *, session_id: str, user_id: str) -> dict | None:
    """Rate-limit + injection-scan på en indgående besked.

    Returnerer None hvis beskeden må passere, ellers {"action": "locked", "reply": ...}
    (kun rate-limit kan låse her — injection logges men låser ikke). Fail-open."""
    try:
        uid = (user_id or "").strip()
        sid = (session_id or "").strip()

        # 1. Rate-limit
        if uid and not check_rate_limit(uid):
            security_guard.record_abuse(uid, sid, "rate_limit", "medium",
                                        details={"throttles": _throttle_count(uid)})
            if _throttle_count(uid) >= THROTTLES_FOR_LOCK:
                security_guard.escalate_session_lock(uid, sid, "rate-limit x3")
                _notify_owner(f"{uid} rate-limit-låst i session {sid[:12]}")
                return {"action": "locked", "reply": (
                    "Session låst pga. for mange beskeder for hurtigt. Start en ny session.")}
            return {"action": "throttled", "reply": (
                "Du sender beskeder hurtigere end jeg kan følge med — vent et øjeblik. "
                f"(advarsel {_throttle_count(uid)}/{THROTTLES_FOR_LOCK})")}

        # 2. Injection-scan (logger + notificerer, låser IKKE)
        hits = scan_for_injection(message)
        if hits:
            security_guard.record_abuse(uid, sid, "prompt_injection", "high",
                                        details={"patterns": hits[:6]})
            _notify_owner(f"prompt-injection-mønstre {hits[:3]} fra {uid or 'ukendt'} (session {sid[:12]})")
        return None
    except Exception:
        # Fail-open (sikkerhed ≠ DoS, jf. docstring) MEN ikke længere stille: en fejl
        # her betyder rate-limit + injection-scan blev IKKE kørt for beskeden.
        # (Auth-cluster trace-kontrakt, 2026-06-22.)
        logger.warning(
            "abuse_monitor.process_incoming fejlede — besked passerer USCANNET "
            "(fail-open)", exc_info=True,
        )
        return None


def scan_tool_output(text: str, *, source: str = "tool") -> list[str]:
    """Scan eksternt tool-output (web_fetch/web_search) for indlejret injection.
    Returnerer matchede mønstre — kalderen kan vælge at advare/sanitisere."""
    hits = scan_for_injection(text)
    if hits:
        try:
            security_guard.record_abuse("", "", "tool_output_injection", "medium",
                                        details={"source": source, "patterns": hits[:6]})
        except Exception:
            pass
    return hits
