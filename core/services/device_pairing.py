"""QR-device-pairing (mobile companion ↔ desktop). Kort-levende engangs-koder.

19/9-2026 (Codex' fjernstyring): koden oprettes først EFTER at brugeren på
computeren har sagt «Tillad» og givet en totrinskode (`kraev_totp`), og den
indløste telefon registreres som enhed (se `redeem`).

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


def redeem(code: str, *, navn: str = "", platform: str = "", now: float | None = None) -> dict | None:
    """Indløs en pairing-kode (engangs) → udsted friskt token. None hvis ukendt/udløbet.

    19/9-2026: telefonen bliver en ENHED (core.runtime.db_devices). Dens id står
    i tokenet som `enhed` — det er dét der gør den synlig i desk's enhedsliste,
    lader den fjernes for sig, og åbner code mode når enheds-reglen er tændt.
    Tokenet får også et `jti`, som ethvert fornyet token har.
    """
    t = now if now is not None else time.time()
    _gc(t)
    rec = _CODES.pop(code, None)  # engangs
    if not rec or rec.get("exp", 0) < t:
        return None
    import uuid
    from core.runtime.db_devices import registrer_telefon
    from core.runtime.jarvisx_auth import issue_token
    enhed = registrer_telefon(rec["user_id"], navn=navn, platform=platform)
    tok = issue_token(
        user_id=rec["user_id"], role=rec.get("role", "member"),
        extra_claims={"jti": uuid.uuid4().hex, "enhed": enhed["id"]},
    )
    _REDEEMED[code] = {"at": t, "user_id": rec["user_id"], "navn": enhed["navn"]}
    return {"status": "ok", "token": tok["token"], "user_id": rec["user_id"],
            "role": rec.get("role", "member"), "enhed": enhed["id"]}


def status(code: str, *, now: float | None = None) -> dict:
    """Status på en pairing-kode (til desktop-poll): redeemed | pending | expired.
    redeemed = mobilen har parret; pending = QR vist, ikke scannet endnu."""
    t = now if now is not None else time.time()
    _gc(t)
    code = (code or "").strip()
    if code in _REDEEMED:
        return {"state": "redeemed", "navn": _REDEEMED[code].get("navn", "")}
    rec = _CODES.get(code)
    if rec and rec.get("exp", 0) >= t:
        return {"state": "pending"}
    return {"state": "expired"}


class TotpFejl(Exception):
    """Parring afvist: ingen totrinsbekræftelse sat op, forkert kode eller for mange forsøg."""

    def __init__(self, besked: str, kode: int) -> None:
        super().__init__(besked)
        self.kode = kode


def kraev_totp(user_id: str, kode: str) -> None:
    """Codex kræver MFA for at forbinde en enhed; vi kræver brugerens TOTP.

    Uden en TOTP-nøgle kan der ikke parres — «slå totrinsbekræftelse til
    først», som Codex' «Fortsæt på chatgpt.com». Tre forsøg pr. 5 min.
    """
    from core.identity.users import get_totp_seed
    from core.services.totp_verifier import record_attempt, verify
    seed = get_totp_seed(discord_id=user_id)
    if not seed:
        raise TotpFejl("Slå totrinsbekræftelse til først (Indstillinger → Konto), så kan du tilføje enheder.", 412)
    if not record_attempt(f"enhed:{user_id}"):
        raise TotpFejl("For mange forsøg — vent fem minutter.", 429)
    if not verify(kode, seed=seed):
        raise TotpFejl("Forkert totrinskode.", 403)
