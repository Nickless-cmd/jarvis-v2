# Server Tier-0-lite Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Kill the "blind lane" and multi-user blocker on `/v1/agent/step` and lay the multimodal foundation — flag-gated, additive, and inert-by-default on the live jarvis-v2 API.

**Architecture:** All work lives server-side in `apps/api/jarvis_api/routes/agent_loop.py` plus two additive helper changes in `core/costing/ledger.py` (record_cost user_id) and `core/runtime/db_schema.py` (costs.user_id column). Every behavior change is either purely additive JSON (extra response keys clients ignore) or gated behind a runtime-state flag defaulting OFF, so flipping the deploy on changes nothing until an operator sets the flag. `finish_reason` is plumbed through the two existing provider-runtime seams (`cheap_provider_runtime_adapters.py`, `cheap_provider_runtime_streaming.py`) as single additive dict keys.

**Tech Stack:** Python 3.11, FastAPI, pytest (`/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`), sqlite (via `core.runtime.db.connect`), runtime-state KV flags (`core.runtime.db_core.get_runtime_state_value`).

**Repo constraint reminder:** This is ALL `[SERVER jarvis-v2]`. jarvis-code (`/home/bs/jarvis-code`) CANNOT `import core.*`; it consumes only the JSON/SSE shapes produced here. No client changes in this phase — the additive envelope + `finish_reason` are the *foundation* the Fase-1 client (A6, image input) will later read.

## File Structure

| File | Create/Modify | One responsibility |
|---|---|---|
| `apps/api/jarvis_api/routes/agent_loop.py` | Modify | The `/v1/agent/step` route + helpers: flag helper, envelope, seam observability, finish_reason, user scoping, block-aware content. |
| `core/costing/ledger.py` | Modify | `record_cost` gains an optional additive `user_id` param written to the ledger. |
| `core/runtime/db_schema.py` | Modify | Additive `costs.user_id` column migration (ALTER, DEFAULT ''). |
| `core/services/cheap_provider_runtime_adapters.py` | Modify | `_execute_openai_compatible_chat` return dict gains additive `finish_reason` key (<20 lines; single-key plumb). |
| `core/services/cheap_provider_runtime_streaming.py` | Modify | `_iter_openai_compatible_chat_events` `done` event gains additive `finish_reason` key (<20 lines; single-key plumb). |
| `tests/api/test_agent_step_envelope.py` | Create | Envelope + cost_usd + finish_reason + observability + scoping + multimodal route tests. |
| `tests/costing/test_record_cost_user_id.py` | Create | `record_cost` user_id write + `costs.user_id` column existence. |

**Boy Scout note:** `agent_loop.py` is 445 lines, `ledger.py` 247 — both well under 2000, no split required. The two `cheap_provider_runtime_*` files receive a single additive dict key each (<20 lines, additive plumb, not a logic change) so the Boy Scout split rule does not trigger. If a worker's edit to either file grows past 20 lines, stop and re-scope.

---

### Task 1: Flag helper + monkeypatchable module-level seams [SERVER jarvis-v2]

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (imports block ~lines 28-34; add helper after `_resolve_role` ~line 44)
- Test: `tests/api/test_agent_step_envelope.py` (Create)

Foundation task: add a runtime-state flag reader (default OFF) and hoist the observability seams to module level so later tasks can gate and tests can monkeypatch them. No behavior change yet.

- [ ] Step: Write failing test `tests/api/test_agent_step_envelope.py`:
```python
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

client = TestClient(app)


def test_flag_defaults_off():
    # Unknown flag key must read False (fail-safe: new behavior inert until enabled).
    assert al._flag("jc_agent_totally_unknown_flag_xyz") is False


def test_flag_reads_runtime_state(monkeypatch):
    monkeypatch.setattr(al, "get_runtime_state_value",
                        lambda key, default=None: True if key == "jc_agent_observability" else default)
    assert al._flag("jc_agent_observability") is True
    assert al._flag("jc_agent_user_scoping") is False


def test_seam_names_exist_for_monkeypatch():
    # Observability seams must be module-level names so tests can patch them.
    assert callable(al.record_cost)
    assert callable(al.note_empty_completion)
```
- [ ] Step: Run `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_agent_step_envelope.py -o addopts="" -q` — expect FAIL (`_flag`, `get_runtime_state_value`, `record_cost`, `note_empty_completion` not module attrs).
- [ ] Step: Implement — add to the imports block of `agent_loop.py` (after line 31, the existing `from core.tools.brain_write_gate import check_brain_write_allowed`):
```python
# Module-level seams (tests monkeypatch these; keeps side effects gate-able):
from core.runtime.db_core import get_runtime_state_value
from core.costing.ledger import record_cost
from core.services.followup_observer import note_empty_completion
```
- [ ] Step: Implement — add helper directly after `_resolve_role` (after line 43):
```python
def _flag(name: str, default: bool = False) -> bool:
    """Read a runtime-state boolean flag. Fail-safe: any error/absence -> default.
    All Fase-0 behavior changes gate on these; every flag defaults OFF so the
    deploy is inert until an operator flips it."""
    try:
        return bool(get_runtime_state_value(name, default))
    except Exception:
        return default
```
- [ ] Step: Run the same pytest command — expect PASS (3 tests).
- [ ] Step: Commit: `git commit -am "feat(agent-step): flag helper + module-level observability seams (inert)"`.

---

### Task 2: Additive costs.user_id column [SERVER jarvis-v2]

**Files:**
- Modify: `core/runtime/db_schema.py` (costs migration block, after line 398 — same pattern as `cache_hit_tokens`/`cache_miss_tokens`)
- Test: `tests/costing/test_record_cost_user_id.py` (Create)

- [ ] Step: Write failing test `tests/costing/test_record_cost_user_id.py`:
```python
from core.runtime.db import connect


def test_costs_table_has_user_id_column():
    # ensure_schema runs on first connect(); the additive column must be present.
    with connect() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(costs)")}
    assert "user_id" in cols
```
- [ ] Step: Run `/opt/conda/envs/ai/bin/python -m pytest tests/costing/test_record_cost_user_id.py::test_costs_table_has_user_id_column -o addopts="" -q` — expect FAIL (no `user_id` column).
- [ ] Step: Implement — in `core/runtime/db_schema.py`, immediately after line 398 (the `cache_miss_tokens` ALTER) and using the already-computed `_cost_cols` set:
```python
        if "user_id" not in _cost_cols:
            conn.execute("ALTER TABLE costs ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
```
- [ ] Step: Also add `user_id TEXT NOT NULL DEFAULT ''` to the `CREATE TABLE IF NOT EXISTS costs` body (after the `cache_miss_tokens` line, before `created_at`) so fresh DBs get the column without relying on the ALTER:
```python
                cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
                user_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
```
- [ ] Step: Run the pytest command — expect PASS.
- [ ] Step: Commit: `git commit -am "feat(costs): additive user_id column (DEFAULT '')"`.

---

### Task 3: record_cost gains optional user_id [SERVER jarvis-v2]

**Files:**
- Modify: `core/costing/ledger.py` (signature line 9-19; INSERT columns line 47-51; VALUES line 52-65)
- Test: `tests/costing/test_record_cost_user_id.py` (extend)

Depends on Task 2 (column must exist).

- [ ] Step: Write failing test — append to `tests/costing/test_record_cost_user_id.py`:
```python
import core.costing.ledger as ledger


class _FakeConn:
    def __init__(self, sink):
        self.sink = sink
    def execute(self, sql, params=None):
        if params is not None:
            self.sink["sql"] = " ".join(sql.split())
            self.sink["params"] = params
        return self
    def commit(self):
        self.sink["committed"] = True
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_record_cost_writes_user_id(monkeypatch):
    sink = {}
    monkeypatch.setattr(ledger, "connect", lambda: _FakeConn(sink))
    # keep the egress side-effect from firing during the test
    import core.services.central_llm_egress as egress
    monkeypatch.setattr(egress, "observe", lambda **k: None)
    ledger.record_cost(lane="agent", provider="deepseek", model="deepseek-v4-flash",
                       input_tokens=10, output_tokens=5, cost_usd=0.001, user_id="member_x")
    assert "user_id" in sink["sql"]
    assert "member_x" in sink["params"]


def test_record_cost_user_id_defaults_empty(monkeypatch):
    sink = {}
    monkeypatch.setattr(ledger, "connect", lambda: _FakeConn(sink))
    import core.services.central_llm_egress as egress
    monkeypatch.setattr(egress, "observe", lambda **k: None)
    ledger.record_cost(lane="agent", provider="deepseek", model="deepseek-v4-flash",
                       input_tokens=1, output_tokens=1, cost_usd=0.0)
    # additive default: no user_id passed -> '' written, old call sites unaffected
    assert sink["params"][-2] == ""  # user_id is second-to-last (before created_at)
```
- [ ] Step: Run `/opt/conda/envs/ai/bin/python -m pytest tests/costing/test_record_cost_user_id.py -o addopts="" -q` — expect FAIL (unexpected `user_id` kwarg / column not written).
- [ ] Step: Implement — in `core/costing/ledger.py` add `user_id: str = "",` to the `record_cost` signature (after `cache_miss_tokens: int = 0,`, before the closing `) -> None:` on line 19).
- [ ] Step: Implement — extend the INSERT column list (line 48-52) to include `user_id` before `created_at`:
```python
            INSERT INTO costs (
                lane, provider, model, input_tokens, output_tokens, cost_usd,
                cache_hit_tokens, cache_miss_tokens, user_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```
- [ ] Step: Implement — add `str(user_id or ""),` to the VALUES tuple (after `int(cache_miss_tokens),`, before `datetime.now(UTC).isoformat(),` on line 63).
- [ ] Step: Run the pytest command — expect PASS (4 tests in file).
- [ ] Step: Commit: `git commit -am "feat(costs): record_cost optional additive user_id"`.

---

### Task 4: Additive structured envelope + cost_usd (non-stream + stream done) [SERVER jarvis-v2]

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (`agent_step` non-stream return, lines 369-392; `_stream_step` done SSE, lines 425-444)
- Test: `tests/api/test_agent_step_envelope.py` (extend)

Purely additive JSON keys — existing clients ignore unknown keys, so this needs no flag. `finish_reason` values are wired in Task 6 (kept `""` here until then; asserted present now).

- [ ] Step: Write failing tests — append to `tests/api/test_agent_step_envelope.py`:
```python
def _patch_model(monkeypatch, text="hej", tool_calls=None, tin=12, tout=7, cost=0.002, fr="stop"):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    def _fake_chat(**kw):
        return {"text": text, "tool_calls": tool_calls or [], "input_tokens": tin,
                "output_tokens": tout, "cost_usd": cost, "finish_reason": fr}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)


def test_nonstream_envelope_additive(monkeypatch):
    _patch_model(monkeypatch)
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.status_code == 200
    b = r.json()
    # additive envelope
    assert b["status"] == "ok"
    assert b["tokens_in"] == 12 and b["tokens_out"] == 7
    assert b["cost_usd"] == 0.002
    assert isinstance(b["duration_ms"], int) and b["duration_ms"] >= 0
    assert b["result"] == "hej"
    assert b["finish_reason"] == "stop"
    # back-compat: old keys still present
    assert b["content"] == "hej" and b["done"] is True
    assert b["usage"]["prompt_tokens"] == 12


def test_nonstream_status_empty(monkeypatch):
    _patch_model(monkeypatch, text="", tool_calls=[])
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.json()["status"] == "empty"


def test_stream_done_has_cost_and_envelope(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    def _fake_iter(**kw):
        yield {"kind": "delta", "text": "hej"}
        yield {"kind": "done", "full_text": "hej", "input_tokens": 3, "output_tokens": 2,
               "cost_usd": 0.0009, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events",
        _fake_iter)
    with client.stream("POST", "/v1/agent/step",
                       json={"messages": [{"role": "user", "content": "hej"}], "stream": True}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    assert "event: done" in body
    import json as _j
    done = [ln for ln in body.splitlines() if ln.startswith("data:") and "cost_usd" in ln][-1]
    payload = _j.loads(done[len("data: "):])
    assert payload["cost_usd"] == 0.0009
    assert payload["status"] == "ok"
    assert payload["tokens_in"] == 3 and payload["tokens_out"] == 2
    assert payload["finish_reason"] == "stop"
```
- [ ] Step: Run `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_agent_step_envelope.py -o addopts="" -q` — expect FAIL (envelope keys absent).
- [ ] Step: Implement non-stream — in `agent_step`, wrap the model call with timing and build the additive envelope. Replace lines 369-392:
```python
    import time as _time
    _t0 = _time.monotonic()
    try:
        raw = _execute_openai_compatible_chat(
            provider=provider, model=model, auth_profile=auth_profile,
            base_url=base_url, messages=chat_messages, tools=tools,
        )
    except Exception as exc:
        logger.exception("agent/step model-kald fejlede: %s", exc)
        return JSONResponse(status_code=502, content={
            "error": {"message": f"model-kald fejlede: {exc}", "type": "upstream_error"}})
    _dur_ms = int((_time.monotonic() - _t0) * 1000)

    tool_calls = list(raw.get("tool_calls") or [])
    content = str(raw.get("text") or "")
    tokens_in = int(raw.get("input_tokens") or 0)
    tokens_out = int(raw.get("output_tokens") or 0)
    cost_usd = float(raw.get("cost_usd") or 0.0)
    finish_reason = str(raw.get("finish_reason") or "")
    status = "ok" if (content or tool_calls) else "empty"
    return JSONResponse(content={
        # additive structured envelope (Fase 0 O1)
        "status": status,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "duration_ms": _dur_ms,
        "finish_reason": finish_reason,
        "result": content,
        # back-compat keys (existing jarvis-code client reads these)
        "content": content,
        "tool_calls": tool_calls,
        "done": not tool_calls,
        "provider": provider,
        "model": model,
        "usage": {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "cost_usd": cost_usd,
        },
    })
```
- [ ] Step: Implement stream — in `_stream_step`, add timing and enrich the `done` SSE. Add `import time as _time; _t0 = _time.monotonic()` at the top of the function body (after the import of `_iter_openai_compatible_chat_events`, line 401). Then replace the `done` branch (lines 425-436) with:
```python
            elif kind == "done":
                if collected:
                    yield _sse("tool_calls", {"tool_calls": collected})
                _content = str(ev.get("full_text") or full)
                _tin = int(ev.get("input_tokens") or 0)
                _tout = int(ev.get("output_tokens") or 0)
                _cost = float(ev.get("cost_usd") or 0.0)
                _fr = str(ev.get("finish_reason") or "")
                _status = "ok" if (_content or collected) else "empty"
                yield _sse("done", {
                    "status": _status,
                    "tokens_in": _tin,
                    "tokens_out": _tout,
                    "cost_usd": _cost,
                    "duration_ms": int((_time.monotonic() - _t0) * 1000),
                    "finish_reason": _fr,
                    "result": _content,
                    # back-compat
                    "content": _content,
                    "done": not collected,
                    "usage": {"prompt_tokens": _tin, "completion_tokens": _tout},
                })
                return
```
- [ ] Step: Also enrich the fallback `done` at the end of `_stream_step` (lines 442-444) so a stream that ends without an explicit done still emits an envelope:
```python
    if collected:
        yield _sse("tool_calls", {"tool_calls": collected})
    yield _sse("done", {
        "status": "ok" if (full or collected) else "empty",
        "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
        "duration_ms": int((_time.monotonic() - _t0) * 1000),
        "finish_reason": "", "result": full,
        "content": full, "done": not collected, "usage": {},
    })
```
- [ ] Step: Run the pytest command — expect PASS.
- [ ] Step: Commit: `git commit -am "feat(agent-step): additive structured envelope + cost_usd on response & stream done"`.

---

### Task 5: note_empty_completion + agent_step nerve at the model seam (flag-gated) [SERVER jarvis-v2]

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (`agent_step` after `_dur_ms` computed, before the return built in Task 4; `_stream_step` done branch)
- Test: `tests/api/test_agent_step_envelope.py` (extend)

Side-effecting (emits a nerve + can open a central incident) → gated behind `jc_agent_observability`, default OFF.

- [ ] Step: Write failing tests — append:
```python
def test_observability_off_by_default(monkeypatch):
    _patch_model(monkeypatch, text="", tool_calls=[])  # empty completion
    called = {"empty": 0, "nerve": 0}
    monkeypatch.setattr(al, "note_empty_completion",
                        lambda *a, **k: called.__setitem__("empty", called["empty"] + 1))
    monkeypatch.setattr(al, "_emit_agent_nerve",
                        lambda **k: called.__setitem__("nerve", called["nerve"] + 1))
    # flag defaults OFF -> no side effects
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert r.status_code == 200
    assert called == {"empty": 0, "nerve": 0}


def test_observability_on_emits_nerve_and_empty(monkeypatch):
    _patch_model(monkeypatch, text="", tool_calls=[])
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_observability")
    seen = {}
    monkeypatch.setattr(al, "note_empty_completion",
                        lambda run_id, **k: seen.__setitem__("empty", k))
    nerves = []
    monkeypatch.setattr(al, "_emit_agent_nerve", lambda **k: nerves.append(k))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "x"}],
                          "stream": False, "session_id": "s1"})
    assert r.status_code == 200
    assert seen["empty"]["path"] == "agent_step"
    assert nerves and nerves[0]["status"] == "empty"
    assert nerves[0]["tokens_out"] == 0


def test_observability_on_nonempty_only_nerve(monkeypatch):
    _patch_model(monkeypatch, text="svar", tout=4)
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_observability")
    empties = []
    monkeypatch.setattr(al, "note_empty_completion", lambda *a, **k: empties.append(k))
    nerves = []
    monkeypatch.setattr(al, "_emit_agent_nerve", lambda **k: nerves.append(k))
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert empties == []            # non-empty -> no empty_completion
    assert nerves[0]["status"] == "ok"
```
- [ ] Step: Run pytest for the file — expect FAIL (`_emit_agent_nerve` missing; no gating logic).
- [ ] Step: Implement — add the nerve helper after `_flag` in `agent_loop.py`:
```python
def _emit_agent_nerve(*, status: str, provider: str, model: str,
                      tokens_in: int, tokens_out: int, cost_usd: float,
                      duration_ms: int, tool_calls: int, finish_reason: str,
                      user_id: str, session_id: str) -> None:
    """Make the client-owned agent lane visible in Den Intelligente Central.
    Self-safe: any failure is swallowed (observability must never break a turn)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "agent", "nerve": "agent_step",
            "status": str(status), "provider": str(provider), "model": str(model),
            "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
            "cost_usd": float(cost_usd), "duration_ms": int(duration_ms),
            "tool_calls": int(tool_calls), "finish_reason": str(finish_reason),
            "user_id": str(user_id or ""), "session_id": str(session_id or ""),
        })
    except Exception:
        logger.debug("agent/step nerve emit fejlede", exc_info=True)
```
- [ ] Step: Implement — in `agent_step`, read `session_id`/`user_id` from the body near the top (after `context = ...`, line 328):
```python
    session_id = str(body.get("session_id") or "")
    user_id = str(body.get("user_id") or "").strip()
```
- [ ] Step: Implement — in `agent_step`, right after `status = "ok" if ... else "empty"` (from Task 4) and BEFORE the return, add the gated block:
```python
    if _flag("jc_agent_observability"):
        _emit_agent_nerve(
            status=status, provider=provider, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
            duration_ms=_dur_ms, tool_calls=len(tool_calls),
            finish_reason=finish_reason, user_id=user_id, session_id=session_id)
        if status == "empty":
            try:
                note_empty_completion(
                    f"jc-agent-{session_id or 'nosess'}", provider=provider, model=model,
                    rounds=1, tools_executed=0, session_id=session_id, path="agent_step")
            except Exception:
                logger.debug("agent/step note_empty_completion fejlede", exc_info=True)
```
- [ ] Step: Implement — mirror in `_stream_step` done branch (after `_status` is computed in Task 4), gated identically. Note `_stream_step` currently takes no `session_id`/`user_id`; add `session_id: str = "", user_id: str = ""` params to its signature (line 395-396) and pass them from the `StreamingResponse` call in `agent_step` (lines 363-366: add `session_id=session_id, user_id=user_id`). Then in the done branch:
```python
                if _flag("jc_agent_observability"):
                    _emit_agent_nerve(
                        status=_status, provider=provider, model=model,
                        tokens_in=_tin, tokens_out=_tout, cost_usd=_cost,
                        duration_ms=int((_time.monotonic() - _t0) * 1000),
                        tool_calls=len(collected), finish_reason=_fr,
                        user_id=user_id, session_id=session_id)
                    if _status == "empty":
                        try:
                            note_empty_completion(
                                f"jc-agent-{session_id or 'nosess'}", provider=provider,
                                model=model, rounds=1, tools_executed=0,
                                session_id=session_id, path="agent_step_stream")
                        except Exception:
                            logger.debug("stream note_empty_completion fejlede", exc_info=True)
```
- [ ] Step: Run the pytest command — expect PASS. Run the FULL file `tests/api/test_agent_step_envelope.py` to confirm no regression.
- [ ] Step: Commit: `git commit -am "feat(agent-step): flag-gated agent_step nerve + note_empty_completion at model seam"`.

---

### Task 6: Plumb finish_reason adapter -> iterator -> route [SERVER jarvis-v2]

**Files:**
- Modify: `core/services/cheap_provider_runtime_adapters.py` (`_execute_openai_compatible_chat` return dict, line 543-559)
- Modify: `core/services/cheap_provider_runtime_streaming.py` (`_iter_openai_compatible_chat_events` done yield, line 303-312)
- Test: `tests/api/test_agent_step_envelope.py` already asserts `finish_reason` surfaces (Task 4); add adapter-level unit tests here.

Single additive dict key in each provider seam. `agent_step`/`_stream_step` already read `raw.get("finish_reason")`/`ev.get("finish_reason")` (Task 4) — those return `""` until this task lands real values.

- [ ] Step: Write failing test — append to `tests/api/test_agent_step_envelope.py`:
```python
def test_adapter_returns_finish_reason(monkeypatch):
    import core.services.cheap_provider_runtime_adapters as ad
    fake_data = {"choices": [{"finish_reason": "length",
                              "message": {"content": "trunc", "tool_calls": []}}],
                 "usage": {"prompt_tokens": 5, "completion_tokens": 4}}

    class _Facade:
        def _require_credentials(self, **k): return {"api_key": "x"}
        def provider_runtime_defaults(self, p): return {"base_url": "http://x"}
        def _http_json(self, *a, **k): return fake_data, {}
    monkeypatch.setattr(ad, "_facade", lambda: _Facade())
    out = ad._execute_openai_compatible_chat(
        provider="deepseek", model="deepseek-v4-flash", auth_profile="deepseek",
        base_url="http://x", messages=[{"role": "user", "content": "hi"}])
    assert out["finish_reason"] == "length"
```
- [ ] Step: Run `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_agent_step_envelope.py::test_adapter_returns_finish_reason -o addopts="" -q` — expect FAIL (`finish_reason` KeyError).
- [ ] Step: Implement adapter — in `cheap_provider_runtime_adapters.py`, capture the choice's finish_reason near where `first_msg` is derived (line 518) and add it to the return dict (after `"cost_usd": ...`, line 558):
```python
    _first_choice = (data.get("choices") or [{}])[0] or {}
    ...
        "cost_usd": float(_estimate_cheap_cost(provider=provider, usage=enriched_usage)),
        "finish_reason": str(_first_choice.get("finish_reason") or ""),
    }
```
(Reuse `_first_choice` for `first_msg = _first_choice.get("message") or {}` on line 518 so the choice is parsed once.)
- [ ] Step: Implement streaming — in `cheap_provider_runtime_streaming.py`, add `"finish_reason": _finish_reason,` to the `done` yield dict (after `"cost_usd": cost_usd,`, line 311). `_finish_reason` is already captured at line 126/258.
- [ ] Step: Run the adapter test — expect PASS. Re-run `test_nonstream_envelope_additive` and `test_stream_done_has_cost_and_envelope` from Task 4 (they assert `finish_reason == "stop"`); with the fake model they already pass, but now the real seams carry the value too.
- [ ] Step: Commit: `git commit -am "feat(runtime): plumb finish_reason through openai-compat adapter + stream iterator"`.

---

### Task 7: user_id scoping into system-prompt build (flag-gated) [SERVER jarvis-v2]

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (`_identity_context` line 62; `_full_context` line 90 + cache key line 97/116; `_build_system_prompt` line 120; `agent_step` call site line 359; pass `user_id` to `record_cost` in Task 5's block)
- Test: `tests/api/test_agent_step_envelope.py` (extend)

Today `_identity_context` hardcodes `ensure_default_workspace(name="default")` and `_full_context` hardcodes `build_visible_chat_prompt_assembly(..., name="default")` — Bjørn's workspace for EVERY caller. Gate behind `jc_agent_user_scoping` (default OFF → `name="default"` exactly as today). **Cache-bleed fix:** `_FULL_CTX_CACHE` key MUST include the workspace name, else user A's assembled memory leaks to user B.

- [ ] Step: Write failing tests — append:
```python
def test_scoping_off_uses_default_workspace(monkeypatch):
    _patch_model(monkeypatch)
    seen = {}
    monkeypatch.setattr(al, "_identity_context", lambda name="default": seen.__setitem__("name", name) or "")
    # flag OFF -> name resolves to "default" regardless of body user_id
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}],
                      "stream": False, "user_id": "member_x", "context": "identity"})
    assert seen["name"] == "default"


def test_scoping_on_resolves_caller_workspace(monkeypatch):
    _patch_model(monkeypatch)
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_user_scoping")
    monkeypatch.setattr(al, "_resolve_workspace_name",
                        lambda user_id: "ws_member_x" if user_id == "member_x" else "default")
    seen = {}
    monkeypatch.setattr(al, "_identity_context", lambda name="default": seen.__setitem__("name", name) or "")
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}],
                      "stream": False, "user_id": "member_x", "context": "identity"})
    assert seen["name"] == "ws_member_x"


def test_full_context_cache_key_includes_workspace(monkeypatch):
    # same user_message, different workspace -> distinct cache entries (no bleed)
    calls = []
    def _fake_assembly(*, provider, model, user_message, name="default"):
        calls.append(name)
        class _A: text = f"CTX::{name}"
        return _A()
    monkeypatch.setattr("core.services.prompt_contract.build_visible_chat_prompt_assembly",
                        _fake_assembly)
    al._FULL_CTX_CACHE.clear()
    a = al._full_context("same message", name="ws_a")
    b = al._full_context("same message", name="ws_b")
    assert a == "CTX::ws_a" and b == "CTX::ws_b"
    assert calls == ["ws_a", "ws_b"]  # both built, no cross-workspace cache hit
```
- [ ] Step: Run pytest for the file — expect FAIL (`_resolve_workspace_name` missing; `_full_context`/`_identity_context` reject `name`).
- [ ] Step: Implement — add resolver after `_flag`/`_emit_agent_nerve`:
```python
def _resolve_workspace_name(user_id: str) -> str:
    """Map an authenticated caller's user_id to their workspace name. Empty user_id
    (owner) or unknown user -> 'default' (today's behavior, Bjørn's workspace)."""
    uid = str(user_id or "").strip()
    if not uid:
        return "default"
    try:
        from core.identity.users import find_user_by_discord_id
        user = find_user_by_discord_id(uid)
        if user and str(getattr(user, "workspace", "") or "").strip():
            return str(user.workspace).strip()
    except Exception:
        logger.debug("agent/step workspace-resolve fejlede", exc_info=True)
    return "default"
```
- [ ] Step: Implement — thread `name` through the prompt helpers. Change `_identity_context()` signature to `def _identity_context(name: str = "default") -> str:` and its call `ensure_default_workspace(name="default")` (line 68) to `ensure_default_workspace(name=name)`.
- [ ] Step: Implement — change `_full_context(user_message: str)` to `def _full_context(user_message: str, name: str = "default") -> str:`. Update the cache key (line 97) to include name: `key = hashlib.sha256((f"{name}\x00{user_message or ''}").encode("utf-8")).hexdigest()[:16]`. Change the assembly call (line 107) `name="default"` → `name=name`.
- [ ] Step: Implement — change `_build_system_prompt(context, user_message="")` to `def _build_system_prompt(context: str, user_message: str = "", name: str = "default") -> str:`; pass `name` into `_full_context(user_message, name)` (line 126) and `_identity_context(name)` (line 130).
- [ ] Step: Implement — in `agent_step`, resolve the name gated on the flag and pass it, right before building `chat_messages` (line 357-359):
```python
    _ws_name = _resolve_workspace_name(user_id) if _flag("jc_agent_user_scoping") else "default"
    chat_messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt(context, _last_user, _ws_name)}]
```
- [ ] Step: Implement — pass `user_id=user_id` into the `record_cost` call (added in Task 8's seam) and into `_emit_agent_nerve` (already wired in Task 5). Confirm `record_cost(..., user_id=user_id)`.
- [ ] Step: Run the pytest command — expect PASS.
- [ ] Step: Commit: `git commit -am "feat(agent-step): flag-gated per-caller workspace scoping (identity/memory) + cache-key isolation"`.

---

### Task 8: record_cost at the model-call seam + block-aware multimodal content [SERVER jarvis-v2]

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (`agent_step` seam after model call; `_last_user` extraction line 351-355; `_stream_step` done branch)
- Test: `tests/api/test_agent_step_envelope.py` (extend)

Two sub-parts: (a) call `record_cost(lane='agent', ..., user_id)` at the seam, flag-gated on `jc_agent_observability`; (b) block-aware `_extract_text` so an array of typed blocks (text/image) is handled for memory-recall extraction and passes through to the model — gated on `jc_agent_multimodal`. Array content already passes through `chat_messages.extend` to the provider payload; the test locks that in.

- [ ] Step: Write failing tests — append:
```python
def test_record_cost_called_at_seam_when_observability_on(monkeypatch):
    _patch_model(monkeypatch, cost=0.003, tin=9, tout=4)
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_observability")
    rec = {}
    monkeypatch.setattr(al, "record_cost", lambda **k: rec.update(k))
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}],
                      "stream": False, "user_id": "member_x"})
    assert rec["lane"] == "agent"
    assert rec["cost_usd"] == 0.003 and rec["input_tokens"] == 9
    assert rec["user_id"] == "member_x"


def test_record_cost_not_called_when_flag_off(monkeypatch):
    _patch_model(monkeypatch)
    calls = []
    monkeypatch.setattr(al, "record_cost", lambda **k: calls.append(k))
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert calls == []


def test_extract_text_from_blocks():
    # unit: block-aware extraction pulls text blocks, ignores image blocks
    blocks = [{"type": "text", "text": "beskriv dette"},
              {"type": "image", "image_url": {"url": "data:image/png;base64,AAA"}}]
    assert al._extract_text(blocks) == "beskriv dette"
    assert al._extract_text("plain") == "plain"


def test_multimodal_blocks_pass_through_to_model(monkeypatch):
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_multimodal")
    captured = {}
    def _fake_chat(**kw):
        captured["messages"] = kw["messages"]
        return {"text": "ok", "tool_calls": [], "input_tokens": 1,
                "output_tokens": 1, "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)
    blocks = [{"type": "text", "text": "hvad ser du"},
              {"type": "image", "image_url": {"url": "data:image/png;base64,AAA"}}]
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": blocks}], "stream": False})
    user_msg = [m for m in captured["messages"] if m.get("role") == "user"][-1]
    # array content reached the model payload UNCHANGED (image block intact)
    assert isinstance(user_msg["content"], list)
    assert any(b.get("type") == "image" for b in user_msg["content"])
```
- [ ] Step: Run pytest for the file — expect FAIL (`_extract_text` missing; record_cost not called; today's `str(content)` mangles the block list into the user message extraction — the model-passthrough test still passes since extend is verbatim, but `_extract_text` and record_cost assertions fail).
- [ ] Step: Implement — add block-aware extractor after `_flag`:
```python
def _extract_text(content: Any) -> str:
    """Extract plain text from a message `content` that may be a str OR an array of
    typed blocks ({type:'text'|'image', ...}). Multimodal foundation: image blocks pass
    through to the model untouched (chat_messages.extend), but memory-recall only needs
    the text. For a plain str this is identical to today's behavior (inert)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return " ".join(p for p in parts if p)
    return str(content or "")
```
- [ ] Step: Implement — change the `_last_user` extraction (line 354) from `_last_user = str(_m.get("content") or "")` to be block-aware, gated so plain-str behavior is byte-identical when the flag is OFF:
```python
    for _m in reversed(client_messages):
        if isinstance(_m, dict) and _m.get("role") == "user":
            _c = _m.get("content")
            _last_user = _extract_text(_c) if _flag("jc_agent_multimodal") else str(_c or "")
            break
```
(Array content still flows to the model via `chat_messages.extend(client_messages)` on line 360 regardless of the flag — that is transport-level and already verbatim; the flag only governs the recall-text extraction.)
- [ ] Step: Implement — add the flag-gated `record_cost` at the seam in `agent_step`, inside the existing `if _flag("jc_agent_observability"):` block from Task 5 (before `_emit_agent_nerve`):
```python
    if _flag("jc_agent_observability"):
        try:
            record_cost(lane="agent", provider=provider, model=model,
                        input_tokens=tokens_in, output_tokens=tokens_out,
                        cost_usd=cost_usd, user_id=user_id)
        except Exception:
            logger.debug("agent/step record_cost fejlede", exc_info=True)
        _emit_agent_nerve(...)   # (unchanged from Task 5)
        ...
```
- [ ] Step: Implement — mirror the seam `record_cost` in `_stream_step`'s done branch (inside its `if _flag("jc_agent_observability"):` block), using `_tin/_tout/_cost` and the `user_id` param.
- [ ] Step: Run the pytest command — expect PASS.
- [ ] Step: Run the FULL suites: `/opt/conda/envs/ai/bin/python -m pytest tests/api/test_agent_step_envelope.py tests/api/test_tools_execute_endpoint.py tests/costing/test_record_cost_user_id.py -o addopts="" -q` — expect ALL PASS (existing 11 tools/execute tests unregressed).
- [ ] Step: Run `python -m compileall core apps/api scripts` (CI smoke) — expect clean.
- [ ] Step: Commit: `git commit -am "feat(agent-step): flag-gated record_cost(lane=agent,user_id) at seam + block-aware multimodal content extraction"`.

---

## Acceptance

Phase 0 is done when, on the live jarvis-v2 API with all three flags (`jc_agent_observability`, `jc_agent_user_scoping`, `jc_agent_multimodal`) **default OFF**:

1. **Inert-by-default proven:** with flags OFF, `/v1/agent/step` behaves exactly as before except for additive JSON keys (`status`, `tokens_in`, `tokens_out`, `cost_usd`, `duration_ms`, `finish_reason`, `result`) on the non-stream response and the stream `done` event — no `record_cost` row, no nerve, no incident, no workspace change. Tests `test_observability_off_by_default`, `test_record_cost_not_called_when_flag_off`, `test_scoping_off_uses_default_workspace` green.
2. **Blind lane closed (flag ON):** `test_observability_on_emits_nerve_and_empty`, `test_record_cost_called_at_seam_when_observability_on` show an `agent`/`agent_step` nerve with `status/tokens/duration/user_id`, a `record_cost(lane='agent', user_id=...)` row, and `note_empty_completion(path='agent_step')` on empty completions.
3. **finish_reason foundation:** real `finish_reason` (e.g. `"length"`) flows adapter → iterator → route → `done` SSE (`test_adapter_returns_finish_reason`, `test_stream_done_has_cost_and_envelope`) — the hook the Fase-1 client (A6) reads.
4. **Multi-user blocker lifted (flag ON):** identity/memory resolve to the caller's workspace, with `_FULL_CTX_CACHE` keyed by workspace so no cross-user context bleed (`test_scoping_on_resolves_caller_workspace`, `test_full_context_cache_key_includes_workspace`).
5. **Multimodal foundation:** an array of typed blocks reaches the model payload unchanged and text is extracted for recall (`test_multimodal_blocks_pass_through_to_model`, `test_extract_text_from_blocks`).
6. **No regression:** all 11 existing `tests/api/test_tools_execute_endpoint.py` tests still pass; `python -m compileall core apps/api scripts` is clean.

Deploy: merge, deploy with all flags OFF (inert), then flip flags one at a time on the live API per Bjørn's decision #1 (no separate staging).