# User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rigtig brugerstyring for Jarvis: SQLite-brugerdb med krypterede kolonner, selvregistrering + email-verifikation, login med JWT, GDPR soft/hard-delete, og kvote-tiers — med owner-only admin-API.

**Architecture:** En ny SQLite-`users`-tabel (db.py-helpers) er autoritativ for auth/kvote/GDPR-data. Følsomme felter (email, totp_seed, discord_id) krypteres per-bruger med `keyring_store.get_user_key` + `encryption.encrypt`; et deterministisk `email_hash` (HMAC-SHA256) giver login-opslag uden at dekryptere. `user_db.py` er den højniveau-adapter; `email_verify.py` håndterer verifikations-tokens; nye `auth.py`/`users.py`-routes eksponerer flowet. Den eksisterende `users.json`/`users.py` (Discord-identitet) bevares uændret i denne leverance — en migration kopierer eksisterende brugere ind i tabellen, og en senere cutover re-pointer legacy-læsere (noteret som follow-up; undgår dual-truth-brud ved at gøre tabellen autoritativ for de NYE felter og users.json kun for legacy Discord-mapping).

**Tech Stack:** Python 3.11 (`/opt/conda/envs/ai/bin/python`), pytest, SQLite (`core/runtime/db.py`), `cryptography` (AES-256-GCM via `core/services/encryption.py`), bcrypt 5.0, JWT (`core/runtime/jarvisx_auth.py`), FastAPI. Test: `/opt/conda/envs/ai/bin/python -m pytest -p no:cacheprovider`. DB-tests bruger `isolated_runtime`-fixturen (`tests/conftest.py`).

**Spec:** `docs/superpowers/specs/2026-06-15-user-management-design.md`

**Sikkerhedsgrænse:** Implementeringen håndterer ALDRIG rigtige password-værdier i klartekst udover at hashe dem ved registrering; SMTP-credential læses fra `runtime.json` via `read_runtime_key` (aldrig hardcoded). Hard-delete af andres data kræver owner-TOTP-override.

---

## File Structure

**Backend (`/media/projects/jarvis-v2`):**
- Modify `pyproject.toml` — tilføj `bcrypt>=5.0`.
- Modify `core/runtime/db.py` — `_ensure_users_table` + row-helpers (insert/get/get_by_email_hash/list/update/soft_delete/hard_delete) + kald i `init_db()`.
- Create `core/identity/passwords.py` — bcrypt hash/verify (ren, lille).
- Create `core/identity/user_db.py` — højniveau-adapter: create/get/find_by_email/update/mute/set_quota/soft+hard-delete; kryptér/dekryptér følsomme felter; email_hash.
- Create `core/identity/email_verify.py` — verifikations-token-store + send-mail + verify.
- Modify `core/services/quota_store.py` — `set_user_quota` (læser tier fra user_db).
- Create `apps/api/jarvis_api/routes/auth.py` — register/verify-email/login.
- Create `apps/api/jarvis_api/routes/users.py` — owner-only CRUD + GDPR-erasure.
- Modify `apps/api/jarvis_api/app.py` — registrér de to nye routere.
- Modify `apps/api/jarvis_api/middleware/jarvisx_user_routing.py` — public-paths for register/verify/login.
- Tests: `tests/test_user_db.py`, `tests/test_passwords.py`, `tests/test_email_verify.py`, `tests/test_user_management_routes.py`, `tests/test_quota_store.py` (udvid).

---

## PHASE A — user_db (SQLite-fundament + kryptering + CRUD)

### Task A1: `passwords.py` — bcrypt hash/verify

**Files:**
- Modify: `pyproject.toml`
- Create: `core/identity/passwords.py`
- Test: `tests/test_passwords.py`

- [ ] **Step 1: Add bcrypt to pyproject**

I `pyproject.toml`, find `[project]`-`dependencies`-listen og tilføj linjen (alfabetisk hvor det passer):

```toml
    "bcrypt>=5.0",
```

(bcrypt 5.0 er allerede installeret i conda-miljøet; dette dokumenterer afhængigheden.)

- [ ] **Step 2: Write the failing test**

Create `tests/test_passwords.py`:

```python
"""Tests for password hashing (spec 2026-06-15 §5.2)."""
from __future__ import annotations

from core.identity.passwords import hash_password, verify_password


def test_hash_then_verify_true() -> None:
    h = hash_password("hemmelig123")
    assert isinstance(h, str) and h.startswith("$2")
    assert verify_password("hemmelig123", h) is True


def test_verify_wrong_password_false() -> None:
    h = hash_password("rigtig")
    assert verify_password("forkert", h) is False


def test_two_hashes_of_same_password_differ() -> None:
    assert hash_password("x") != hash_password("x")  # random salt


def test_verify_handles_garbage_hash() -> None:
    assert verify_password("x", "ikke-et-hash") is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_passwords.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.identity.passwords'`

- [ ] **Step 4: Write the implementation**

Create `core/identity/passwords.py`:

```python
"""Password-hashing (spec 2026-06-15 §5.2) — bcrypt, cost-factor 12.

Ren helper: hash + verify. Aldrig logning af klartekst-passwords.
"""
from __future__ import annotations

import bcrypt

_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    """bcrypt-hash (cost 12). Returnerer en utf-8-streng ($2b$…)."""
    h = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS))
    return h.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """True hvis password matcher hash. Fejl-tolerant (ugyldigt hash → False)."""
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_passwords.py -q -p no:cacheprovider`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml core/identity/passwords.py tests/test_passwords.py
git commit -m "feat(users): bcrypt password hashing (§5.2)"
```

---

### Task A2: `users`-tabel + row-helpers i db.py

**Files:**
- Modify: `core/runtime/db.py` (ny `_ensure_users_table` + helpers; kald i `init_db()`)
- Test: `tests/test_user_db.py` (del 1 — rå row-lag)

Row-laget er rent SQL: ingen kryptering her (det ligger i user_db.py, Task A3). Tabellen lagrer allerede-krypterede/hashede værdier.

- [ ] **Step 1: Write the failing test**

Create `tests/test_user_db.py`:

```python
"""Tests for users-tabellen + user_db-adapter (spec 2026-06-15)."""
from __future__ import annotations


def test_insert_and_get_user_row(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, get_user_row
    insert_user_row(
        user_id="u1", email_hash="h1", email_enc=b"E", name="Bjørn",
        role="owner", workspace="bjorn", password_hash="$2b$x",
        discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t",
    )
    r = get_user_row("u1")
    assert r is not None
    assert r["email_hash"] == "h1"
    assert r["role"] == "owner"
    assert r["email_verified"] == 0
    assert r["muted"] == 0
    assert r["deleted_at"] is None


def test_get_user_row_by_email_hash(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, get_user_row_by_email_hash
    insert_user_row(user_id="u2", email_hash="hh", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    r = get_user_row_by_email_hash("hh")
    assert r is not None and r["user_id"] == "u2"


def test_update_user_fields(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, update_user_row, get_user_row
    insert_user_row(user_id="u3", email_hash="h3", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    update_user_row("u3", {"email_verified": 1, "muted": 1, "tier": "plus", "updated_at": "t2"})
    r = get_user_row("u3")
    assert r["email_verified"] == 1 and r["muted"] == 1 and r["tier"] == "plus"


def test_soft_delete_sets_timestamp(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, soft_delete_user_row, get_user_row
    insert_user_row(user_id="u4", email_hash="h4", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    soft_delete_user_row("u4", deleted_at="gone")
    assert get_user_row("u4")["deleted_at"] == "gone"


def test_hard_delete_removes_row(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, hard_delete_user_row, get_user_row
    insert_user_row(user_id="u5", email_hash="h5", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    assert hard_delete_user_row("u5") is True
    assert get_user_row("u5") is None


def test_list_users_excludes_soft_deleted_by_default(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, soft_delete_user_row, list_user_rows
    insert_user_row(user_id="a", email_hash="ha", email_enc=b"", name="x", role="member",
                    workspace="a", password_hash="p", discord_id_enc=b"", totp_seed_enc=b"",
                    created_at="t", updated_at="t")
    insert_user_row(user_id="b", email_hash="hb", email_enc=b"", name="y", role="member",
                    workspace="b", password_hash="p", discord_id_enc=b"", totp_seed_enc=b"",
                    created_at="t", updated_at="t")
    soft_delete_user_row("b", deleted_at="gone")
    ids = {r["user_id"] for r in list_user_rows()}
    assert ids == {"a"}
    ids_all = {r["user_id"] for r in list_user_rows(include_deleted=True)}
    assert ids_all == {"a", "b"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider`
Expected: FAIL — `cannot import name 'insert_user_row' from 'core.runtime.db'`

- [ ] **Step 3: Implement row-helpers in db.py**

Tilføj nær de øvrige `_ensure_*_table`-funktioner i `core/runtime/db.py` (fx i nærheden af `_ensure_private_brain_records_table`):

```python
def _ensure_users_table(conn: sqlite3.Connection) -> None:
    """Idempotent: brugerstyring (spec 2026-06-15). Følsomme felter lagres
    krypteret (email_enc/discord_id_enc/totp_seed_enc); email_hash er et
    deterministisk opslags-hash så login kan finde brugeren uden at dekryptere."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            email_hash TEXT NOT NULL UNIQUE,
            email_enc BLOB NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            workspace TEXT NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            discord_id_enc BLOB NOT NULL DEFAULT x'',
            totp_seed_enc BLOB NOT NULL DEFAULT x'',
            email_verified INTEGER NOT NULL DEFAULT 0,
            tier TEXT NOT NULL DEFAULT '',
            muted INTEGER NOT NULL DEFAULT 0,
            consent_data_processing INTEGER NOT NULL DEFAULT 0,
            consent_marketing INTEGER NOT NULL DEFAULT 0,
            consent_blind_access INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
        """
    )
    conn.commit()


def insert_user_row(
    *, user_id: str, email_hash: str, email_enc: bytes, name: str, role: str,
    workspace: str, password_hash: str, discord_id_enc: bytes, totp_seed_enc: bytes,
    created_at: str, updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_users_table(conn)
        conn.execute(
            """
            INSERT INTO users
                (user_id, email_hash, email_enc, name, role, workspace,
                 password_hash, discord_id_enc, totp_seed_enc, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, email_hash, email_enc, name, role, workspace,
             password_hash, discord_id_enc, totp_seed_enc, created_at, updated_at),
        )
        conn.commit()
    return get_user_row(user_id) or {}


def get_user_row(user_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_users_table(conn)
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_row_by_email_hash(email_hash: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_users_table(conn)
        row = conn.execute("SELECT * FROM users WHERE email_hash = ?", (email_hash,)).fetchone()
    return dict(row) if row else None


_USER_UPDATABLE = {
    "email_hash", "email_enc", "name", "role", "workspace", "password_hash",
    "discord_id_enc", "totp_seed_enc", "email_verified", "tier", "muted",
    "consent_data_processing", "consent_marketing", "consent_blind_access",
    "updated_at", "deleted_at",
}


def update_user_row(user_id: str, fields: dict[str, object]) -> bool:
    cols = [(k, v) for k, v in fields.items() if k in _USER_UPDATABLE]
    if not cols:
        return False
    set_clause = ", ".join(f"{k} = ?" for k, _ in cols)
    params = [v for _, v in cols] + [user_id]
    with connect() as conn:
        _ensure_users_table(conn)
        cur = conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", params)
        conn.commit()
    return cur.rowcount > 0


def soft_delete_user_row(user_id: str, *, deleted_at: str) -> bool:
    return update_user_row(user_id, {"deleted_at": deleted_at})


def hard_delete_user_row(user_id: str) -> bool:
    with connect() as conn:
        _ensure_users_table(conn)
        cur = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    return cur.rowcount > 0


def list_user_rows(*, include_deleted: bool = False) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_users_table(conn)
        where = "" if include_deleted else "WHERE deleted_at IS NULL"
        rows = conn.execute(f"SELECT * FROM users {where} ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]
```

Registrér tabellen i `init_db()` (find funktionen i db.py og tilføj et kald sammen med de øvrige `_ensure_*_table(conn)`-kald inde i `with connect() as conn:`-blokken):

```python
        _ensure_users_table(conn)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_user_db.py
git commit -m "feat(users): SQLite users-tabel + row-helpers (krypterede kolonner)"
```

---

### Task A3: `user_db.py` — adapter med kryptering + email_hash

**Files:**
- Create: `core/identity/user_db.py`
- Test: `tests/test_user_db.py` (del 2 — adapter)

- [ ] **Step 1: Write the failing test**

Tilføj i `tests/test_user_db.py`:

```python
def test_create_user_roundtrip_decrypts_email(isolated_runtime) -> None:
    from core.identity.user_db import create_user, get_user
    u = create_user(email="Bjorn@Example.com ", name="Bjørn", password="hemmelig",
                    role="owner", workspace="bjorn")
    assert u["email"] == "bjorn@example.com"  # normaliseret + dekrypteret
    assert u["email_verified"] is False
    got = get_user(u["user_id"])
    assert got["email"] == "bjorn@example.com"
    assert got["name"] == "Bjørn"


def test_find_user_by_email_is_case_insensitive(isolated_runtime) -> None:
    from core.identity.user_db import create_user, find_user_by_email
    create_user(email="a@b.dk", name="A", password="x", role="member", workspace="a")
    assert find_user_by_email("A@B.DK") is not None
    assert find_user_by_email("nope@b.dk") is None


def test_duplicate_email_rejected(isolated_runtime) -> None:
    import pytest
    from core.identity.user_db import create_user
    create_user(email="dup@b.dk", name="A", password="x", role="member", workspace="a")
    with pytest.raises(ValueError):
        create_user(email="DUP@b.dk", name="B", password="y", role="member", workspace="b")


def test_verify_login_checks_password(isolated_runtime) -> None:
    from core.identity.user_db import create_user, verify_login
    create_user(email="l@b.dk", name="L", password="rigtig", role="member", workspace="l")
    ok = verify_login("l@b.dk", "rigtig")
    assert ok is not None and ok["email"] == "l@b.dk"
    assert verify_login("l@b.dk", "forkert") is None
    assert verify_login("ukendt@b.dk", "x") is None


def test_mute_and_set_quota(isolated_runtime) -> None:
    from core.identity.user_db import create_user, mute_user, unmute_user, set_quota_tier, get_user
    u = create_user(email="m@b.dk", name="M", password="x", role="member", workspace="m")
    uid = u["user_id"]
    mute_user(uid)
    assert get_user(uid)["muted"] is True
    unmute_user(uid)
    assert get_user(uid)["muted"] is False
    set_quota_tier(uid, "pro")
    assert get_user(uid)["tier"] == "pro"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider -k "roundtrip or by_email or duplicate or login or mute"`
Expected: FAIL — `No module named 'core.identity.user_db'`

- [ ] **Step 3: Write the implementation**

Create `core/identity/user_db.py`:

```python
"""Højniveau-bruger-adapter (spec 2026-06-15) ovenpå users-tabellen.

Følsomme felter (email, discord_id, totp_seed) krypteres per-bruger med
keyring_store.get_user_key + encryption.encrypt. email_hash (HMAC-SHA256 over
normaliseret email + en server-pepper) er deterministisk så login kan slå op
uden at dekryptere alle brugere. Aldrig klartekst-password lagret (kun bcrypt).
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any

from core.identity.passwords import hash_password, verify_password
from core.runtime.secrets import read_runtime_key
from core.services.encryption import decrypt, encrypt
from core.services.keyring_store import get_user_key
from core.runtime import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _email_hash(email: str) -> str:
    """Deterministisk opslags-hash. Pepper fra runtime (eller fast fallback)."""
    try:
        pepper = str(read_runtime_key("user_email_pepper"))
    except Exception:
        pepper = "jarvis-user-email-pepper-v1"
    return hmac.new(pepper.encode("utf-8"), _norm_email(email).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _enc(user_id: str, value: str) -> bytes:
    if not value:
        return b""
    return encrypt(value.encode("utf-8"), get_user_key(user_id))


def _dec(user_id: str, blob: bytes | None) -> str:
    if not blob:
        return ""
    try:
        return decrypt(bytes(blob), get_user_key(user_id)).decode("utf-8")
    except Exception:
        return ""


def _row_to_public(row: dict[str, Any]) -> dict[str, Any]:
    uid = str(row["user_id"])
    return {
        "user_id": uid,
        "email": _dec(uid, row.get("email_enc")),
        "name": row.get("name", ""),
        "role": row.get("role", "member"),
        "workspace": row.get("workspace", ""),
        "discord_id": _dec(uid, row.get("discord_id_enc")),
        "email_verified": bool(row.get("email_verified")),
        "tier": row.get("tier", "") or "",
        "muted": bool(row.get("muted")),
        "consent_data_processing": bool(row.get("consent_data_processing")),
        "consent_marketing": bool(row.get("consent_marketing")),
        "consent_blind_access": bool(row.get("consent_blind_access")),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "deleted_at": row.get("deleted_at"),
    }


def create_user(*, email: str, name: str, password: str, role: str = "member",
                workspace: str | None = None) -> dict[str, Any]:
    norm = _norm_email(email)
    if not norm:
        raise ValueError("email påkrævet")
    eh = _email_hash(norm)
    if db.get_user_row_by_email_hash(eh):
        raise ValueError("email allerede registreret")
    user_id = uuid.uuid4().hex
    ws = workspace or user_id
    now = _now()
    db.insert_user_row(
        user_id=user_id, email_hash=eh, email_enc=_enc(user_id, norm), name=name,
        role=role, workspace=ws, password_hash=hash_password(password),
        discord_id_enc=b"", totp_seed_enc=b"", created_at=now, updated_at=now,
    )
    return get_user(user_id)  # type: ignore[return-value]


def get_user(user_id: str) -> dict[str, Any] | None:
    row = db.get_user_row(user_id)
    return _row_to_public(row) if row else None


def find_user_by_email(email: str) -> dict[str, Any] | None:
    row = db.get_user_row_by_email_hash(_email_hash(email))
    return _row_to_public(row) if row else None


def verify_login(email: str, password: str) -> dict[str, Any] | None:
    row = db.get_user_row_by_email_hash(_email_hash(email))
    if not row or row.get("deleted_at"):
        return None
    if not verify_password(password, str(row.get("password_hash") or "")):
        return None
    return _row_to_public(row)


def set_email_verified(user_id: str, verified: bool = True) -> bool:
    return db.update_user_row(user_id, {"email_verified": 1 if verified else 0,
                                        "updated_at": _now()})


def mute_user(user_id: str) -> bool:
    return db.update_user_row(user_id, {"muted": 1, "updated_at": _now()})


def unmute_user(user_id: str) -> bool:
    return db.update_user_row(user_id, {"muted": 0, "updated_at": _now()})


def set_quota_tier(user_id: str, tier: str) -> bool:
    if tier not in ("free", "plus", "pro", "owner"):
        raise ValueError(f"ukendt tier '{tier}'")
    return db.update_user_row(user_id, {"tier": tier, "updated_at": _now()})


def set_consent(user_id: str, *, data_processing: bool | None = None,
                marketing: bool | None = None, blind_access: bool | None = None) -> bool:
    fields: dict[str, Any] = {"updated_at": _now()}
    if data_processing is not None:
        fields["consent_data_processing"] = 1 if data_processing else 0
    if marketing is not None:
        fields["consent_marketing"] = 1 if marketing else 0
    if blind_access is not None:
        fields["consent_blind_access"] = 1 if blind_access else 0
    return db.update_user_row(user_id, fields)


def list_users(*, include_deleted: bool = False) -> list[dict[str, Any]]:
    return [_row_to_public(r) for r in db.list_user_rows(include_deleted=include_deleted)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider`
Expected: PASS (alle, inkl. de nye)

- [ ] **Step 5: Commit**

```bash
git add core/identity/user_db.py tests/test_user_db.py
git commit -m "feat(users): user_db adapter — kryptering + email_hash + CRUD"
```

---

## PHASE B — Registrering + email-verifikation

### Task B1: `email_verify.py` — token-store + send + verify

**Files:**
- Create: `core/identity/email_verify.py`
- Test: `tests/test_email_verify.py`

Verifikations-tokens lagres i `runtime_state_kv` via db (samme nøgle-mønster som ui_panel_store): nøgle `email_verify_tokens` → liste af `{token, user_id, expires_at, created_day}`. Max 3 oprettelser pr. email pr. dag.

- [ ] **Step 1: Write the failing test**

Create `tests/test_email_verify.py`:

```python
"""Tests for email-verifikation (spec 2026-06-15 §5)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def test_create_and_consume_token(isolated_runtime) -> None:
    from core.identity.email_verify import create_token, consume_token
    tok = create_token(user_id="u1", email="a@b.dk")
    assert tok and isinstance(tok, str)
    uid = consume_token(tok)
    assert uid == "u1"
    # Token kan kun bruges én gang
    assert consume_token(tok) is None


def test_expired_token_rejected(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    tok = email_verify.create_token(user_id="u2", email="c@b.dk", ttl_hours=-1)
    assert email_verify.consume_token(tok) is None


def test_rate_limit_three_per_email_per_day(isolated_runtime) -> None:
    from core.identity.email_verify import create_token, RateLimited
    import pytest
    for _ in range(3):
        create_token(user_id="u3", email="rate@b.dk")
    with pytest.raises(RateLimited):
        create_token(user_id="u3", email="rate@b.dk")


def test_send_verification_email_uses_mail_sender(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    sent = {}

    def fake_send(args):
        sent.update(args)
        return {"success": True}

    monkeypatch.setattr(email_verify, "_send_mail", fake_send)
    tok = email_verify.send_verification_email(user_id="u4", email="dest@b.dk",
                                               base_url="https://jarvis.srvlab.dk")
    assert sent["to"] == "dest@b.dk"
    assert tok in sent["body"]
    assert "verify" in sent["body"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_email_verify.py -q -p no:cacheprovider`
Expected: FAIL — `No module named 'core.identity.email_verify'`

- [ ] **Step 3: Write the implementation**

Create `core/identity/email_verify.py`:

```python
"""Email-verifikation (spec 2026-06-15 §5). Token-store i runtime_state_kv,
24h TTL, max 3 pr. email pr. dag. Sender via den eksisterende mail-opsætning
(mail_tools._exec_send_mail → SMTP 587/STARTTLS, credential fra runtime.json).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "email_verify_tokens"
_MAX_PER_DAY = 3


class RateLimited(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _now().date().isoformat()


def _load() -> list[dict]:
    raw = get_runtime_state_value(_KEY, [])
    return raw if isinstance(raw, list) else []


def _save(items: list[dict]) -> None:
    set_runtime_state_value(_KEY, items[-500:])


def create_token(*, user_id: str, email: str, ttl_hours: int = 24) -> str:
    items = _load()
    day = _today()
    em = (email or "").strip().lower()
    used_today = sum(1 for r in items if r.get("email") == em and r.get("created_day") == day)
    if used_today >= _MAX_PER_DAY:
        raise RateLimited(f"max {_MAX_PER_DAY} verifikations-mails pr. dag for {em}")
    token = uuid.uuid4().hex
    expires = (_now() + timedelta(hours=ttl_hours)).isoformat()
    items.append({"token": token, "user_id": str(user_id), "email": em,
                  "expires_at": expires, "created_day": day})
    _save(items)
    return token


def consume_token(token: str) -> str | None:
    """Returnér user_id hvis token er gyldigt + ikke udløbet; fjern det (engangs)."""
    items = _load()
    now = _now()
    found = None
    rest = []
    for r in items:
        if r.get("token") == token and found is None:
            try:
                exp = datetime.fromisoformat(str(r.get("expires_at")))
            except Exception:
                exp = now - timedelta(seconds=1)
            if exp > now:
                found = str(r.get("user_id"))
            # forbruges uanset (udløbet token fjernes også)
            continue
        rest.append(r)
    if found is not None or len(rest) != len(items):
        _save(rest)
    return found


def _send_mail(args: dict) -> dict:
    from core.tools.mail_tools import _exec_send_mail
    return _exec_send_mail(args)


def send_verification_email(*, user_id: str, email: str, base_url: str) -> str:
    token = create_token(user_id=user_id, email=email)
    link = f"{base_url.rstrip('/')}/api/auth/verify-email?token={token}"
    body = (
        "Hej!\n\nBekræft din email for at aktivere din Jarvis-konto:\n\n"
        f"{link}\n\nLinket udløber om 24 timer. Hvis du ikke har oprettet en "
        "konto, kan du ignorere denne mail.\n\n— Jarvis"
    )
    _send_mail({"to": email, "subject": "Bekræft din Jarvis-konto", "body": body})
    return token
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_email_verify.py -q -p no:cacheprovider`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/identity/email_verify.py tests/test_email_verify.py
git commit -m "feat(users): email-verifikation — token-store + send (24h, 3/dag)"
```

---

### Task B2: `register_user` i user_db

**Files:**
- Modify: `core/identity/user_db.py`
- Test: `tests/test_user_db.py` (tilføj)

- [ ] **Step 1: Write the failing test**

Tilføj i `tests/test_user_db.py`:

```python
def test_register_user_creates_unverified_and_returns_token(isolated_runtime, monkeypatch) -> None:
    from core.identity import user_db, email_verify
    sent = {}
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: sent.update(a) or {"success": True})
    user, token = user_db.register_user(email="new@b.dk", name="Ny", password="pw",
                                        base_url="https://jarvis.srvlab.dk")
    assert user["email_verified"] is False
    assert token and sent["to"] == "new@b.dk"
    # Verificér via token
    assert user_db.verify_email_token(token) is True
    assert user_db.get_user(user["user_id"])["email_verified"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py::test_register_user_creates_unverified_and_returns_token -q -p no:cacheprovider`
Expected: FAIL — `module 'core.identity.user_db' has no attribute 'register_user'`

- [ ] **Step 3: Implement register_user + verify_email_token**

Tilføj i `core/identity/user_db.py`:

```python
def register_user(*, email: str, name: str, password: str, base_url: str,
                  role: str = "member") -> tuple[dict[str, Any], str]:
    """Selvregistrering: opret bruger (email_verified=0) + send verifikations-mail.
    Returnerer (user, token)."""
    from core.identity import email_verify
    user = create_user(email=email, name=name, password=password, role=role)
    token = email_verify.send_verification_email(
        user_id=user["user_id"], email=user["email"], base_url=base_url)
    return user, token


def verify_email_token(token: str) -> bool:
    """Forbrug et verifikations-token → markér brugeren email_verified."""
    from core.identity import email_verify
    user_id = email_verify.consume_token(token)
    if not user_id:
        return False
    return set_email_verified(user_id, True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/identity/user_db.py tests/test_user_db.py
git commit -m "feat(users): register_user + verify_email_token"
```

---

## PHASE C — Login + auth-routes

### Task C1: `routes/auth.py` — register / verify-email / login

**Files:**
- Create: `apps/api/jarvis_api/routes/auth.py`
- Modify: `apps/api/jarvis_api/app.py` (registrér router)
- Modify: `apps/api/jarvis_api/middleware/jarvisx_user_routing.py` (public paths)
- Test: `tests/test_user_management_routes.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_user_management_routes.py`:

```python
"""Integration-tests for user-management routes (spec 2026-06-15)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client(isolated_runtime):
    from apps.api.jarvis_api.app import create_app
    return TestClient(create_app())


def test_register_then_login_flow(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    captured = {}
    monkeypatch.setattr(email_verify, "_send_mail",
                        lambda a: captured.update(a) or {"success": True})
    c = _client(isolated_runtime)

    r = c.post("/api/auth/register", json={"email": "flow@b.dk", "name": "Flow", "password": "pw123456"})
    assert r.status_code == 200, r.text
    assert r.json()["email_verified"] is False

    # Login før verifikation afvises
    r = c.post("/api/auth/login", json={"email": "flow@b.dk", "password": "pw123456"})
    assert r.status_code == 403

    # Verificér via token fra mailen
    token = captured["body"].split("token=")[1].split()[0].strip()
    r = c.get(f"/api/auth/verify-email?token={token}")
    assert r.status_code == 200 and r.json()["verified"] is True

    # Nu lykkes login + giver en bearer-token
    r = c.post("/api/auth/login", json={"email": "flow@b.dk", "password": "pw123456"})
    assert r.status_code == 200
    assert r.json()["token"]


def test_login_wrong_password_401(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify, user_db
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: {"success": True})
    c = _client(isolated_runtime)
    user, tok = user_db.register_user(email="w@b.dk", name="W", password="rigtig",
                                      base_url="http://t")
    user_db.verify_email_token(tok)
    r = c.post("/api/auth/login", json={"email": "w@b.dk", "password": "forkert"})
    assert r.status_code == 401


def test_register_duplicate_email_409(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: {"success": True})
    c = _client(isolated_runtime)
    c.post("/api/auth/register", json={"email": "d@b.dk", "name": "A", "password": "pw123456"})
    r = c.post("/api/auth/register", json={"email": "d@b.dk", "name": "B", "password": "pw123456"})
    assert r.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_management_routes.py::test_register_then_login_flow -q -p no:cacheprovider`
Expected: FAIL — 404 (ruterne findes ikke endnu)

- [ ] **Step 3: Write the router**

Create `apps/api/jarvis_api/routes/auth.py`:

```python
"""Auth-routes (spec 2026-06-15 §5): register / verify-email / login.

Public (ingen bearer påkrævet). Login kræver email_verified. Password håndteres
kun som hash; klartekst forlader aldrig request-scope.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.identity import user_db
from core.runtime.jarvisx_auth import issue_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    email: str
    name: str
    password: str


class LoginReq(BaseModel):
    email: str
    password: str


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.post("/register")
def register(req: RegisterReq, request: Request) -> JSONResponse:
    try:
        user, _token = user_db.register_user(
            email=req.email, name=req.name, password=req.password,
            base_url=_base_url(request))
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"ok": False, "error": str(exc)})
    return JSONResponse(content={"ok": True, "user_id": user["user_id"],
                                 "email": user["email"], "email_verified": False})


@router.get("/verify-email")
def verify_email(token: str = Query(...)) -> JSONResponse:
    ok = user_db.verify_email_token(token)
    if not ok:
        return JSONResponse(status_code=400,
                            content={"ok": False, "verified": False,
                                     "error": "ugyldigt eller udløbet token"})
    return JSONResponse(content={"ok": True, "verified": True})


@router.post("/login")
def login(req: LoginReq) -> JSONResponse:
    user = user_db.verify_login(req.email, req.password)
    if not user:
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "forkert email eller password"})
    if not user["email_verified"]:
        return JSONResponse(status_code=403,
                            content={"ok": False, "error": "email ikke verificeret"})
    tok = issue_token(user_id=user["user_id"], role=user["role"])
    return JSONResponse(content={"ok": True, "token": tok["token"],
                                 "user_id": user["user_id"], "role": user["role"]})
```

- [ ] **Step 4: Register router + public paths**

I `apps/api/jarvis_api/app.py`, tilføj importen øverst sammen med de øvrige route-imports:

```python
from apps.api.jarvis_api.routes.auth import router as user_auth_router
```

Og registrér den sammen med de øvrige `app.include_router(...)`-kald (fx lige efter `app.include_router(openai_auth_router)`):

```python
    app.include_router(user_auth_router)
```

I `apps/api/jarvis_api/middleware/jarvisx_user_routing.py`, tilføj de nye public paths i `_PUBLIC_PATHS`-tuplen:

```python
    "/api/auth/register",
    "/api/auth/verify-email",
    "/api/auth/login",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_management_routes.py -q -p no:cacheprovider`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/routes/auth.py apps/api/jarvis_api/app.py apps/api/jarvis_api/middleware/jarvisx_user_routing.py tests/test_user_management_routes.py
git commit -m "feat(users): auth-routes register/verify-email/login + JWT"
```

---

## PHASE D — GDPR + kvoter + admin-routes

### Task D1: GDPR-sletning i user_db (soft/hard + audit + keyring)

**Files:**
- Modify: `core/identity/user_db.py`
- Test: `tests/test_user_db.py` (tilføj)

Hard-delete bruger `delete_policy` til at afgøre mode, sletter user-row + brugerens keyring-DEK (så krypteret data bliver ulæseligt, §6.2), og skriver en audit-linje til `runtime_state_kv` (`user_audit_log`).

- [ ] **Step 1: Write the failing test**

Tilføj i `tests/test_user_db.py`:

```python
def test_soft_delete_marks_user(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, get_user
    u = create_user(email="sd@b.dk", name="S", password="x", role="member", workspace="s")
    assert delete_user(u["user_id"], mode="soft", actor="owner") is True
    assert get_user(u["user_id"])["deleted_at"] is not None


def test_hard_delete_removes_user_and_key(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, get_user
    from core.runtime.db import get_user_row
    u = create_user(email="hd@b.dk", name="H", password="x", role="member", workspace="h")
    uid = u["user_id"]
    assert delete_user(uid, mode="hard", actor="owner") is True
    assert get_user(uid) is None
    assert get_user_row(uid) is None


def test_delete_writes_audit_entry(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, read_audit_log
    u = create_user(email="au@b.dk", name="A", password="x", role="member", workspace="a")
    delete_user(u["user_id"], mode="soft", actor="bjorn")
    log = read_audit_log()
    assert any(e["user_id"] == u["user_id"] and e["action"] == "delete:soft"
               and e["actor"] == "bjorn" for e in log)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider -k "soft_delete_marks or hard_delete_removes or audit_entry"`
Expected: FAIL — `module 'core.identity.user_db' has no attribute 'delete_user'`

- [ ] **Step 3: Implement delete_user + audit**

Tilføj i `core/identity/user_db.py`:

```python
_AUDIT_KEY = "user_audit_log"


def _audit(*, user_id: str, action: str, actor: str) -> None:
    from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    log = get_runtime_state_value(_AUDIT_KEY, [])
    if not isinstance(log, list):
        log = []
    log.append({"user_id": user_id, "action": action, "actor": actor, "at": _now()})
    set_runtime_state_value(_AUDIT_KEY, log[-1000:])


def read_audit_log() -> list[dict[str, Any]]:
    from core.runtime.db import get_runtime_state_value
    log = get_runtime_state_value(_AUDIT_KEY, [])
    return log if isinstance(log, list) else []


def delete_user(user_id: str, *, mode: str = "soft", actor: str = "owner") -> bool:
    """mode='soft' → deleted_at-timestamp (fortryd-venlig, grace-period).
    mode='hard' → permanent sletning af user-row + keyring-DEK (GDPR §6.2).
    Audit logges altid."""
    if not db.get_user_row(user_id):
        return False
    if mode == "hard":
        try:
            from core.services.keyring_store import delete_user_key
            delete_user_key(user_id)
        except Exception:
            pass
        ok = db.hard_delete_user_row(user_id)
    else:
        ok = db.soft_delete_user_row(user_id, deleted_at=_now())
    if ok:
        _audit(user_id=user_id, action=f"delete:{mode}", actor=actor)
    return ok
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_db.py -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/identity/user_db.py tests/test_user_db.py
git commit -m "feat(users): GDPR soft/hard-delete + keyring-key-sletning + audit-log"
```

---

### Task D2: `set_user_quota` i quota_store (tier fra user_db)

**Files:**
- Modify: `core/services/quota_store.py`
- Test: `tests/test_quota_store.py` (tilføj)

`get_tier` skal foretrække user_db-tier (det nye autoritative felt), med fallback til den eksisterende rolle-baserede logik.

- [ ] **Step 1: Write the failing test**

Tilføj i `tests/test_quota_store.py` (opret filen hvis den ikke findes; importér `isolated_runtime`):

```python
def test_set_user_quota_then_get_tier(isolated_runtime) -> None:
    from core.identity.user_db import create_user
    from core.services.quota_store import set_user_quota, get_tier
    u = create_user(email="q@b.dk", name="Q", password="x", role="member", workspace="q")
    uid = u["user_id"]
    assert set_user_quota(uid, "pro") is True
    assert get_tier(uid) == "pro"


def test_set_user_quota_rejects_unknown_tier(isolated_runtime) -> None:
    import pytest
    from core.identity.user_db import create_user
    from core.services.quota_store import set_user_quota
    u = create_user(email="q2@b.dk", name="Q", password="x", role="member", workspace="q2")
    with pytest.raises(ValueError):
        set_user_quota(u["user_id"], "platinum")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_quota_store.py -q -p no:cacheprovider -k user_quota`
Expected: FAIL — `cannot import name 'set_user_quota'`

- [ ] **Step 3: Implement set_user_quota + prefer user_db tier i get_tier**

I `core/services/quota_store.py`, tilføj funktionen:

```python
def set_user_quota(user_id: str, tier: str) -> bool:
    """Sæt en brugers eksplicitte tier (autoritativt i user_db). Owner kan give
    enhver tier; ordblinde/blinde kan få Plus-kvoter gratis via 'plus'."""
    from core.identity.user_db import set_quota_tier
    return set_quota_tier(user_id, tier)
```

I `get_tier`, øverst i funktionen (før den eksisterende rolle-baserede logik), tilføj et user_db-opslag der vinder hvis sat:

```python
    try:
        from core.identity.user_db import get_user
        _u = get_user(user_id)
        if _u and _u.get("tier") in _VALID_TIERS:
            return str(_u["tier"])
    except Exception:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_quota_store.py -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/quota_store.py tests/test_quota_store.py
git commit -m "feat(users): set_user_quota + get_tier foretrækker user_db-tier"
```

---

### Task D3: `routes/users.py` — owner-only CRUD + GDPR-erasure

**Files:**
- Create: `apps/api/jarvis_api/routes/users.py`
- Modify: `apps/api/jarvis_api/app.py` (registrér router)
- Test: `tests/test_user_management_routes.py` (tilføj)

Alle endpoints er owner-only via `require_owner`-dependencyen fra `jarvisx_auth`. Owner får en bearer-token ved login (Task C1).

- [ ] **Step 1: Write the failing test**

Tilføj i `tests/test_user_management_routes.py`:

```python
def _owner_token(isolated_runtime, monkeypatch) -> tuple[object, str]:
    from core.identity import email_verify, user_db
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: {"success": True})
    user, tok = user_db.register_user(email="owner@b.dk", name="Owner", password="ownerpw",
                                      base_url="http://t", role="owner")
    user_db.verify_email_token(tok)
    from core.runtime.jarvisx_auth import issue_token
    t = issue_token(user_id=user["user_id"], role="owner")["token"]
    return user, t


def test_list_users_requires_owner(isolated_runtime, monkeypatch) -> None:
    c = _client(isolated_runtime)
    r = c.get("/api/users")
    assert r.status_code in (401, 403)


def test_owner_lists_and_mutes_and_deletes(isolated_runtime, monkeypatch) -> None:
    from core.identity import user_db
    owner, token = _owner_token(isolated_runtime, monkeypatch)
    member = user_db.create_user(email="mem@b.dk", name="Mem", password="x",
                                 role="member", workspace="mem")
    c = _client(isolated_runtime)
    hdr = {"Authorization": token}

    r = c.get("/api/users", headers=hdr)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()["users"]}
    assert "mem@b.dk" in emails

    r = c.patch(f"/api/users/{member['user_id']}", headers=hdr, json={"muted": True, "tier": "plus"})
    assert r.status_code == 200
    assert user_db.get_user(member["user_id"])["muted"] is True

    r = c.delete(f"/api/users/{member['user_id']}", headers=hdr, json={"mode": "soft"})
    assert r.status_code == 200
    assert user_db.get_user(member["user_id"])["deleted_at"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_management_routes.py -q -p no:cacheprovider -k "requires_owner or lists_and_mutes"`
Expected: FAIL — 404 (ruterne findes ikke)

- [ ] **Step 3: Write the router**

Create `apps/api/jarvis_api/routes/users.py`:

```python
"""Owner-only user-administration (spec 2026-06-15 §4/§6). CRUD + GDPR-erasure.

Beskyttet af require_owner (JWT owner-token). Følsomme data dekrypteres kun i
respons (owner ser email/discord); klartekst-password eksponeres aldrig.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.identity import user_db
from core.runtime.jarvisx_auth import require_owner

router = APIRouter(prefix="/api/users", tags=["users"])


class PatchUserReq(BaseModel):
    name: str | None = None
    role: str | None = None
    muted: bool | None = None
    tier: str | None = None
    consent_data_processing: bool | None = None
    consent_marketing: bool | None = None
    consent_blind_access: bool | None = None


class DeleteUserReq(BaseModel):
    mode: str = "soft"


@router.get("")
def list_all(claims: dict = Depends(require_owner)) -> JSONResponse:
    return JSONResponse(content={"ok": True, "users": user_db.list_users(include_deleted=True)})


@router.get("/{user_id}")
def get_one(user_id: str, claims: dict = Depends(require_owner)) -> JSONResponse:
    u = user_db.get_user(user_id)
    if not u:
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    return JSONResponse(content={"ok": True, "user": u})


@router.patch("/{user_id}")
def patch_one(user_id: str, req: PatchUserReq,
              claims: dict = Depends(require_owner)) -> JSONResponse:
    if not user_db.get_user(user_id):
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    if req.muted is not None:
        user_db.mute_user(user_id) if req.muted else user_db.unmute_user(user_id)
    if req.tier is not None:
        try:
            user_db.set_quota_tier(user_id, req.tier)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    if any(v is not None for v in (req.consent_data_processing, req.consent_marketing,
                                   req.consent_blind_access)):
        user_db.set_consent(user_id, data_processing=req.consent_data_processing,
                            marketing=req.consent_marketing, blind_access=req.consent_blind_access)
    extra: dict[str, Any] = {}
    if req.name is not None:
        extra["name"] = req.name
    if req.role is not None:
        extra["role"] = req.role
    if extra:
        from core.runtime.db import update_user_row
        update_user_row(user_id, extra)
    return JSONResponse(content={"ok": True, "user": user_db.get_user(user_id)})


@router.delete("/{user_id}")
def delete_one(user_id: str, req: DeleteUserReq,
               claims: dict = Depends(require_owner)) -> JSONResponse:
    mode = req.mode if req.mode in ("soft", "hard") else "soft"
    actor = str(claims.get("sub") or "owner")
    ok = user_db.delete_user(user_id, mode=mode, actor=actor)
    if not ok:
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    return JSONResponse(content={"ok": True, "deleted": mode})
```

- [ ] **Step 4: Register router**

I `apps/api/jarvis_api/app.py`, tilføj import + include sammen med auth-routeren fra Task C1:

```python
from apps.api.jarvis_api.routes.users import router as users_admin_router
```
```python
    app.include_router(users_admin_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_user_management_routes.py -q -p no:cacheprovider`
Expected: PASS (alle)

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/routes/users.py apps/api/jarvis_api/app.py tests/test_user_management_routes.py
git commit -m "feat(users): owner-only admin-routes CRUD + GDPR-erasure"
```

---

## PHASE E — Fuld verifikation + deploy

### Task E1: Fuld suite + deploy

- [ ] **Step 1: Hele user-management-test-suiten**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_passwords.py tests/test_user_db.py tests/test_email_verify.py tests/test_quota_store.py tests/test_user_management_routes.py -q -p no:cacheprovider`
Expected: alle PASS

- [ ] **Step 2: Compile-tjek på rørte kerne-filer**

Run: `/opt/conda/envs/ai/bin/python -m compileall core/runtime/db.py core/identity/user_db.py core/identity/email_verify.py core/identity/passwords.py core/services/quota_store.py apps/api/jarvis_api/routes/auth.py apps/api/jarvis_api/routes/users.py apps/api/jarvis_api/app.py -q`
Expected: ingen output

- [ ] **Step 3: Verificér SMTP-credential findes (manuelt, ikke autonomt)**

Bekræft at `mail_smtp_host`/`mail_smtp_port`/`mail_user`/`mail_password` findes i `~/.jarvis-v2/config/runtime.json` (de gør pr. 2026-06-15). Tilføj evt. `user_email_pepper` (valgfri; ellers bruges en fast fallback). **Bjørn indtaster selv eventuelle hemmelige værdier — ikke Claude.**

- [ ] **Step 4: Deploy (kræver Bjørns ok)**

```bash
git push origin main && git push target main
```
Genstart `jarvis-api` på target (idle-tjekket). Verificér live: `/api/auth/register` svarer (uden at sende rigtig mail til en testadresse — brug en adresse du ejer, eller monkeypatch i staging).

- [ ] **Step 5: Manuel end-to-end (én rigtig bruger)**

1. POST `/api/auth/register` med en email du ejer → modtag verifikations-mail fra jarvis@srvlab.dk.
2. Klik linket → `email_verified=1`.
3. POST `/api/auth/login` → få bearer-token.
4. Som owner: GET `/api/users` (liste), PATCH (mute/tier), DELETE (soft).

---

## Notes for the implementer

- **conda:** alle Python-kald via `/opt/conda/envs/ai/bin/python`.
- **DB-tests:** brug `isolated_runtime`-fixturen (frisk temp-DB). Den kalder `init_db()`, så `_ensure_users_table` skal være registreret dér (Task A2).
- **Coverage-gate:** nye `core/`-moduler har matchende `tests/test_<modul>.py` (passwords, user_db, email_verify). `db.py`/`quota_store.py` har/får test-filer. Routes ligger under `apps/` (ikke omfattet af core-coverage-gaten).
- **Dual-truth-note:** users-tabellen er autoritativ for de NYE felter (email/password/verified/tier/consent/deleted_at). Den eksisterende `users.json` bevares til legacy Discord-identitet i denne leverance. FOLLOW-UP (separat): migrér `users.json`-brugere ind i tabellen + re-point `users.py`-læsere, så der kun er én kilde. Indtil da: opret ikke samme bruger begge steder uden bevidsthed om det.
- **Sikkerhed:** klartekst-password forlader aldrig request-scope (hashes straks). SMTP-credential fra runtime.json. Hard-delete sletter keyring-DEK → krypteret data bliver ulæseligt. Owner-only admin via `require_owner`.
- **TOTP-på-hard-delete (follow-up):** spec §6.2 vil have en frisk owner-TOTP-override ved hard-delete af *andres* data. Denne leverance gater på `require_owner` (gyldig owner-JWT) — tilstrækkeligt som v1-kontrol, men IKKE en per-handling TOTP-challenge. FOLLOW-UP: kræv `totp_verifier.verify` + `record_attempt` i `DELETE`-handleren når `mode='hard'` og target ≠ caller. `delete_policy.resolve_delete_action` kan samtidig wires ind for den fulde mode/bekræftelses-matrix.
- **--workers 1 frys-fælde:** rute-handlerne her er lette (DB-opslag); hvis et fremtidigt kald bliver tungt/blokerende, wrap i `asyncio.to_thread`.
