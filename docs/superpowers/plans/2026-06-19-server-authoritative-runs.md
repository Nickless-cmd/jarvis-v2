# Server-Authoritative Runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gør visible-runs server-autoritative (lever som baggrundsopgave med en per-run event-log) så et mobil-svar overlever app-baggrund, plus bidirektionel desktop↔mobil-sync — uden at ændre desktop-klienten.

**Architecture:** En ny in-memory `run_event_log` pr. run_id er den eneste sandhed om en runs frames. En detached baggrundstråd kører runnet og appender v2-frames til loggen. `/chat/stream/v2` og nye subscribe-endpoints er bare abonnenter der læser loggen fra et offset. Et `server_authoritative_runs`-flag vælger ny sti vs. nuværende A1-tee. Mobil-klienten gen-abonnerer fra sidste offset ved socket-drop.

**Tech Stack:** Python 3.11 / FastAPI (backend, conda `ai`), React Native + Expo (mobil, worktree), pytest, jest, react-native-sse.

---

## Dev workflow (LÆS FØRST)

- **Backend lever på containeren `10.0.0.39`** (`/media/projects/jarvis-v2`, 332 commits foran origin). Backend-filer redigeres lokalt i `/tmp`, `scp`'es til containeren, og **committes på containerens git**. Deploy = `scp` + `ssh bs@10.0.0.39 "sudo systemctl restart jarvis-api"`.
- Python på containeren: `~/miniconda3/envs/ai/bin/python`. Tests: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest <fil> -q`.
- **Mobil lever i worktree** `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`. Tests: `npx tsc --noEmit` + `npx jest`. Build: bump `app.json` version + `android.versionCode` + `build.gradle` versionCode/versionName, `npx expo prebuild -p android --no-install` (kun ved native-dep-ændring), `cd android && ./gradlew :app:assembleRelease -PreactNativeArchitectures=arm64-v8a`, `adb install -r`.
- **Token til curl-tests:** `ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python scripts/mint_jarvisx_token.py --user-id bjorn --role owner --ttl-days 1 --name test"` → pluk `eyJ...`.
- **--workers 1** → in-memory delt på tværs af endpoints + tråde. Bevar dette.

---

## Phase 1 — run_event_log (den rette primitiv)

### Task 1: `run_event_log.py` + tests

**Files:**
- Create (container): `core/services/run_event_log.py`
- Create (container): `tests/test_run_event_log.py`

- [ ] **Step 1: Skriv den fejlende test**

`tests/test_run_event_log.py`:
```python
import time
import core.services.run_event_log as rel


def setup_function():
    rel._RUNS.clear()


def test_append_read_offset_and_done():
    rel.create("r1", "s1")
    rel.append("r1", "f0")
    rel.append("r1", "f1")
    frames, done = rel.read("r1", 0)
    assert frames == ["f0", "f1"] and done is False
    frames, done = rel.read("r1", 1)
    assert frames == ["f1"] and done is False
    rel.mark_done("r1")
    _, done = rel.read("r1", 2)
    assert done is True


def test_read_unknown_run():
    assert rel.read("nope", 0) == ([], False)


def test_active_run_for_session_returns_latest_not_done():
    rel.create("r1", "s1")
    rel.mark_done("r1")
    rel.create("r2", "s1")
    assert rel.active_run_for_session("s1") == "r2"


def test_is_live_and_live_run_ids():
    rel.create("r1", "s1")
    rel.append("r1", "f")
    assert rel.is_live("r1") is True
    assert rel.live_run_ids() == ["r1"]
    rel.mark_done("r1")
    assert rel.is_live("r1") is False
    assert rel.live_run_ids() == []


def test_is_live_false_when_stale():
    rel.create("r1", "s1")
    rel._RUNS["r1"]["last_append_at"] = time.monotonic() - 999
    assert rel.is_live("r1") is False


def test_frame_cap():
    rel.create("r1", "s1")
    for i in range(rel._MAX_FRAMES + 50):
        rel.append("r1", f"f{i}")
    frames, _ = rel.read("r1", 0)
    assert len(frames) == rel._MAX_FRAMES


def test_prune_keeps_latest_per_session():
    rel.create("r1", "s1")
    rel.mark_done("r1")
    rel.create("r2", "s1")
    rel.mark_done("r2")
    rel.prune()
    assert "r1" not in rel._RUNS  # ældre afsluttet droppet
    assert "r2" in rel._RUNS      # seneste pr. session beholdt
```

- [ ] **Step 2: Kør testen — forvent FAIL**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest tests/test_run_event_log.py -q`
Expected: FAIL (`ModuleNotFoundError: core.services.run_event_log`).

- [ ] **Step 3: Skriv `core/services/run_event_log.py`**

```python
"""In-memory, append-only, offset-indekseret event-log PR. RUN.

Den autoritative sandhed om en visible-runs v2-SSE-frames. Et detached run
appender hertil fra sin baggrundstråd; HTTP-endpoints læser fra et offset og
streamer videre. Keyed pr. run_id (IKKE session — det var A3's fejl, hvor
overlappende runs i samme session klobbede hinandens buffer).

--workers 1 → delt in-memory på tværs af alle endpoints + baggrundstråde.
"""
from __future__ import annotations

import threading
import time

_lock = threading.Lock()
# run_id -> {session_id, frames: list[str], done: bool, last_append_at: float, created_at: float}
_RUNS: dict[str, dict] = {}
_MAX_FRAMES = 4000   # runaway-værn pr. run
_LIVE_IDLE_S = 20.0  # pings hver ~5s holder live under tool-runder
_KEEP_DONE_PER_SESSION = 1  # behold seneste afsluttede log pr. session til sen reconnect


def create(run_id: str, session_id: str) -> None:
    rid = (run_id or "").strip()
    if not rid:
        return
    with _lock:
        _RUNS[rid] = {
            "session_id": (session_id or "").strip(),
            "frames": [],
            "done": False,
            "last_append_at": time.monotonic(),
            "created_at": time.monotonic(),
        }


def append(run_id: str, frame: str) -> None:
    rid = (run_id or "").strip()
    if not rid or not frame:
        return
    with _lock:
        st = _RUNS.get(rid)
        if st is None:
            return
        if len(st["frames"]) < _MAX_FRAMES:
            st["frames"].append(frame)
        st["last_append_at"] = time.monotonic()


def mark_done(run_id: str) -> None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is not None:
            st["done"] = True


def read(run_id: str, from_idx: int) -> tuple[list[str], bool]:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if st is None:
            return ([], False)
        return (st["frames"][from_idx:], bool(st["done"]))


def active_run_for_session(session_id: str) -> str | None:
    sid = (session_id or "").strip()
    newest: tuple[float, str] | None = None
    with _lock:
        for rid, st in _RUNS.items():
            if st["session_id"] == sid and not st["done"]:
                if newest is None or st["created_at"] > newest[0]:
                    newest = (st["created_at"], rid)
    return newest[1] if newest else None


def is_live(run_id: str) -> bool:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        if not st or st["done"]:
            return False
        return (time.monotonic() - st["last_append_at"]) < _LIVE_IDLE_S


def live_run_ids() -> list[str]:
    now = time.monotonic()
    with _lock:
        return [
            rid for rid, st in _RUNS.items()
            if not st["done"] and (now - st["last_append_at"]) < _LIVE_IDLE_S
        ]


def session_for_run(run_id: str) -> str | None:
    with _lock:
        st = _RUNS.get((run_id or "").strip())
        return st["session_id"] if st else None


def prune() -> None:
    """Behold alle ikke-done runs + de seneste _KEEP_DONE_PER_SESSION done-runs
    pr. session; drop ældre afsluttede logs (DB har det endelige svar)."""
    with _lock:
        done_by_session: dict[str, list[tuple[float, str]]] = {}
        for rid, st in _RUNS.items():
            if st["done"]:
                done_by_session.setdefault(st["session_id"], []).append((st["created_at"], rid))
        drop: set[str] = set()
        for _sid, runs in done_by_session.items():
            runs.sort(reverse=True)  # nyeste først
            for _ts, rid in runs[_KEEP_DONE_PER_SESSION:]:
                drop.add(rid)
        for rid in drop:
            _RUNS.pop(rid, None)
```

- [ ] **Step 4: Kør testen — forvent PASS**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest tests/test_run_event_log.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit (på containerens git)**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add core/services/run_event_log.py tests/test_run_event_log.py && git commit -q -m 'feat(runs): per-run event-log (server-authoritative fundament)'"
```

---

## Phase 2 — flag + detached runner

### Task 2: `server_authoritative_runs`-flag i settings

**Files:**
- Modify (container): `core/runtime/settings.py` (Settings-dataclass ~linje 247, serialisering ~397, load ~784)

- [ ] **Step 1: Tilføj feltet til Settings-dataclass** (ved siden af `context_compact_threshold_tokens`)

```python
    server_authoritative_runs: bool = False
```

- [ ] **Step 2: Tilføj til `to_dict`/serialisering** (~linje 397)

```python
            "server_authoritative_runs": self.server_authoritative_runs,
```

- [ ] **Step 3: Tilføj til load-fra-data** (~linje 784)

```python
        server_authoritative_runs=bool(data.get("server_authoritative_runs", defaults.server_authoritative_runs)),
```

- [ ] **Step 4: Verificér load**

Run: `ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -c 'from core.runtime.settings import load_settings; print(load_settings().server_authoritative_runs)'"`
Expected: `False` (flag default OFF — nul adfærdsændring indtil vi flipper).

- [ ] **Step 5: Commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add core/runtime/settings.py && git commit -q -m 'feat(settings): server_authoritative_runs-flag (default OFF)'"
```

### Task 3: Omskriv `detached_run.py` til run_event_log

**Files:**
- Modify (container): `core/services/visible_runs_sections/detached_run.py`
- Modify (container): `tests/test_detached_run.py`

- [ ] **Step 1: Opdater testen** (mock run_event_log i stedet for run_follow)

`tests/test_detached_run.py`:
```python
import time
from unittest import mock


def _make_async_iter(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _patch(monkeypatch, frames):
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2
    created, appended, done = [], [], []
    monkeypatch.setattr(rel, "create", lambda rid, sid: created.append((rid, sid)))
    monkeypatch.setattr(rel, "append", lambda rid, f: appended.append((rid, f)))
    monkeypatch.setattr(rel, "mark_done", lambda rid: done.append(rid))
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _make_async_iter([]))
    monkeypatch.setattr(v2, "translate_to_v2", lambda it, **kw: _make_async_iter(frames))
    return created, appended, done


def test_detached_run_creates_log_appends_and_marks_done(monkeypatch):
    created, appended, done = _patch(monkeypatch, ["a", "b", "c"])
    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    rid = start_user_run_detached(
        message="hej", session_id="s1", eff_model="m", eff_provider="p", lane="l"
    )
    assert rid and created and created[0][1] == "s1"      # log oprettet synkront m. session
    for _ in range(60):
        if len(appended) >= 3 and done:
            break
        time.sleep(0.05)
    assert [f for _r, f in appended] == ["a", "b", "c"]    # alle frames teed
    assert done and done[0] == rid                          # mark_done kørt
```

- [ ] **Step 2: Kør testen — forvent FAIL**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest tests/test_detached_run.py -q`
Expected: FAIL (gammel impl bruger run_follow / forkert signatur).

- [ ] **Step 3: Skriv `core/services/visible_runs_sections/detached_run.py`**

```python
"""Detached (request-uafhængig) bruger-run → server-autoritativt via run_event_log.

Runnet kører i en baggrundstråd og tee'er sine v2-frames til run_event_log[run_id].
HTTP-forbindelser er bare abonnenter. Klient-disconnect aflyser IKKE runnet; det
kører færdigt, persisterer i DB og unregistrerer sig (via gen.aclose i finally).
Log keyed pr. RUN → ingen kollision mellem overlappende runs (A3's fejl elimineret).
"""
from __future__ import annotations

from uuid import uuid4


def start_user_run_detached(
    *,
    message: str,
    session_id: str,
    approval_mode: str = "ask",
    thinking_mode: str = "think",
    force_user_id: str | None = None,
    tool_scope: str = "",
    provider_override: str = "",
    model_override: str = "",
    eff_model: str = "",
    eff_provider: str = "",
    lane: str = "",
) -> str:
    """Start et server-autoritativt run. Returnerer run_id (klienten abonnerer
    via run_event_log gennem /chat/stream/v2 eller /chat/runs/{id}/subscribe)."""
    import contextvars as _ctxvars
    import threading

    import core.services.run_event_log as rel
    from core.services.visible_runs import start_visible_run
    from core.services.visible_runs_sse_v2 import translate_to_v2

    run_id = f"visible-{uuid4().hex}"
    sid = (session_id or "").strip()
    rel.create(run_id, sid)  # synkront FØR retur → straks synlig i live_run_ids

    legacy_iter = start_visible_run(
        message=message,
        session_id=session_id,
        approval_mode=approval_mode,
        thinking_mode=thinking_mode,
        force_user_id=force_user_id,
        tool_scope=tool_scope,
        provider_override=provider_override,
        model_override=model_override,
    )

    def _in_thread() -> None:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()

        async def _consume() -> None:
            gen = translate_to_v2(
                legacy_iter,
                run_id=run_id,
                model=eff_model,
                provider=eff_provider,
                lane=lane,
                session_id=sid,
                ping_interval_s=5.0,
            )
            try:
                async for frame in gen:
                    try:
                        rel.append(run_id, frame)
                    except Exception:
                        pass
            finally:
                try:
                    await gen.aclose()  # → _stream_visible_run finally → unregister
                except Exception:
                    pass
                try:
                    rel.mark_done(run_id)
                except Exception:
                    pass
                try:
                    rel.prune()
                except Exception:
                    pass

        try:
            loop.run_until_complete(_consume())
        except Exception:
            try:
                rel.mark_done(run_id)
            except Exception:
                pass
        finally:
            loop.close()

    _ctx = _ctxvars.copy_context()
    threading.Thread(target=lambda: _ctx.run(_in_thread), name="jarvis-user-run", daemon=True).start()
    return run_id
```

> **Bemærk:** `translate_to_v2` får nu `run_id=run_id` (ikke `""`), så message_start-framen
> bærer det rigtige run_id fra start — klienten kender run_id straks til reconnect.

- [ ] **Step 4: Kør testen — forvent PASS**

Run: `PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest tests/test_detached_run.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add core/services/visible_runs_sections/detached_run.py tests/test_detached_run.py && git commit -q -m 'feat(runs): detached runner tee'er til run_event_log pr. run'"
```

---

## Phase 3 — endpoints (flag-gatet)

### Task 4: `/chat/stream/v2` — flag-gatet detached vs A1-tee

**Files:**
- Modify (container): `apps/api/jarvis_api/routes/chat_stream_v2.py` (erstat `legacy_iter = ...` t.o.m. `return StreamingResponse(...)`, ~linje 119-188)

- [ ] **Step 1: Erstat run-start + respons med flag-gate**

Erstat blokken fra `legacy_iter = start_visible_run(` til og med den afsluttende `)` på `StreamingResponse(...)` med:

```python
    if settings.server_authoritative_runs:
        # SERVER-AUTORITATIV: kør detached + abonnér på run-loggen fra offset 0.
        from core.services.visible_runs_sections.detached_run import start_user_run_detached
        import core.services.run_event_log as rel

        run_id = start_user_run_detached(
            message=effective_message,
            session_id=session_id,
            approval_mode=request.approval_mode,
            thinking_mode=request.thinking_mode,
            force_user_id=_uid,
            tool_scope=_tool_scope,
            provider_override=_prov_override,
            model_override=_model_override,
            eff_model=_eff_model,
            eff_provider=_eff_provider,
            lane=settings.primary_model_lane,
        )

        async def _subscribe():
            import asyncio as _a
            idx = 0
            empty = 0
            while True:
                frames, done = rel.read(run_id, idx)
                for f in frames:
                    idx += 1
                    yield f
                if done:
                    break
                if frames:
                    empty = 0
                else:
                    empty += 1
                    if empty > 300:  # ~24s helt tavst (pings hver 5s holder live) → giv op
                        break
                await _a.sleep(0.08)

        return StreamingResponse(
            _subscribe(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Stream-Protocol": "v2-anthropic",
                "X-Run-Id": run_id,
            },
        )

    # FLAG OFF → nuværende stabile A1-tee (uændret).
    legacy_iter = start_visible_run(
        message=effective_message,
        session_id=session_id,
        approval_mode=request.approval_mode,
        thinking_mode=request.thinking_mode,
        force_user_id=_uid,
        tool_scope=_tool_scope,
        provider_override=_prov_override,
        model_override=_model_override,
    )
    v2_stream = translate_to_v2(
        legacy_iter, run_id="", model=_eff_model, provider=_eff_provider,
        lane=settings.primary_model_lane, session_id=session_id, ping_interval_s=5.0,
    )

    async def _broadcast_tee():
        try:
            from core.services.run_follow import begin_follow, end_follow, publish_follow_frame
        except Exception:
            async for frame in v2_stream:
                yield frame
            return
        try:
            begin_follow(session_id, "")
        except Exception:
            pass
        try:
            async for frame in v2_stream:
                try:
                    publish_follow_frame(session_id, frame)
                except Exception:
                    pass
                yield frame
        finally:
            try:
                end_follow(session_id)
            except Exception:
                pass

    return StreamingResponse(
        _broadcast_tee(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Stream-Protocol": "v2-anthropic",
        },
    )
```

- [ ] **Step 2: Syntakstjek + deploy + restart (flag stadig OFF)**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -c 'import ast; ast.parse(open(\"apps/api/jarvis_api/routes/chat_stream_v2.py\").read()); print(\"OK\")' && sudo systemctl restart jarvis-api && sleep 4 && systemctl is-active jarvis-api"
```

- [ ] **Step 3: Verificér FLAG OFF = uændret (golden baseline)**

Mint token, opret session, stream "Sig kort hej", bekræft `message_stop` + svar persisteret (præcis som i dag). Dette beviser nul regression med flag OFF.

- [ ] **Step 4: Commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add apps/api/jarvis_api/routes/chat_stream_v2.py && git commit -q -m 'feat(stream): flag-gatet server-autoritativ sti (OFF=A1-tee uændret)'"
```

### Task 5: subscribe + sessions/{id}/live endpoints

**Files:**
- Modify (container): `apps/api/jarvis_api/routes/chat.py` (tilføj 2 endpoints før `/sessions/{session_id}/follow`)

- [ ] **Step 1: Tilføj endpoints**

```python
@router.get("/runs/{run_id}/subscribe")
async def chat_run_subscribe(run_id: str, from_idx: int = 0):
    """Gen-abonnér på et server-autoritativt run fra et offset (mobil-reconnect
    efter socket-drop). Catch-up fra from_idx + live-hale til done. 404 hvis
    run_id ukendt/pruned → klient falder tilbage til sessions.select."""
    import asyncio
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    import core.services.run_event_log as rel

    if rel.session_for_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def _gen():
        idx = max(0, int(from_idx))
        empty = 0
        while True:
            frames, done = rel.read(run_id, idx)
            for f in frames:
                idx += 1
                yield f
            if done:
                break
            if frames:
                empty = 0
            else:
                empty += 1
                if empty > 300:
                    break
            await asyncio.sleep(0.08)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": run_id})


@router.get("/sessions/{session_id}/live")
async def chat_session_live(session_id: str):
    """Attach til sessionens aktive run fra offset 0 (cross-device + foreground-
    attach). 204 hvis intet aktivt run."""
    import asyncio
    from fastapi import Response
    from fastapi.responses import StreamingResponse
    import core.services.run_event_log as rel

    run_id = rel.active_run_for_session(session_id)
    if not run_id:
        return Response(status_code=204)

    async def _gen():
        idx = 0
        empty = 0
        while True:
            frames, done = rel.read(run_id, idx)
            for f in frames:
                idx += 1
                yield f
            if done:
                break
            if frames:
                empty = 0
            else:
                empty += 1
                if empty > 300:
                    break
            await asyncio.sleep(0.08)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": run_id})
```

- [ ] **Step 2: Syntakstjek + restart**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -c 'import ast; ast.parse(open(\"apps/api/jarvis_api/routes/chat.py\").read()); print(\"OK\")' && sudo systemctl restart jarvis-api && sleep 4 && systemctl is-active jarvis-api"
```

- [ ] **Step 3: Commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add apps/api/jarvis_api/routes/chat.py && git commit -q -m 'feat(chat): /runs/{id}/subscribe + /sessions/{id}/live (gen-abonnering)'"
```

### Task 6: `/chat/active-runs` → run_event_log (flag-gatet)

**Files:**
- Modify (container): `apps/api/jarvis_api/routes/chat.py` (`chat_active_runs`)

- [ ] **Step 1: Gør active-runs flag-bevidst**

Erstat `chat_active_runs`-kroppen med:
```python
    from core.runtime.settings import load_settings
    if load_settings().server_authoritative_runs:
        import core.services.run_event_log as rel
        sids = []
        for rid in rel.live_run_ids():
            sid = rel.session_for_run(rid)
            if sid and sid not in sids:
                sids.append(sid)
        return {"session_ids": sids}
    # FLAG OFF → run_follow.live_sessions (uændret)
    from core.services.run_follow import live_sessions
    try:
        return {"session_ids": live_sessions()}
    except Exception:
        return {"session_ids": []}
```

- [ ] **Step 2: Restart + commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && sudo systemctl restart jarvis-api && sleep 4 && systemctl is-active jarvis-api && git add apps/api/jarvis_api/routes/chat.py && git commit -q -m 'feat(active-runs): afled fra run_event_log naar flag ON'"
```

---

## Phase 4 — multi-klient integrationstest (LEKTIEN fra A3)

### Task 7: drop+resubscribe+golden-frame harness

**Files:**
- Create (container): `tests/test_server_authoritative_runs.py`

- [ ] **Step 1: Skriv integrationstesten** (mod kørende api på `127.0.0.1:8080`, flag ON)

```python
"""Multi-klient integrationstest — kerne-lektien fra A3 ('verificeret med kun curl').
KRÆVER: jarvis-api kører på 127.0.0.1:8080 MED server_authoritative_runs=true,
og en gyldig owner-token i env JARVIS_TEST_TOKEN.

Kør: JARVIS_TEST_TOKEN=eyJ... ~/miniconda3/envs/ai/bin/python -m pytest \
     tests/test_server_authoritative_runs.py -q -s
"""
import os
import time
import urllib.request

import pytest

BASE = "http://127.0.0.1:8080"
TOK = os.environ.get("JARVIS_TEST_TOKEN", "")
pytestmark = pytest.mark.skipif(not TOK, reason="kræver JARVIS_TEST_TOKEN + kørende api")


def _post(path, body):
    req = urllib.request.Request(
        BASE + path, data=__import__("json").dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
        method="POST")
    return urllib.request.urlopen(req, timeout=30)


def _mk_session():
    import json
    r = _post("/chat/sessions", {"title": "satest"})
    return json.load(r)["session"]["id"]


def _read_frames(resp, max_frames=99999):
    out = []
    for raw in resp:
        line = raw.decode(errors="replace")
        if line.startswith("data:"):
            out.append(line)
            if '"type": "message_stop"' in line or '"type":"message_stop"' in line:
                break
        if len(out) >= max_frames:
            break
    return out


def test_drop_midstream_then_resubscribe_no_gap_and_completes():
    sid = _mk_session()
    resp = _post("/chat/stream/v2", {
        "session_id": sid, "message": "Tael langsomt til 15",
        "approval_mode": "trust", "thinking_mode": "none"})
    run_id = resp.headers.get("X-Run-Id")
    assert run_id, "server-autoritativ sti skal sætte X-Run-Id (er flag ON?)"
    # læs ~5 data-frames, drop så forbindelsen
    first = _read_frames(resp, max_frames=5)
    resp.close()
    offset = len(first)
    # gen-abonnér fra offset → skal fange op + nå message_stop
    req = urllib.request.Request(
        f"{BASE}/chat/runs/{run_id}/subscribe?from_idx={offset}",
        headers={"Authorization": f"Bearer {TOK}"})
    resp2 = urllib.request.urlopen(req, timeout=40)
    rest = _read_frames(resp2)
    resp2.close()
    assert any("message_stop" in f for f in rest), "reconnect skal nå message_stop"


def test_unknown_run_404():
    req = urllib.request.Request(
        f"{BASE}/chat/runs/visible-doesnotexist/subscribe",
        headers={"Authorization": f"Bearer {TOK}"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code == 404
```

- [ ] **Step 2: Kør harness MOD lokal api med flag ON (skygge-verifikation FØR live)**

På containeren: sæt `server_authoritative_runs=true` i `~/.jarvis-v2/config/runtime.json`, restart, mint token, kør:
```bash
JARVIS_TEST_TOKEN=<token> PYTHONPATH=/media/projects/jarvis-v2 ~/miniconda3/envs/ai/bin/python -m pytest tests/test_server_authoritative_runs.py -q -s
```
Expected: 2 passed (drop+resubscribe når message_stop; ukendt run → 404).

- [ ] **Step 3: Golden-frame desktop-kompat-tjek (manuelt, dokumentér)**

Med flag OFF: dump frame-typerne for "Sig kort hej". Med flag ON: samme. Bekræft sekvensen (message_start → content_block_* → message_stop) er identisk. Noter resultatet i commit-beskeden.

- [ ] **Step 4: Commit**

```bash
ssh bs@10.0.0.39 "cd /media/projects/jarvis-v2 && git add tests/test_server_authoritative_runs.py && git commit -q -m 'test(runs): multi-klient drop+resubscribe+404 harness (A3-modgift)'"
```

---

## Phase 5 — mobil-klient (gen-abonnering)

### Task 8: streamClient offset-sporing + reconnect

**Files:**
- Modify (worktree): `apps/mobile/src/lib/streamClient.ts`
- Modify (worktree): `apps/mobile/src/lib/apiClient.ts` (tilføj subscribe-URL-helper hvis nødvendigt — ellers byg URL i streamClient)

- [ ] **Step 1: Tilføj reconnect-felter til StreamRequest/StreamControl + en `subscribeRun`-funktion**

I `streamClient.ts`: udvid `startStream` så den (a) tæller modtagne frames i `offset`, (b) fanger `run_id` fra X-Run-Id ELLER message_start, (c) ved 'error' før message_stop kalder en intern `reconnect(offset, runId)` der åbner en GET-EventSource mod `/chat/runs/{runId}/subscribe?from_idx={offset}` og fortsætter samme handlers (genbrug eksisterende frame-parsing). Backoff: 500ms·2^n, max 5 forsøg; derefter `onError`. Vis status via en ny `onReconnecting?()`-handler.

```typescript
export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void
  onRunId?: (runId: string) => void
  onReconnecting?: (attempt: number) => void
  onInterrupted?: () => void
  onError?: (error: Error) => void
  onComplete?: () => void
}
```

Kernelogik (skitse — implementér fuldt): træk frame-listener-loopet ud i en
genbrugelig `attach(url, method, body)` der opdaterer `offset` pr. modtaget
data-frame og sætter `gotStop` på message_stop. `startStream` kalder
`attach(POST /chat/stream/v2, body)`. 'error'-handleren (hvis !gotStop):
```typescript
if (runId && attempt < 5) {
  attempt += 1
  handlers.onReconnecting?.(attempt)
  setTimeout(() => attach(`/chat/runs/${runId}/subscribe?from_idx=${offset}`, 'GET'),
             500 * 2 ** (attempt - 1))
} else {
  handlers.onInterrupted?.(); handlers.onError?.(detailedError(event))
}
```

- [ ] **Step 2: Test (jest)** — `streamClient.test.ts`: simulér message_start (sætter runId) → 'error' → forvent at en ny EventSource åbnes mod subscribe-URL'en med korrekt `from_idx`. Mock `react-native-sse` så vi kan inspicere konstruktør-URL'er.

- [ ] **Step 3: Kør jest** — `npx jest src/lib/streamClient.test.ts` → PASS.

- [ ] **Step 4: Commit**

```bash
cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 && git add apps/mobile/src/lib/streamClient.ts apps/mobile/src/lib/streamClient.test.ts && git commit -q -m "feat(mobile): auto-reconnect fra offset ved socket-drop"
```

### Task 9: StreamContext + ChatScreen wiring

**Files:**
- Modify (worktree): `apps/mobile/src/state/StreamContext.tsx` (videregiv onReconnecting → en `reconnecting`-status; behold lastError til ægte fejl)
- Modify (worktree): `apps/mobile/src/screens/ChatScreen.tsx` (vis "genforbinder…" i stedet for "Stream fejlede" mens reconnecting; foreground-resume → `/sessions/{id}/live` via en `attachLive`-helper)

- [ ] **Step 1: StreamContext** — tilføj `reconnecting: boolean` til context-value; sæt true i onReconnecting, false ved næste onEvent/onComplete/onError.
- [ ] **Step 2: ChatScreen** — banner: hvis `stream.reconnecting`, vis diskret "Genforbinder…" (ikke fejl). Behold ErrorBanner kun ved ægte `status==='error'` efter opbrugte forsøg.
- [ ] **Step 3: Foreground-resume** — i AppState-effekten: efter `sessions.select`, hvis `/chat/active-runs` viser sessionen aktiv, kald en `stream.attachLive(config, sessionId)` der åbner `/sessions/{id}/live` og fodrer reducer.
- [ ] **Step 4: tsc + jest** — `npx tsc --noEmit && npx jest` → grønt (opdatér ChatScreen.test-mock med `reconnecting` + evt. `attachLive`).
- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 && git add -A && git commit -q -m "feat(mobile): genforbinder-status + foreground attach-live"
```

---

## Phase 6 — udrulning (flag-styret)

### Task 10: Deploy OFF → verificér desktop → flip ON → on-device

- [ ] **Step 1:** Bekræft flag OFF i `~/.jarvis-v2/config/runtime.json` på containeren; restart; verificér desktop-app + mobil streamer som i dag (nul regression). Golden-baseline.
- [ ] **Step 2:** Byg mobil med Task 8-9 (bump version, build, `adb install -r`).
- [ ] **Step 3:** Flip `server_authoritative_runs=true` i runtime.json; restart.
- [ ] **Step 4: On-device-smoke (Bjørn):** send besked → baggrund appen midt i svaret → vent → vend tilbage → svaret skal stå færdigt (auto-reconnect). Send fra desktop → mobil viser live. Send fra mobil → desktop viser live (bidirektionel).
- [ ] **Step 5:** Hvis noget overrasker: flip flag OFF (øjeblikkelig tilbagerulning, ingen deploy). Ellers: opdatér memory ([[reference_mobile_stream_socket_abort]], [[project_live_session_broadcast]]) + tag mobil-baseline.

---

## Self-review-noter

- **Spec-dækning:** run_event_log (T1) ✓, flag (T2) ✓, detached runner (T3) ✓, stream-route flag-gate (T4) ✓, subscribe+live (T5) ✓, active-runs (T6) ✓, multi-klient-test (T7) ✓, mobil-reconnect (T8-9) ✓, flag-udrulning (T10) ✓. FCM-push bevidst udeladt (Stykke B).
- **Type-konsistens:** `run_id` overalt; `from_idx` query-param matcher klientens `offset`; `read(run_id, from_idx)→(frames,done)` brugt ens i alle tre subscribe-loops.
- **Desktop urørt:** flag OFF = nuværende kode; flag ON = desktop modtager identiske frames via /chat/stream/v2 (samme translate_to_v2-output), kun afleveret via subscribe-loop i stedet for tee — golden-frame-verificeret i T7 Step 3.
