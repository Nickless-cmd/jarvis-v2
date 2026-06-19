# Mobile Push Notifications (FCM) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Native push-notifikationer i Jarvis Android-companion via FCM data-only (svar-klar, proaktiv, reminder), så Google aldrig ser indhold.

**Architecture:** Server-side `push_dispatcher` afgør hvornår/hvem (suppression via run_event_log + grace), `fcm_gateway` sender data-only FCM v1, `device_tokens` holder tokens pr. bruger. Appen vækkes, henter indhold over HTTPS, viser native notifikation via notifee, tap dyb-linker til samtalen.

**Tech Stack:** Python (FastAPI, google-auth, sqlite via `core.runtime.db.connect`), pytest. Mobil: React Native (bare Expo SDK 56), `@react-native-firebase/messaging`, `notifee`, vitest.

**Spec:** `docs/superpowers/specs/2026-06-19-mobile-push-notifications-design.md`

**KRITISKE miljø-noter (læs FØR du starter):**
- Server-kode bor på container `bs@10.0.0.39:/media/projects/jarvis-v2`. Rediger der (scp/ssh). Mobil bor lokalt i `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`.
- Python: `~/miniconda3/envs/ai/bin/python`, altid `PYTHONPATH=/media/projects/jarvis-v2`. Pytest fra absolutte stier (ssh starter i `~`).
- **Coverage-gate:** test-filen SKAL hedde `tests/test_<modul>.py` præcist (fx `tests/test_device_tokens.py`), ellers fejler pre-commit stille. Verificér altid at HEAD faktisk rykkede efter commit.
- `--workers 1`: in-memory state (run_event_log) deles på tværs af endpoints+tråde i samme proces.
- Genstart efter server-ændring: `sudo systemctl restart jarvis-api`.
- Creds er på plads: `runtime.json` har `fcm_project_id=jarvis-companion-58e5c` + `fcm_service_account_path`; `google-services.json` ligger i mobilens `android/app/`.

---

## Fase A — Server-fundament (container, pytest)

### Task 1: device_tokens.py — token-tabel + CRUD

**Files:**
- Create: `/media/projects/jarvis-v2/core/services/device_tokens.py`
- Test: `/media/projects/jarvis-v2/tests/test_device_tokens.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_device_tokens.py
import core.services.device_tokens as dt


def _clear():
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")


def test_register_and_list():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.register("bjorn", "tok-B", "android")
    dt.register("mikkel", "tok-C", "android")
    assert set(dt.list_for_user("bjorn")) == {"tok-A", "tok-B"}
    assert dt.list_for_user("mikkel") == ["tok-C"]


def test_register_is_upsert():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.register("mikkel", "tok-A", "android")  # samme token, ny ejer (telefon-skift)
    assert dt.list_for_user("bjorn") == []
    assert dt.list_for_user("mikkel") == ["tok-A"]


def test_delete():
    _clear()
    dt.register("bjorn", "tok-A", "android")
    dt.delete("tok-A")
    assert dt.list_for_user("bjorn") == []
    dt.delete("tok-A")  # idempotent — må ikke fejle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_device_tokens.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.services.device_tokens'`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/device_tokens.py
"""Per-bruger FCM device-tokens. Egen tabel — rører ikke db.py's 33k linjer."""
from __future__ import annotations

from datetime import UTC, datetime

from core.runtime.db import connect

_ENSURED = False


def _ensure_table() -> None:
    global _ENSURED
    if _ENSURED:
        return
    with connect() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS device_tokens (
                   token       TEXT PRIMARY KEY,
                   user_id     TEXT NOT NULL,
                   platform    TEXT NOT NULL DEFAULT 'android',
                   updated_at  TEXT NOT NULL
               )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_device_tokens_user ON device_tokens(user_id)")
    _ENSURED = True


def register(user_id: str, token: str, platform: str = "android") -> None:
    uid, tok = (user_id or "").strip(), (token or "").strip()
    if not uid or not tok:
        return
    _ensure_table()
    with connect() as c:
        c.execute(
            """INSERT INTO device_tokens(token, user_id, platform, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(token) DO UPDATE SET
                   user_id=excluded.user_id,
                   platform=excluded.platform,
                   updated_at=excluded.updated_at""",
            (tok, uid, (platform or "android").strip(), datetime.now(UTC).isoformat()),
        )


def list_for_user(user_id: str) -> list[str]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    _ensure_table()
    with connect() as c:
        rows = c.execute(
            "SELECT token FROM device_tokens WHERE user_id=? ORDER BY updated_at", (uid,)
        ).fetchall()
    return [r[0] for r in rows]


def delete(token: str) -> None:
    tok = (token or "").strip()
    if not tok:
        return
    _ensure_table()
    with connect() as c:
        c.execute("DELETE FROM device_tokens WHERE token=?", (tok,))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_device_tokens.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/device_tokens.py tests/test_device_tokens.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): device_tokens-tabel + CRUD pr. bruger"
```

---

### Task 2: run_event_log — abonnent-sporing til suppression

**Files:**
- Modify: `/media/projects/jarvis-v2/core/services/run_event_log.py`
- Test: `/media/projects/jarvis-v2/tests/test_run_event_log.py` (tilføj til eksisterende)

- [ ] **Step 1: Write the failing test (tilføj nederst i filen)**

```python
def test_subscriber_tracking_and_consumed():
    rel.create("r1", "s1")
    assert rel.was_consumed_or_active("r1") is False
    rel.subscriber_opened("r1")
    assert rel.was_consumed_or_active("r1") is True   # aktiv subscriber
    rel.subscriber_closed("r1")
    assert rel.was_consumed_or_active("r1") is False  # ingen aktiv, ikke consumed
    rel.mark_consumed("r1")
    assert rel.was_consumed_or_active("r1") is True    # consumed = nogen så det til ende


def test_consumed_unknown_run_is_false():
    assert rel.was_consumed_or_active("ukendt") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_run_event_log.py -q`
Expected: FAIL (`AttributeError: module ... has no attribute 'subscriber_opened'`)

- [ ] **Step 3: Write minimal implementation**

I `create()`, tilføj to felter til dict'en (find linjen med `"created_at": time.monotonic(),` og tilføj EFTER den, inde i dict-literalen):

```python
            "subscribers": 0,
            "consumed": False,
```

Tilføj disse funktioner nederst i `core/services/run_event_log.py`:

```python
def subscriber_opened(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["subscribers"] = int(st.get("subscribers", 0)) + 1


def subscriber_closed(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["subscribers"] = max(0, int(st.get("subscribers", 0)) - 1)


def mark_consumed(run_id: str) -> None:
    """En subscriber yieldede message_stop → nogen så runnet til ende."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["consumed"] = True


def was_consumed_or_active(run_id: str) -> bool:
    """True hvis en levende subscriber så/ser runnet til ende → undertryk push."""
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return False
        return bool(st.get("consumed")) or int(st.get("subscribers", 0)) > 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_run_event_log.py -q`
Expected: PASS (alle, inkl. de 2 nye)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/run_event_log.py tests/test_run_event_log.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): abonnent-sporing i run_event_log til suppression-signal"
```

---

### Task 3: chat_sessions.get_session_owner

**Files:**
- Modify: `/media/projects/jarvis-v2/core/services/chat_sessions.py`
- Test: `/media/projects/jarvis-v2/tests/test_chat_sessions_owner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chat_sessions_owner.py
import core.services.chat_sessions as cs


def test_owner_from_user_message():
    sess = cs.create_chat_session(title="ejer-test")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="bjorn")
    assert cs.get_session_owner(str(sid)) == "bjorn"


def test_owner_none_when_no_stamp():
    sess = cs.create_chat_session(title="ingen-ejer")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    assert cs.get_session_owner(str(sid)) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_chat_sessions_owner.py -q`
Expected: FAIL (`AttributeError: ... has no attribute 'get_session_owner'`)

- [ ] **Step 3: Write minimal implementation**

Tilføj til `core/services/chat_sessions.py` (brug samme `connect`-import som resten af filen — tjek toppen; hvis den importerer `from core.runtime.db import connect`, genbrug den):

```python
def get_session_owner(session_id: str) -> str | None:
    """Ejeren = user_id på den seneste besked i sessionen der HAR et stempel.
    Returnerer None for ustemplede (legacy) sessioner."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute(
            """SELECT user_id FROM chat_messages
               WHERE session_id=? AND user_id IS NOT NULL AND user_id<>''
               ORDER BY rowid DESC LIMIT 1""",
            (sid,),
        ).fetchone()
    return row[0] if row else None
```

> Bemærk: verificér tabel-/kolonnenavn for chat-beskeder i `chat_sessions.py` (`append_chat_message` viser INSERT-target). Hvis tabellen ikke hedder `chat_messages` eller kolonnen ikke er `session_id`/`user_id`, ret SQL'en til de faktiske navne — kør testen for at bekræfte.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_chat_sessions_owner.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/chat_sessions.py tests/test_chat_sessions_owner.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): get_session_owner til token-routing"
```

---

### Task 4: fcm_gateway.py — FCM v1 data-only send

**Files:**
- Create: `/media/projects/jarvis-v2/core/services/fcm_gateway.py`
- Test: `/media/projects/jarvis-v2/tests/test_fcm_gateway.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fcm_gateway.py
import core.services.fcm_gateway as fcm


def test_build_message_is_data_only_high_priority():
    msg = fcm._build_message("tok-X", {"kind": "answer_ready", "session_id": "s1"})
    body = msg["message"]
    assert body["token"] == "tok-X"
    assert body["data"] == {"kind": "answer_ready", "session_id": "s1"}
    assert "notification" not in body  # data-only → Google ser intet indhold
    assert body["android"]["priority"] == "high"


def test_send_unregistered_returns_invalid(monkeypatch):
    # Mock HTTP: FCM svarer 404 UNREGISTERED → gateway returnerer ("invalid", ...)
    class _Resp:
        status = 404
        def read(self): return b'{"error":{"status":"NOT_FOUND","message":"Requested entity was not found."}}'
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(fcm, "_access_token", lambda: "fake-oauth")
    monkeypatch.setattr(fcm, "_project_id", lambda: "proj-1")
    import urllib.request
    def _fake_urlopen(req, timeout=0):
        from urllib.error import HTTPError
        raise HTTPError(req.full_url, 404, "Not Found", {}, _Resp())
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    ok, code = fcm.send("tok-dead", {"kind": "answer_ready"})
    assert ok is False
    assert code == "invalid"  # → dispatcher sletter tokenet
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_fcm_gateway.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/fcm_gateway.py
"""FCM HTTP v1 gateway — data-only push. Google ser kun et vaekke-signal.

Parallel til ntfy_gateway. OAuth via google-auth (allerede i ai-miljoeet).
Config i runtime.json: fcm_project_id + fcm_service_account_path.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def _runtime() -> dict:
    try:
        return json.loads((Path.home() / ".jarvis-v2" / "config" / "runtime.json").read_text())
    except Exception:
        return {}


def _project_id() -> str | None:
    return _runtime().get("fcm_project_id")


def _sa_path() -> str | None:
    return _runtime().get("fcm_service_account_path")


def is_configured() -> bool:
    return bool(_project_id()) and bool(_sa_path()) and Path(_sa_path() or "").exists()


def _access_token() -> str | None:
    """Mint en OAuth-access-token fra service-account via google-auth."""
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        creds = service_account.Credentials.from_service_account_file(_sa_path(), scopes=[_SCOPE])
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        logger.warning("fcm: kunne ikke minte access-token: %s", e)
        return None


def _build_message(token: str, data: dict) -> dict:
    # ALLE data-vaerdier skal vaere strenge i FCM v1.
    str_data = {k: str(v) for k, v in (data or {}).items()}
    return {
        "message": {
            "token": token,
            "data": str_data,
            "android": {"priority": "high"},
        }
    }


def send(token: str, data: dict) -> tuple[bool, str]:
    """Send data-only push. Returnerer (ok, code). code='invalid' => slet token."""
    if not is_configured():
        return (False, "unconfigured")
    tok = _access_token()
    pid = _project_id()
    if not tok or not pid:
        return (False, "auth")
    url = f"https://fcm.googleapis.com/v1/projects/{pid}/messages:send"
    payload = json.dumps(_build_message(token, data)).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        return (True, "ok")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        if e.code in (404, 400) and ("NOT_FOUND" in body or "UNREGISTERED" in body or "INVALID_ARGUMENT" in body):
            return (False, "invalid")
        logger.warning("fcm: HTTP %s: %s", e.code, body[:200])
        return (False, "http")
    except Exception as e:
        logger.warning("fcm: send-fejl: %s", e)
        return (False, "net")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_fcm_gateway.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/fcm_gateway.py tests/test_fcm_gateway.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): fcm_gateway — data-only FCM v1 send + token-oprydnings-signal"
```

---

### Task 5: push_dispatcher.py — hvornår/hvem

**Files:**
- Create: `/media/projects/jarvis-v2/core/services/push_dispatcher.py`
- Test: `/media/projects/jarvis-v2/tests/test_push_dispatcher.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_push_dispatcher.py
import core.services.push_dispatcher as pd
import core.services.device_tokens as dt
import core.services.run_event_log as rel


def _setup(monkeypatch):
    sent = []
    monkeypatch.setattr(pd, "_fcm_send", lambda token, data: sent.append((token, data)) or (True, "ok"))
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")
    return sent


def test_suppressed_when_consumed(monkeypatch):
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-1", "sess-1")
    rel.mark_consumed("run-1")  # nogen saa det live
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-1")  # synkron intern (ingen grace-timer i test)
    assert sent == []  # undertrykt


def test_pushes_when_not_consumed(monkeypatch):
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-2", "sess-2")  # ingen subscriber, ikke consumed
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-2")
    assert len(sent) == 1
    token, data = sent[0]
    assert token == "tok-A"
    assert data["kind"] == "answer_ready"
    assert data["run_id"] == "run-2"


def test_invalid_token_is_deleted(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(pd, "_fcm_send", lambda token, data: (False, "invalid"))
    dt.register("bjorn", "tok-dead")
    rel.create("run-3", "sess-3")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-3")
    assert dt.list_for_user("bjorn") == []  # selv-oprydning
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_push_dispatcher.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/push_dispatcher.py
"""Beslutter HVORNAAR og HVEM der skal pushes. Bygger paa run_event_log-suppression."""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

PUSH_GRACE_S = 5.0  # giv en levende klient tid til at draene sidste frames foer vi tjekker


def _fcm_send(token: str, data: dict):
    from core.services.fcm_gateway import send
    return send(token, data)


def _owner_of_run(run_id: str):
    from core.services import run_event_log as rel
    from core.services.chat_sessions import get_session_owner
    sid = rel.session_for_run(run_id)
    return get_session_owner(sid) if sid else None


def _push_to_user(user_id: str, data: dict) -> None:
    from core.services import device_tokens as dt
    for token in dt.list_for_user(user_id):
        try:
            ok, code = _fcm_send(token, data)
            if not ok and code == "invalid":
                dt.delete(token)
        except Exception as e:
            logger.warning("push: send-fejl for token: %s", e)


def _dispatch_run_done(run_id: str) -> None:
    from core.services import run_event_log as rel
    if rel.was_consumed_or_active(run_id):
        return  # nogen saa det live
    sid = rel.session_for_run(run_id)
    owner = _owner_of_run(run_id)
    if not owner:
        return
    _push_to_user(owner, {"kind": "answer_ready", "session_id": sid or "", "run_id": run_id})


def on_run_done(run_id: str) -> None:
    """Kaldes fra detached_run finally. Planlaegger suppression-tjek efter grace."""
    try:
        threading.Timer(PUSH_GRACE_S, _dispatch_run_done, args=(run_id,)).start()
    except Exception as e:
        logger.warning("push: kunne ikke planlaegge run-done-tjek: %s", e)


def on_initiative(user_id: str, text: str) -> None:
    if not user_id:
        return
    _push_to_user(user_id, {"kind": "initiative", "preview": (text or "")[:80]})


def on_reminder(user_id: str, text: str) -> None:
    if not user_id:
        return
    _push_to_user(user_id, {"kind": "reminder", "preview": (text or "")[:80]})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_push_dispatcher.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/push_dispatcher.py tests/test_push_dispatcher.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): push_dispatcher — grace + suppression + token-oprydning"
```

---

### Task 6: routes/push.py — register/unregister

**Files:**
- Create: `/media/projects/jarvis-v2/apps/api/jarvis_api/routes/push.py`
- Modify: `/media/projects/jarvis-v2/apps/api/jarvis_api/app.py` (include router)
- Test: `/media/projects/jarvis-v2/tests/test_push_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_push_routes.py
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app
import core.services.device_tokens as dt


def test_register_scopes_to_auth_user(monkeypatch):
    # Tving current_user_id til 'bjorn' (auth-laget mockes)
    import apps.api.jarvis_api.routes.push as push_routes
    monkeypatch.setattr(push_routes, "_current_user", lambda: "bjorn")
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")
    client = TestClient(app)
    r = client.post("/push/register", json={"token": "tok-Z", "platform": "android"})
    assert r.status_code == 200
    assert dt.list_for_user("bjorn") == ["tok-Z"]
    r2 = client.post("/push/unregister", json={"token": "tok-Z"})
    assert r2.status_code == 200
    assert dt.list_for_user("bjorn") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_push_routes.py -q`
Expected: FAIL (router findes ikke / 404)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/jarvis_api/routes/push.py
"""Push token-registrering. Scoper til den auth'ede bruger."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import core.services.device_tokens as device_tokens

router = APIRouter(prefix="/push", tags=["push"])


class RegisterBody(BaseModel):
    token: str
    platform: str = "android"


class UnregisterBody(BaseModel):
    token: str


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.post("/register")
async def register(body: RegisterBody) -> dict:
    uid = _current_user()
    if not uid or not (body.token or "").strip():
        return {"ok": False}
    device_tokens.register(uid, body.token, body.platform)
    return {"ok": True}


@router.post("/unregister")
async def unregister(body: UnregisterBody) -> dict:
    device_tokens.delete(body.token)
    return {"ok": True}
```

I `apps/api/jarvis_api/app.py`, find linjen `app.include_router(chat_stream_v2_router)` og tilføj efter den:

```python
    from apps.api.jarvis_api.routes.push import router as push_router
    app.include_router(push_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_push_routes.py -q`
Expected: PASS (1 passed). Hvis auth-middleware blokerer TestClient, sæt evt. `current_user_id` via miljø/override som de øvrige route-tests i `tests/` gør — tjek et eksisterende `tests/test_*route*.py` for mønsteret.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add apps/api/jarvis_api/routes/push.py apps/api/jarvis_api/app.py tests/test_push_routes.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): /push/register + /push/unregister (bruger-scoped)"
```

---

### Task 7: Wiring — abonnent-sporing i SSE + on_run_done

**Files:**
- Modify: `/media/projects/jarvis-v2/apps/api/jarvis_api/routes/chat_stream_v2.py` (`_subscribe`-generatoren)
- Modify: `/media/projects/jarvis-v2/apps/api/jarvis_api/routes/chat.py` (`/runs/{id}/subscribe` + `/sessions/{id}/live` generatorer)
- Modify: `/media/projects/jarvis-v2/core/services/visible_runs_sections/detached_run.py` (`_consume` finally)

- [ ] **Step 1: Tilføj subscriber-sporing i de tre SSE-generatorer**

I HVER af de tre generator-løkker (`_subscribe` i chat_stream_v2.py, `_gen` i chat.py's `chat_run_subscribe` og `chat_session_live`), wrap løkken så `rel` opdateres. Mønster (anvend på alle tre — `run_id` er allerede i scope):

```python
        import core.services.run_event_log as rel  # allerede importeret i chat_stream_v2; tilføj i chat.py hvis mangler
        rel.subscriber_opened(run_id)
        try:
            idx = 0
            empty = 0
            while True:
                frames, done = rel.read(run_id, idx)
                for f in frames:
                    idx += 1
                    yield f
                    if '"type": "message_stop"' in f or '"type":"message_stop"' in f:
                        rel.mark_consumed(run_id)
                if done:
                    break
                if frames:
                    empty = 0
                else:
                    empty += 1
                    if empty > 300:
                        break
                await _a.sleep(0.08)
        finally:
            rel.subscriber_closed(run_id)
```

> Behold den eksisterende `await asyncio.sleep`-reference (`_a` i chat_stream_v2, `asyncio` i chat.py) — ret kun navnet så det matcher filens import.

- [ ] **Step 2: Kald on_run_done i detached_run finally**

I `core/services/visible_runs_sections/detached_run.py`, i `_consume`'s `finally`-blok, EFTER `rel.mark_done(run_id)`:

```python
                try:
                    from core.services.push_dispatcher import on_run_done
                    on_run_done(run_id)
                except Exception:
                    pass
```

- [ ] **Step 3: Verificér intet brækker (compile + eksisterende tests)**

Run:
```
~/miniconda3/envs/ai/bin/python -m py_compile /media/projects/jarvis-v2/apps/api/jarvis_api/routes/chat_stream_v2.py /media/projects/jarvis-v2/apps/api/jarvis_api/routes/chat.py /media/projects/jarvis-v2/core/services/visible_runs_sections/detached_run.py
PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_run_event_log.py /media/projects/jarvis-v2/tests/test_single_flight_guard.py -q
```
Expected: COMPILE OK + alle tests PASS.

- [ ] **Step 4: Live-røgtest (flag ON)**

Sæt flag ON, genstart api, send to beskeder hurtigt i samme session (som single-flight-testen) + verificér i logs at `on_run_done` ikke kaster. Bekræft normal streaming uændret.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add apps/api/jarvis_api/routes/chat_stream_v2.py apps/api/jarvis_api/routes/chat.py core/services/visible_runs_sections/detached_run.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): wire subscriber-sporing i SSE + on_run_done i detached finally"
```

---

## Fase B — Trigger-wiring (proaktiv + reminder)

> **Designnote (fra self-review):** `initiative_queue.push_initiative` har ingen user-param, og scheduled reminders er bevidst INTERNE signaler til Jarvis (ikke direkte bruger-DMs — de lander i hans awareness, han beslutter at handle). Det KORREKTE fælles integrationspunkt er derfor `notification_bridge.send_session_notification(content, source)` — netop dér hvor Jarvis faktisk sender en proaktiv besked til en brugers session. Ét hook dækker både proaktiv og reminder-udfald.

### Task 8: Wire notification_bridge → push_dispatcher

**Files:**
- Modify: `/media/projects/jarvis-v2/core/services/notification_bridge.py` (`send_session_notification`)
- Test: `/media/projects/jarvis-v2/tests/test_notification_bridge_push.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notification_bridge_push.py
import core.services.notification_bridge as nb


def test_proactive_notification_triggers_push(monkeypatch):
    calls = []
    monkeypatch.setattr(nb, "_push_proactive", lambda session_id, text: calls.append((session_id, text)))
    # Tving en kendt pinned session
    monkeypatch.setattr(nb, "get_pinned_session_id", lambda: "sess-9")
    res = nb.send_session_notification("Jeg har en tanke", source="inner-voice")
    assert res.get("status") in ("ok", "no_session")
    if res.get("status") == "ok":
        assert calls == [("sess-9", "Jeg har en tanke")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_notification_bridge_push.py -q`
Expected: FAIL (`_push_proactive` findes ikke)

- [ ] **Step 3: Write minimal implementation**

Tilføj helper i `core/services/notification_bridge.py`:

```python
def _push_proactive(session_id: str, text: str) -> None:
    """Spejl en proaktiv session-notifikation som mobil-push til sessionens ejer."""
    try:
        from core.services.chat_sessions import get_session_owner
        from core.services.push_dispatcher import on_initiative
        owner = get_session_owner(session_id)
        if owner:
            on_initiative(owner, text)
    except Exception:
        pass
```

I `send_session_notification(...)`, dér hvor funktionen har bestemt mål-sessionen OG netop har leveret beskeden med succes (lige før `return {"status": "ok", ...}`), tilføj:

```python
        _push_proactive(target_session_id, content)
```

> Brug det faktiske session-variabelnavn funktionen allerede har udregnet (typisk fra `get_pinned_session_id()` eller seneste session) og `content`-parameteren. Læs funktionen og indsæt kaldet på success-stien.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_notification_bridge_push.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add core/services/notification_bridge.py tests/test_notification_bridge_push.py
git -C /media/projects/jarvis-v2 commit -m "feat(push): proaktiv/reminder-notifikationer -> mobil-push via notification_bridge"
```

---

## Fase C — Mobil (lokal worktree)

> Alle stier under `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`. Bump `app.json` versionCode + `package.json` version før build (jf. deploy-reglen). Device: Galaxy S24 (RFCX211W6CR), `adb install -r`.

### Task 9: Native deps — RNFirebase + notifee + gradle

**Files:**
- Modify: `package.json`, `android/build.gradle`, `android/app/build.gradle`

- [ ] **Step 1: Installer pakker**

```bash
cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile
npm i @react-native-firebase/app @react-native-firebase/messaging @notifee/react-native
```

- [ ] **Step 2: Gradle-wiring**

I `android/build.gradle` (projekt-niveau) `dependencies { classpath(...) }`: tilføj `classpath 'com.google.gms:google-services:4.4.2'`.
I `android/app/build.gradle`: tilføj øverst efter de andre `apply plugin`-linjer: `apply plugin: 'com.google.gms.google-services'`.

- [ ] **Step 3: Verificér gradle-sync**

```bash
cd android && ./gradlew :app:dependencies --configuration releaseRuntimeClasspath >/tmp/gradle.log 2>&1; tail -3 /tmp/gradle.log
```
Expected: BUILD SUCCESSFUL (eller ingen plugin-fejl).

- [ ] **Step 4: Commit**

```bash
git -C /media/projects/jarvis-v2 add .worktrees/jarvis-mobile-companion-v1/apps/mobile/package.json .worktrees/jarvis-mobile-companion-v1/apps/mobile/android/build.gradle .worktrees/jarvis-mobile-companion-v1/apps/mobile/android/app/build.gradle .worktrees/jarvis-mobile-companion-v1/apps/mobile/package-lock.json
git -C /media/projects/jarvis-v2 commit -m "feat(mobile-push): RNFirebase + notifee deps + gradle google-services plugin"
```

### Task 10: src/lib/push.ts — registrering + modtagelse + visning

**Files:**
- Create: `src/lib/push.ts`
- Test: `src/lib/push.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// src/lib/push.test.ts
import { describe, it, expect, vi } from 'vitest'
import { buildNotification } from './push'

describe('buildNotification', () => {
  it('answer_ready -> titel + body fra hentet besked', () => {
    const n = buildNotification({ kind: 'answer_ready', session_id: 's1' }, 'Hej Bjørn, her er svaret')
    expect(n.title).toMatch(/Jarvis/)
    expect(n.body).toContain('her er svaret')
    expect(n.data.session_id).toBe('s1')
  })
  it('reminder -> bruger preview', () => {
    const n = buildNotification({ kind: 'reminder', preview: 'Ring til lægen' }, null)
    expect(n.title).toMatch(/Påmindelse/)
    expect(n.body).toContain('Ring til lægen')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile && npx vitest run src/lib/push.test.ts`
Expected: FAIL (`buildNotification` findes ikke)

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/lib/push.ts
import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance } from '@notifee/react-native'
import type { ApiConfig } from './types'

export type PushData = { kind: string; session_id?: string; run_id?: string; preview?: string }

/** Pure: byg notifikations-felter ud fra data + (evt.) hentet beskedtekst. Testbar. */
export function buildNotification(data: PushData, fetchedBody: string | null) {
  if (data.kind === 'reminder') {
    return { title: 'Påmindelse', body: data.preview ?? '', data }
  }
  if (data.kind === 'initiative') {
    return { title: 'Jarvis', body: data.preview ?? 'Jarvis vil sige noget', data }
  }
  // answer_ready
  return { title: 'Jarvis svarede', body: fetchedBody ?? 'Nyt svar', data }
}

async function fetchLatest(config: ApiConfig, sessionId: string): Promise<string | null> {
  try {
    const url = new URL(`/chat/sessions/${encodeURIComponent(sessionId)}`, config.apiBaseUrl).toString()
    const r = await fetch(url, { headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {} })
    if (!r.ok) return null
    const j = await r.json()
    const msgs = j.messages ?? []
    const last = [...msgs].reverse().find((m: any) => m.role === 'assistant')
    if (!last) return null
    const c = last.content
    const text = typeof c === 'string' ? c : (Array.isArray(c) ? c.map((b: any) => b.text ?? '').join('') : '')
    return text.slice(0, 140)
  } catch { return null }
}

async function display(config: ApiConfig, data: PushData) {
  const body = data.session_id ? await fetchLatest(config, data.session_id) : null
  const n = buildNotification(data, body)
  const channelId = await notifee.createChannel({ id: 'jarvis', name: 'Jarvis', importance: AndroidImportance.HIGH })
  await notifee.displayNotification({
    title: n.title, body: n.body, data: n.data as any,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' },
  })
}

/** Registrér token efter login + lyt på rotation. */
export async function registerForPush(config: ApiConfig): Promise<void> {
  try {
    await messaging().requestPermission()
    const token = await messaging().getToken()
    await postToken(config, token)
    messaging().onTokenRefresh((t) => { void postToken(config, t) })
  } catch { /* graceful: ingen push, in-app virker stadig */ }
}

async function postToken(config: ApiConfig, token: string) {
  const url = new URL('/push/register', config.apiBaseUrl).toString()
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}) },
    body: JSON.stringify({ token, platform: 'android' }),
  })
}

/** Kald i forgrunden (app åben). */
export function attachForegroundHandler(config: ApiConfig) {
  return messaging().onMessage(async (msg) => { await display(config, (msg.data ?? {}) as PushData) })
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile && npx vitest run src/lib/push.test.ts`
Expected: PASS (2 passed). (Mock `@react-native-firebase/messaging` + `@notifee/react-native` i `vitest.setup` hvis import fejler — kun `buildNotification` testes, så det er rent.)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add .worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/push.ts .worktrees/jarvis-mobile-companion-v1/apps/mobile/src/lib/push.test.ts
git -C /media/projects/jarvis-v2 commit -m "feat(mobile-push): push.ts — registrering, hent-indhold, vis, deep-link-data"
```

### Task 11: App-wiring — baggrunds-handler + login + tap-navigation

**Files:**
- Modify: `index.js` (eller app-entry — baggrunds-handler SKAL registreres uden for komponent-træet)
- Modify: login-flow (hvor `ApiConfig` bliver klar) → kald `registerForPush` + `attachForegroundHandler`
- Modify: navigation (tap → åbn `data.session_id`)

- [ ] **Step 1: Baggrunds-handler i index.js**

Øverst i `index.js` (før `AppRegistry.registerComponent`):

```javascript
import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance } from '@notifee/react-native'

messaging().setBackgroundMessageHandler(async (msg) => {
  const data = msg.data ?? {}
  const channelId = await notifee.createChannel({ id: 'jarvis', name: 'Jarvis', importance: AndroidImportance.HIGH })
  // Baggrund: vis straks med preview; appen henter fuld tekst ved tap/åbning.
  const title = data.kind === 'reminder' ? 'Påmindelse' : 'Jarvis svarede'
  await notifee.displayNotification({
    title, body: data.preview ?? 'Nyt fra Jarvis', data,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' },
  })
})
```

- [ ] **Step 2: Registrér ved login + forgrunds-handler**

Hvor appen har en gyldig `ApiConfig` efter login (fx i `StreamProvider`/app-root effekt), tilføj:

```typescript
import { registerForPush, attachForegroundHandler } from './lib/push'
// i en useEffect der kører når config.authToken er sat:
useEffect(() => {
  if (!config?.authToken) return
  void registerForPush(config)
  const unsub = attachForegroundHandler(config)
  return () => unsub()
}, [config?.authToken])
```

- [ ] **Step 3: Tap-navigation**

Hvor app-navigationen er sat op, lyt på notifee-events + initial notifikation og naviger til `data.session_id`:

```typescript
import notifee, { EventType } from '@notifee/react-native'
// i app-root:
useEffect(() => {
  const unsub = notifee.onForegroundEvent(({ type, detail }) => {
    if (type === EventType.PRESS && detail.notification?.data?.session_id) {
      sessions.select(config, String(detail.notification.data.session_id))
    }
  })
  notifee.getInitialNotification().then((n) => {
    const sid = n?.notification?.data?.session_id
    if (sid) sessions.select(config, String(sid))
  })
  return () => unsub()
}, [config])
```

- [ ] **Step 4: Verificér tsc + vitest**

Run: `cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile && npx tsc -b && npx vitest run`
Expected: tsc OK + alle tests PASS.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2 add .worktrees/jarvis-mobile-companion-v1/apps/mobile
git -C /media/projects/jarvis-v2 commit -m "feat(mobile-push): baggrunds-handler + login-registrering + tap-navigation"
```

### Task 12: Build + ende-til-ende verifikation (manuel)

- [ ] **Step 1: Bump version + byg APK**

```bash
cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile
# bump versionCode i app.json + android/app/build.gradle + version i package.json
cd android && ./gradlew :app:assembleRelease -PreactNativeArchitectures=arm64-v8a
```
Kopiér APK til `~/jarvis-mobile.apk`, `adb install -r ~/jarvis-mobile.apk`.

- [ ] **Step 2: Deploy server (flag ON) + genstart**

```bash
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api && systemctl is-active jarvis-api'
```

- [ ] **Step 3: Ende-til-ende (det endelige bevis)**

Test alle tre app-tilstande med en svar-klar-trigger (send fra desktop til en delt session mens mobilen ikke kigger):
1. App i **forgrunden** på en ANDEN samtale → notifikation vises, tap åbner rette samtale.
2. App i **baggrund** → notifikation vises, tap åbner rette samtale.
3. App **helt lukket/dræbt** → notifikation vises (FCM vækker), tap åbner rette samtale.
4. App **i forgrunden på PRÆCIS den samtale** → INGEN banner (suppression).
5. Verificér på server at `device_tokens` har Bjørns token, og at en streamet-til-ende kørsel IKKE udløser push.

- [ ] **Step 4: Commit (version-bump)**

```bash
git -C /media/projects/jarvis-v2 add .worktrees/jarvis-mobile-companion-v1/apps/mobile/app.json .worktrees/jarvis-mobile-companion-v1/apps/mobile/android/app/build.gradle .worktrees/jarvis-mobile-companion-v1/apps/mobile/package.json
git -C /media/projects/jarvis-v2 commit -m "chore(mobile-push): version-bump for push-build"
```

---

## Afslutning

Efter alle tasks: brug **superpowers:finishing-a-development-branch**. Verificér fuld suite:
- Server: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest /media/projects/jarvis-v2/tests/test_device_tokens.py /media/projects/jarvis-v2/tests/test_run_event_log.py /media/projects/jarvis-v2/tests/test_fcm_gateway.py /media/projects/jarvis-v2/tests/test_push_dispatcher.py /media/projects/jarvis-v2/tests/test_push_routes.py /media/projects/jarvis-v2/tests/test_chat_sessions_owner.py -q`
- Mobil: `cd .../apps/mobile && npx tsc -b && npx vitest run`
- Opdatér memory `reference_mobile_stream_socket_abort` / opret `project_mobile_push_notifications` med live-status.
