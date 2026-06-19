"""QR-device-pairing (mobile companion ↔ desktop). Kort-levende engangs-koder.

Desktop (autentificeret) beder om en pairing-kode → QR med {url, code}. Mobilen
scanner → redeem'er koden → får et friskt Jarvis-token bundet til samme bruger.
Mirror af google_login-mønstret: in-memory, kort TTL, engangs.

Sikkerhed: koden er kort + kortlevende + engangs; redeem udsteder et NYT token
(genbruger ikke desktoppens). GDPR: ingen persondata i koden.
"""
from __future__ import annotations

import secrets
import time

_TTL = 120.0
_CODES: dict[str, dict] = {}
# Indløste koder (code → {at, user_id}) så desktop kan vise "mobil tilsluttet ✓".
# Kort opbevaring; ryddes sammen med udløbne koder.
_REDEEMED: dict[str, dict] = {}


def _gc(now: float) -> None:
    for k in [k for k, v in _CODES.items() if v.get("exp", 0) < now]:
        _CODES.pop(k, None)
    # Glem indløsninger der er ældre end 2× TTL (de er kun til kortvarig UI-feedback).
    for k in [k for k, v in _REDEEMED.items() if v.get("at", 0) < now - 2 * _TTL]:
        _REDEEMED.pop(k, None)


def create_pairing(user_id: str, role: str = "member", *, now: float | None = None) -> dict:
    """Opret en pairing-kode for en (autentificeret) bruger. Returnerer {code, expires_in}."""
    t = now if now is not None else time.time()
    _gc(t)
    if not user_id:
        return {"status": "error", "error": "no_user"}
    code = secrets.token_urlsafe(9)  # kort nok til QR, lang nok mod gæt
    _CODES[code] = {"user_id": user_id, "role": role or "member", "exp": t + _TTL}
    return {"status": "ok", "code": code, "expires_in": int(_TTL)}


def redeem(code: str, *, now: float | None = None) -> dict | None:
    """Indløs en pairing-kode (engangs) → udsted friskt token. None hvis ukendt/udløbet."""
    t = now if now is not None else time.time()
    _gc(t)
    rec = _CODES.pop(code, None)  # engangs
    if not rec or rec.get("exp", 0) < t:
        return None
    from core.runtime.jarvisx_auth import issue_token
    tok = issue_token(user_id=rec["user_id"], role=rec.get("role", "member"))
    _REDEEMED[code] = {"at": t, "user_id": rec["user_id"]}
    return {"status": "ok", "token": tok["token"], "user_id": rec["user_id"], "role": rec.get("role", "member")}


def status(code: str, *, now: float | None = None) -> dict:
    """Status på en pairing-kode (til desktop-poll): redeemed | pending | expired.
    redeemed = mobilen har parret; pending = QR vist, ikke scannet endnu."""
    t = now if now is not None else time.time()
    _gc(t)
    code = (code or "").strip()
    if code in _REDEEMED:
        return {"state": "redeemed"}
    rec = _CODES.get(code)
    if rec and rec.get("exp", 0) >= t:
        return {"state": "pending"}
    return {"state": "expired"}
