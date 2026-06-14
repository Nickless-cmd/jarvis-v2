"""TOTP-verifikation (RFC 6238) til owner-override — ren stdlib, ingen dependency.

Bruges når Bjørn skal hæve sig til owner i en fremmed sessions-kontekst
(`!override <6-cifret kode>`, spec §6.3). pyotp er ikke i miljøet, så dette er
en ren hmac/base32-impl — færre afhængigheder, bedre secrets-hygiejne.

- `generate_seed()` — ny 16-byte base32-nøgle (vises som QR i app-setup, §6.2).
- `generate_code(seed, timestamp)` — 6-cifret TOTP for et tidspunkt (test + display).
- `verify(code, seed, now, valid_window)` — match mod ±valid_window vinduer (§9 clock drift).
- `record_attempt(session_id, now)` — rate-limit 3/5 min pr. session (§9).
- `revoke(seed)` — returnér ny nøgle (owner kalder ved kompromittering, §9).

Determinisme i tests via injicérbar `now`/`timestamp`. Ingen seed → alt afvises.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from collections import deque

_PERIOD = 30  # sekunder pr. TOTP-vindue (RFC 6238 standard)
_DIGITS = 6
_RATE_MAX = 3          # forsøg
_RATE_WINDOW = 300     # sekunder (5 min)


def _b32_decode(seed: str) -> bytes:
    """Dekodér base32-seed; tilføj padding + uppercase. Tom/ugyldig → b''."""
    if not seed:
        return b""
    s = seed.strip().replace(" ", "").upper()
    s += "=" * (-len(s) % 8)
    try:
        return base64.b32decode(s, casefold=True)
    except Exception:
        return b""


def _hotp(key: bytes, counter: int) -> str:
    """RFC 4226 HOTP — HMAC-SHA1 + dynamic truncation → _DIGITS cifre."""
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** _DIGITS)).zfill(_DIGITS)


def generate_code(seed: str, *, timestamp: float | None = None) -> str:
    """6-cifret TOTP for `seed` på `timestamp` (default: nu)."""
    key = _b32_decode(seed)
    if not key:
        return ""
    ts = time.time() if timestamp is None else timestamp
    counter = int(ts // _PERIOD)
    return _hotp(key, counter)


def verify(
    code: str | None,
    *,
    seed: str | None,
    now: float | None = None,
    valid_window: int = 1,
) -> bool:
    """True hvis `code` matcher TOTP for `seed` inden for ±valid_window vinduer.

    valid_window=1 → nuværende + 1 tidligere + 1 fremtidig = 90 sek (§6.3/§9).
    Ingen seed → False (override deaktiveret til seed er sat).
    """
    key = _b32_decode(seed or "")
    if not key or not code:
        return False
    code = str(code).strip()
    if len(code) != _DIGITS or not code.isdigit():
        return False
    ts = time.time() if now is None else now
    base = int(ts // _PERIOD)
    for drift in range(-valid_window, valid_window + 1):
        if hmac.compare_digest(_hotp(key, base + drift), code):
            return True
    return False


def generate_seed() -> str:
    """Ny tilfældig 16-byte base32-nøgle (uden padding) til QR-setup."""
    raw = os.urandom(16)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def provisioning_uri(seed: str, *, account: str, issuer: str = "Jarvis") -> str:
    """Byg en otpauth://-URI som authenticator-apps (Google Authenticator, Authy,
    2FAS) kan scanne fra QR eller indtaste. RFC 6238 / Key Uri Format.

    `account` = bruger-label (fx "Bjørn"); `issuer` = tjeneste-navn ("Jarvis").
    """
    from urllib.parse import quote
    label = quote(f"{issuer}:{account}")
    params = f"secret={seed}&issuer={quote(issuer)}&algorithm=SHA1&digits={_DIGITS}&period={_PERIOD}"
    return f"otpauth://totp/{label}?{params}"


def revoke(_old_seed: str | None = None) -> str:
    """Returnér en ny seed. Caller (owner-session) persisterer den + smider den gamle.

    Den gamle seed bruges ikke videre — argumentet findes kun for kald-symmetri/audit.
    """
    return generate_seed()


# In-memory rate-limit pr. session. Cross-proces er ikke nødvendigt: rate-limit
# er en lokal misbrugs-bremse, ikke en autoritets-kilde (override-state ligger i
# override_store, Task 2.2).
_ATTEMPTS: dict[str, deque[float]] = {}


def record_attempt(session_id: str, *, now: float | None = None) -> bool:
    """Registrér et override-forsøg. True hvis tilladt, False hvis rate-limited.

    Maks _RATE_MAX forsøg pr. _RATE_WINDOW sekunder pr. session (§9).
    """
    if not session_id:
        return False
    ts = time.time() if now is None else now
    dq = _ATTEMPTS.setdefault(session_id, deque())
    cutoff = ts - _RATE_WINDOW
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= _RATE_MAX:
        return False
    dq.append(ts)
    return True
