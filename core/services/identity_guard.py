"""Identity-mismatch-detection + pushback (spec 2026-06-21 §3, §4).

Den oprindelige bug: Bjørn loggede ind som sin mor (Lotte), skrev "jeg hedder
Bjørn", og Jarvis accepterede det uden verifikation. Enhver kunne dermed bilde
Jarvis ind hvem de er.

Denne guard kører FØR LLM-kaldet på indgående beskeder:
1. Udtræk et eksplicit identitets-claim ("jeg hedder X" / "mit navn er X" / ...).
2. Hvis X matcher en ANDEN kendt bruger end sessionens ejer → mismatch.
3. Hvis override er aktivt (TOTP-verificeret) → claim'et er legitimt → ingen pushback.
4. Ellers: pushback + tæl. 3x ignoreret i samme session → session-lock (eskalering).

Hybrid (§5.3): her er kun pattern-laget (first-pass). LLM-fallback for subtile
forsøg kan lægges ovenpå senere; pattern fanger de åbenlyse spoofs.
"""
from __future__ import annotations

import re

from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services import override_store, security_guard

# Stærke navne-erklæringer (lav falsk-positiv): kræver et eksplicit "hedder/navn".
# "jeg er X" UDELADES bevidst — det rammer "jeg er træt" osv.
_CLAIM_PATTERNS = [
    re.compile(r"\bjeg\s+hedder\s+([A-Za-zÆØÅæøå]{2,20})", re.IGNORECASE),
    re.compile(r"\bmit\s+navn\s+er\s+([A-Za-zÆØÅæøå]{2,20})", re.IGNORECASE),
    re.compile(r"\bdet\s+(?:her\s+)?er\s+([A-Za-zÆØÅæøå]{2,20})(?:\s+der\s+skriver)?\b", re.IGNORECASE),
    re.compile(r"\bmy\s+name\s+is\s+([A-Za-zÆØÅæøå]{2,20})", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+([A-Za-zÆØÅæøå]{2,20})\s+speaking", re.IGNORECASE),
    re.compile(r"\bi['´]?m\s+called\s+([A-Za-zÆØÅæøå]{2,20})", re.IGNORECASE),
]

_PUSHBACK_KEY = "identity_pushback:"


def extract_claimed_name(message: str) -> str | None:
    """Returnér det erklærede navn (normaliseret, Title-case) eller None."""
    text = message or ""
    for pat in _CLAIM_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group(1).strip()
            if name:
                return name[:1].upper() + name[1:].lower()
    return None


def _known_user_names() -> dict[str, str]:
    """Map normaliseret display-navn → user_id, fra users.json (best-effort)."""
    out: dict[str, str] = {}
    try:
        from core.identity.users import load_users
        for u in load_users() or []:
            nm = str(getattr(u, "name", "") or "").strip()
            uid = str(getattr(u, "discord_id", "") or "").strip()
            if nm and uid:
                out[nm.lower()] = uid
    except Exception:
        pass
    return out


def _pushback_count(session_id: str) -> int:
    try:
        v = get_runtime_state_value(_PUSHBACK_KEY + session_id, None)
        return int(v.get("count", 0)) if isinstance(v, dict) else 0
    except Exception:
        return 0


def _bump_pushback(session_id: str) -> int:
    n = _pushback_count(session_id) + 1
    try:
        set_runtime_state_value(_PUSHBACK_KEY + session_id, {"count": n})
    except Exception:
        pass
    return n


def reset_pushback(session_id: str) -> None:
    try:
        set_runtime_state_value(_PUSHBACK_KEY + session_id, {"count": 0})
    except Exception:
        pass


def _display_name_for(user_id: str) -> str:
    uid = (user_id or "").strip()
    if not uid:
        return ""
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(uid)
        return str(getattr(u, "name", "") or "") if u else ""
    except Exception:
        return ""


def guard_incoming(message: str, *, session_id: str, user_id: str) -> dict | None:
    """Samlet gate FØR LLM-kald: (1) låst session/konto → mute, (2) identity-mismatch
    → pushback/lock. Returnerer None hvis beskeden må passere normalt.

    Fail-open: en exception må aldrig spærre normal chat (sikkerhed ≠ selvmål-DoS)."""
    try:
        sid = (session_id or "").strip()
        if security_guard.is_session_locked(sid):
            return {"action": "locked", "reply": (
                "Denne session er låst. Start en ny session for at tale med Jarvis igen.")}
        if user_id and security_guard.is_account_locked(user_id):
            return {"action": "locked", "reply": (
                "Din konto er midlertidigt låst efter gentagne sikkerheds-hændelser. "
                "Kontakt ejeren (Bjørn) for at låse op.")}
        # Rate-limit + prompt-injection-scan (logger/notificerer; rate-limit kan låse).
        try:
            from core.services import abuse_monitor
            _ab = abuse_monitor.process_incoming(message, session_id=sid, user_id=user_id)
            if _ab is not None:
                return _ab
        except Exception:
            pass
        return check_identity(
            message, session_id=sid, session_user_id=user_id,
            session_display_name=_display_name_for(user_id),
        )
    except Exception:
        return None


def check_identity(
    message: str, *, session_id: str, session_user_id: str, session_display_name: str = "",
) -> dict | None:
    """Kør identity-guard på en indgående besked.

    Returnerer None hvis alt er fint (normal tur). Ellers et dict:
      {"action": "pushback"|"locked", "reply": <besked til brugeren>}.

    `session_user_id`/`session_display_name` = den FAKTISKE ejer af sessionen
    (fra auth/users.json), IKKE hvad beskeden påstår.
    """
    sid = (session_id or "").strip()
    claimed = extract_claimed_name(message)
    if not claimed or not sid:
        return None

    # Override aktivt → personen er TOTP-verificeret som owner → claim legitimt.
    try:
        if override_store.is_active(sid):
            return None
    except Exception:
        pass

    # Matcher claim'et sessionens egen ejer? Så er det ikke spoofing.
    owner_name = (session_display_name or "").strip().lower()
    if owner_name and claimed.lower() == owner_name:
        return None

    # Matcher claim'et en ANDEN kendt bruger? (det er den farlige spoof —
    # særligt at udgive sig for owner). Ukendte navne ignoreres (lav falsk-positiv).
    known = _known_user_names()
    claimed_uid = known.get(claimed.lower())
    if not claimed_uid or claimed_uid == (session_user_id or "").strip():
        return None  # ukendt navn eller = sessionens egen ejer → ingen mismatch

    # Ægte mismatch: nogen i en session der tilhører A påstår at være B (kendt bruger).
    n = _bump_pushback(sid)
    security_guard.record_abuse(
        session_user_id, sid, "identity_spoof", "high",
        details={"claimed": claimed, "claimed_uid": claimed_uid, "attempt": n},
    )
    security_guard.record_audit(session_user_id, "identity_pushback", session_id=sid,
                                details={"claimed": claimed, "attempt": n})

    if n >= security_guard.PUSHBACK_LIMIT:
        result = security_guard.escalate_session_lock(
            session_user_id, sid, reason=f"identity-spoof x{n} (claimed {claimed})")
        reset_pushback(sid)
        locked_msg = (
            f"Denne session er nu låst efter gentagne uverificerede identitets-påstande. "
            f"Start en ny session for at tale med Jarvis igen."
        )
        if result == "account_lockdown":
            locked_msg = (
                "Din konto er midlertidigt låst efter gentagne uverificerede "
                "identitets-påstande. Kontakt ejeren for at låse op."
            )
        return {"action": "locked", "reply": locked_msg}

    return {
        "action": "pushback",
        "reply": (
            f"Jeg kan se at denne session tilhører **{session_display_name or 'en anden bruger'}**. "
            f"Hvis du faktisk er **{claimed}**, skal du verificere dig med `!override <din TOTP-kode>` "
            f"før jeg behandler dig som {claimed}. (Forsøg {n}/{security_guard.PUSHBACK_LIMIT})"
        ),
    }
