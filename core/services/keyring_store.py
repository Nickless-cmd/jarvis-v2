"""Per-bruger nøgle-håndtering (spec §16.3).

Server-side Jarvis kører headless (ingen OS keyring/dbus på containeren — verificeret),
så nøglemodellen er **KEK/DEK**:
- **KEK** (key-encryption-key, master): genereres + persisteres i runtime.json
  (config/, adskilt fra workspaces/). Forlader aldrig serveren.
- **DEK** (data-encryption-key, per bruger): tilfældig, gemt WRAPPED (AES-256-GCM
  med KEK) i runtime_state-DB. Indlæses kun under brugerens aktive session.

På en desktop med OS keyring bruges den i stedet (get_user_key prøver den først).
PBKDF2-fallback fra password findes til klient-afledte nøgler.

Lifecycle (§16.3): nøgler logges aldrig, sendes aldrig over netværk, persisteres
aldrig i klartekst (KEK i runtime.json bag config-perms; DEK kun wrapped). User-delete
sletter DEK → krypteret data bliver ulæseligt (GDPR §16.7).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

_SERVICE = "jarvis-v2-encryption"
_PBKDF2_ITERATIONS = 600_000
_KEY_BYTES = 32
_KEK_RUNTIME_KEY = "encryption_kek"  # pragma: allowlist secret
_DEK_DB_PREFIX = "user_dek:"


#: Hvor længe proben må vente på nøgleringen. En LÅST SecretService-samling
#: venter på en oplåsnings-dialog der aldrig kommer på en server.
_PROBE_TIMEOUT_S = 2.0
#: Sat når proben hang. Husket for processens levetid, så hvert opslag ikke
#: betaler timeouten igen og efterlader en ny hængende tråd.
_KEYRING_BLOKERET = False


def _keyring():
    global _KEYRING_BLOKERET
    if _KEYRING_BLOKERET:
        return None
    try:
        import keyring
    except Exception:
        return None
    # Proben kører i en daemon-tråd med en frist (12/11-2026). Målt på CT105: den
    # delte bash-session har DBUS_SESSION_BUS_ADDRESS, servicene har ikke. En
    # Python-proces startet derfra fik SecretService, hvis samling er låst, og
    # `get_password` ventede evigt på en oplåsnings-dialog (33 bash-kald på én
    # dag ramte 120 s-timeouten). En probe der hænger er ingen nøgleringe:
    # server-KEK/DEK bruges, som servicene gør. Det beskytter også mod en
    # split-brain-nøgle — var oplåsningen lykkedes, havde `get_user_key` gemt en
    # ANDEN tilfældig nøgle end den server-DEK servicene bruger.
    import threading

    udfald: dict[str, object] = {}

    def _probe() -> None:
        try:
            # Probe-operation: fail-backenden (headless container) består
            # .priority-tjekket men kaster NoKeyringError ved FAKTISK brug. En
            # harmløs lookup afslører det robust → fald tilbage til server-side
            # KEK/DEK.
            keyring.get_keyring().get_password("jarvis-v2-keyring-probe", "probe")
            udfald["ok"] = True
        except Exception:
            udfald["ok"] = False

    traad = threading.Thread(target=_probe, name="keyring-probe", daemon=True)
    traad.start()
    traad.join(_PROBE_TIMEOUT_S)
    if traad.is_alive():
        _KEYRING_BLOKERET = True
        return None
    return keyring if udfald.get("ok") else None


# ── Server-side KEK/DEK (headless) ──────────────────────────────────────────

def _get_or_create_kek() -> bytes:
    """Master-KEK fra runtime.json; genereres + persisteres atomisk ved første brug.

    Læser/skriver SAMME fil (config.SETTINGS_FILE) for symmetri — env-override via
    JARVISX_ENCRYPTION_KEK hvis sat (samme idé som read_runtime_key)."""
    from core.runtime.config import SETTINGS_FILE
    env = os.environ.get("JARVISX_ENCRYPTION_KEK")
    if env:
        return bytes.fromhex(env)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")) if SETTINGS_FILE.is_file() else {}
    except Exception:
        data = {}
    existing = data.get(_KEK_RUNTIME_KEY)
    if existing:
        return bytes.fromhex(str(existing))
    # Generér + persistér (read-modify-write, bevar andre keys, atomisk).
    kek = os.urandom(_KEY_BYTES)
    data[_KEK_RUNTIME_KEY] = kek.hex()
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(SETTINGS_FILE)
    return kek


def _server_get_dek(user_id: str) -> bytes:
    """Hent (eller generér + wrap) en brugers DEK fra DB, unwrapped med KEK."""
    from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    from core.services.encryption import encrypt, decrypt
    kek = _get_or_create_kek()
    db_key = _DEK_DB_PREFIX + user_id
    wrapped_b64 = get_runtime_state_value(db_key, "")
    if isinstance(wrapped_b64, str) and wrapped_b64:
        return decrypt(base64.b64decode(wrapped_b64), kek)
    dek = os.urandom(_KEY_BYTES)
    set_runtime_state_value(db_key, base64.b64encode(encrypt(dek, kek)).decode("ascii"))
    return dek


def get_user_key(user_id: str) -> bytes:
    """Brugerens 256-bit DEK. Prøver OS keyring; ellers server-side KEK/DEK (headless)."""
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("user_id påkrævet")
    kr = _keyring()
    if kr is not None:
        stored = kr.get_password(_SERVICE, uid)
        if stored:
            return base64.b64decode(stored)
        key = os.urandom(_KEY_BYTES)
        kr.set_password(_SERVICE, uid, base64.b64encode(key).decode("ascii"))
        return key
    return _server_get_dek(uid)


def delete_user_key(user_id: str) -> bool:
    """Slet en brugers DEK (GDPR §16.7) — krypteret data bliver derefter ulæseligt."""
    uid = str(user_id or "").strip()
    if not uid:
        return False
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(_SERVICE, uid)
            return True
        except Exception:
            return False
    # Server-side: ryd wrapped DEK fra DB.
    try:
        from core.runtime.db import get_runtime_state_value, set_runtime_state_value
        db_key = _DEK_DB_PREFIX + uid
        if not get_runtime_state_value(db_key, ""):
            return False
        set_runtime_state_value(db_key, "")
        return True
    except Exception:
        return False


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 nøgle-derivation (fallback, §16.3). 600k iterationer."""
    return hashlib.pbkdf2_hmac(
        "sha256", str(password or "").encode("utf-8"), salt,
        _PBKDF2_ITERATIONS, dklen=_KEY_BYTES,
    )


def new_salt() -> bytes:
    """Tilfældigt 16-byte salt (gemmes pr. bruger, ikke hemmeligt)."""
    return os.urandom(16)
