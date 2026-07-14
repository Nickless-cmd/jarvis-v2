# jc_agent_loop Turn-Loop Extraction Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Extract repl_ptk.py's UI-coupled turn-loop into a UI-free `src/jc_agent_loop.py` module (the shared-substrate seed) with behavior preserved exactly, locked by characterization tests written first.

**Architecture:** The turn-loop today lives as three `PtkApp` methods that mix pure orchestration (round iteration, model steps, tool execution, message assembly) with prompt_toolkit-driven side-effects (live-region deltas, foldable round widget, scrollback emit). We keep the side-effects in `PtkApp` but move the orchestration into module-level functions in `jc_agent_loop.py` that operate on a structural `host` object (PtkApp satisfies it). `PtkApp._turn_worker/_run_one_step/_run_one_tool` become one-line delegators. `jc_agent_loop.py` imports only UI-free siblings (`api`, `render`, `session`, `tools`) — never `prompt_toolkit`, never `core.*`.

**Tech Stack:** Python 3.11 (ai conda-env), pytest. Client repo `/home/bs/jarvis-code` (CANNOT import `core.*` — all logic reimplemented client-side; this phase moves existing client code only). Tests run: `/opt/conda/envs/ai/bin/python -m pytest <path> -q -o addopts=""`.

## File Structure

- **`/home/bs/jarvis-code/src/repl_ptk.py`** (MODIFY) — App-shell + PtkApp UI class. After this phase it owns rendering/state/side-effect sinks and delegates turn orchestration to `jc_agent_loop`. Adds `_make_tool_display()` seam; re-exports `_is_write_tool` for back-compat.
- **`/home/bs/jarvis-code/src/jc_agent_loop.py`** (CREATE) — UI-free turn-loop substrate. One responsibility: drive a user turn against the server (`run_turn_worker`), run one model step (`run_one_step`), run one tool call (`run_one_tool`), operating purely through a `host` protocol. No prompt_toolkit import. This is where Fase 1 Tier 0 contracts land.
- **`/home/bs/jarvis-code/tests/test_turnloop_characterization.py`** (CREATE) — Safety-net characterization tests exercising `PtkApp._run_one_step/_run_one_tool/_turn_worker`. Must stay green before AND after extraction (proves behavior preserved).
- **`/home/bs/jarvis-code/tests/test_jc_agent_loop.py`** (CREATE) — Unit tests for the new module surface using a minimal recording `FakeHost` (proves the loop is genuinely UI-free and host-driven).

---

### Task 1: [CLIENT jarvis-code] Prep stable dependency seams + `_make_tool_display`

Behavior-preserving prep so tests can patch module-qualified seams (`src.api.*`, `src.session.*`, `src.tools.*`) that survive the later cut-and-move. Without this, the loop calls bound names (`agent_step_stream`, `save_message`, `execute_tool`, `TOOL_EXECUTORS`) that would need different patch targets before vs. after extraction.

**Files:**
- Modify `/home/bs/jarvis-code/src/repl_ptk.py`:
  - Imports (after line 29-33): add `from . import api as api_mod` and `from . import session as session_mod`.
  - `_run_one_step` (lines 989, 1023): `agent_step_stream(...)` → `api_mod.agent_step_stream(...)`; `agent_step(...)` → `api_mod.agent_step(...)`.
  - `_run_one_tool` (line 1201-1204): `name in TOOL_EXECUTORS` → `name in tools_mod.TOOL_EXECUTORS`; `execute_tool(...)` → `tools_mod.execute_tool(...)`.
  - `_turn_worker` (line 862): `save_message(...)` → `session_mod.save_message(...)`; (line 820) `display = _PtkToolDisplay(self)` → `display = self._make_tool_display()`.
  - Add method `_make_tool_display` on `PtkApp` (place next to `_run_turn`, ~line 795).
- Test: `/home/bs/jarvis-code/tests/test_turnloop_characterization.py` (created here, one test proving the seam; grown in Task 2).

Note: `src.api`, `src.session`, `src.tools`, `src.render` were verified to contain NO `prompt_toolkit` import (only docstring mentions) — safe UF-free seams.

- [ ] Step: Write failing test for the new `_make_tool_display` seam. Create `/home/bs/jarvis-code/tests/test_turnloop_characterization.py`:
```python
import json
from src.repl_ptk import PtkApp, _PtkToolDisplay


def _mk_app(**over):
    cfg = {"api_url": "http://x", "auth_token": "t", "max_tool_rounds": 60}
    cfg.update(over.pop("config", {}))
    app = PtkApp(config=cfg, session_id="s", model="m", mode="code",
                 messages=[], cwd="/tmp", **over)
    return app


def test_make_tool_display_returns_adapter_bound_to_app():
    app = _mk_app()
    disp = app._make_tool_display()
    assert isinstance(disp, _PtkToolDisplay)
    # adapter must expose the surface execute_tool relies on
    assert hasattr(disp, "console") and hasattr(disp, "prompt_approval")
```
- [ ] Step: Run — expect FAIL (`AttributeError: 'PtkApp' object has no attribute '_make_tool_display'`).
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_turnloop_characterization.py -q -o addopts=""
```
- [ ] Step: Implement. In `/home/bs/jarvis-code/src/repl_ptk.py` add the two module imports and the seam method:
```python
# with the other imports near the top
from . import api as api_mod
from . import session as session_mod
```
```python
    def _make_tool_display(self) -> "_PtkToolDisplay":
        """Byg display-adapteren til LOKAL tool-eksekvering. Seam så den UI-frie
        turn-loop (jc_agent_loop) kan hente adapteren uden at kende _PtkToolDisplay."""
        return _PtkToolDisplay(self)
```
- [ ] Step: Apply the module-qualified seam edits inside `_run_one_step`, `_run_one_tool`, `_turn_worker` exactly as listed under Files (agent_step_stream/agent_step → `api_mod.`; execute_tool/TOOL_EXECUTORS → `tools_mod.`; save_message → `session_mod.`; `_PtkToolDisplay(self)` → `self._make_tool_display()`).
- [ ] Step: Run the new test + full suite — expect PASS (behavior-preserving prep; existing 14 driver tests + rest stay green).
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_turnloop_characterization.py tests/test_repl_ptk_driver.py -q -o addopts=""
/opt/conda/envs/ai/bin/python -m pytest tests/ -q -o addopts=""
```
- [ ] Step: Commit.
```bash
cd /home/bs/jarvis-code && git add -A && git commit -m "refactor(jc-ptk): stable dep-seams (api_mod/session_mod/tools_mod) + _make_tool_display

Prep for jc_agent_loop-ekstraktion: kald netværks/tool/session-afhængigheder
via modul-kvalificerede navne så patch-targets overlever cut-and-move.
Adfærds-bevarende — ingen logik ændret.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: [CLIENT jarvis-code] Characterization tests (safety net) locking current behavior

Write tests against the CURRENT `PtkApp` methods that assert exact behavior of all three turn-loop functions. These are green now (they document reality) and MUST stay green after extraction — that is the proof behavior is preserved. They exercise `PtkApp` (transitively the module after Task 3), so they double as the module's integration test.

**Files:**
- Modify `/home/bs/jarvis-code/tests/test_turnloop_characterization.py` (append the cases below).
- No source change in this task.

- [ ] Step: Append `_run_one_step` characterization cases (streaming happy path; non-stream fallback on stream error). Patch the `src.api.*` seams from Task 1:
```python
def test_run_one_step_streams_content_tools_and_usage(monkeypatch):
    app = _mk_app()
    events = [
        {"type": "delta", "text": "Hej "},
        {"type": "delta", "text": "Bjørn"},
        {"type": "tool_calls",
         "tool_calls": [{"id": "1", "function": {"name": "bash", "arguments": "{}"}}]},
        {"type": "done", "content": "Hej Bjørn",
         "usage": {"prompt_tokens": 5, "completion_tokens": 2}},
    ]
    monkeypatch.setattr("src.api.agent_step_stream", lambda **kw: iter(events))
    content, tool_calls = app._run_one_step("http://x", "t",
                                            [{"role": "user", "content": "hej"}])
    assert content == "Hej Bjørn"
    assert tool_calls[0]["function"]["name"] == "bash"
    assert app.turn_cost["completion_tokens"] == 2
    assert app._stream_text == "Hej Bjørn"


def test_run_one_step_falls_back_to_nonstream_on_error(monkeypatch):
    app = _mk_app()
    monkeypatch.setattr("src.api.agent_step_stream",
                        lambda **kw: iter([{"type": "error", "error": "boom"}]))
    monkeypatch.setattr("src.api.agent_step",
                        lambda **kw: {"content": "recovered", "tool_calls": [],
                                      "usage": {"completion_tokens": 3}})
    content, tool_calls = app._run_one_step("http://x", "t",
                                            [{"role": "user", "content": "x"}])
    assert content == "recovered" and tool_calls == []
    assert app._stream_text == "recovered"
    assert app.turn_cost["completion_tokens"] == 3
```
- [ ] Step: Append `_run_one_tool` characterization cases (local bash → tool-result append; plan-mode blocks writes; forwarded non-local routes via `route_tool_call`):
```python
def test_run_one_tool_local_bash_appends_typed_tool_result(monkeypatch):
    app = _mk_app()
    monkeypatch.setattr(
        "src.tools.execute_tool",
        lambda name, args, display, **kw: {"status": "ok", "stdout": "hi\n", "exit_code": 0})
    tc = {"id": "42", "function": {"name": "bash", "arguments": '{"command": "echo hi"}'}}
    api_messages = []
    app._run_one_tool(tc, app._make_tool_display(), api_messages, "turn1")
    assert len(api_messages) == 1
    msg = api_messages[0]
    assert msg["role"] == "tool" and msg["tool_call_id"] == "42" and msg["name"] == "bash"
    assert json.loads(msg["content"])["status"] == "ok"


def test_run_one_tool_plan_mode_blocks_write_without_executing(monkeypatch):
    app = _mk_app()
    app.plan_mode = "readonly"
    called = {"exec": False}
    monkeypatch.setattr("src.tools.execute_tool",
                        lambda *a, **k: called.__setitem__("exec", True) or {})
    tc = {"id": "9", "function": {"name": "write_file",
                                  "arguments": '{"path": "/x", "content": "y"}'}}
    api_messages = []
    app._run_one_tool(tc, app._make_tool_display(), api_messages, "t")
    assert called["exec"] is False
    assert json.loads(api_messages[0]["content"])["status"] == "blocked"


def test_run_one_tool_forwards_non_local_tool(monkeypatch):
    app = _mk_app()
    seen = {}
    def _route(name, args, **kw):
        seen["name"] = name
        return {"status": "ok", "result": "forwarded"}
    monkeypatch.setattr("src.tools.route_tool_call", _route)
    tc = {"id": "7", "function": {"name": "operator_click", "arguments": "{}"}}
    api_messages = []
    app._run_one_tool(tc, app._make_tool_display(), api_messages, "t")
    assert seen["name"] == "operator_click"
    assert json.loads(api_messages[0]["content"])["status"] == "ok"
```
- [ ] Step: Append `_turn_worker` characterization cases (no-tool break + persistence; round-cap notice). Patch `src.session.save_message` and stub the sub-methods via the host:
```python
def test_turn_worker_saves_final_and_records_messages(monkeypatch):
    app = _mk_app()
    saved = []
    monkeypatch.setattr("src.session.save_message",
                        lambda sid, role, content: saved.append((role, content)))
    monkeypatch.setattr(app, "_run_one_step",
                        lambda api_url, auth, msgs: ("Færdigt svar", []))
    app.busy = True
    app._turn_worker("gør noget")
    assert ("assistant", "Færdigt svar") in saved
    assert app.messages[-2] == {"role": "user", "content": "gør noget"}
    assert app.messages[-1] == {"role": "assistant", "content": "Færdigt svar"}
    assert app.busy is False


def test_turn_worker_hits_round_cap_and_emits_notice(monkeypatch):
    app = _mk_app(config={"max_tool_rounds": 2})
    monkeypatch.setattr("src.session.save_message", lambda *a: None)
    emits = []
    monkeypatch.setattr(app, "_emit", lambda t, **k: emits.append(t))
    monkeypatch.setattr(
        app, "_run_one_step",
        lambda *a: ("", [{"id": "1", "function": {"name": "bash", "arguments": "{}"}}]))
    monkeypatch.setattr(app, "_run_one_tool", lambda *a: None)
    app.busy = True
    app._turn_worker("loop")
    assert any("loftet" in e for e in emits)
    assert app.busy is False
```
- [ ] Step: Run — expect ALL PASS against current (Task-1) code. This is the locked safety net.
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_turnloop_characterization.py -q -o addopts=""
```
- [ ] Step: Commit.
```bash
cd /home/bs/jarvis-code && git add -A && git commit -m "test(jc-ptk): karakteriserings-tests låser turn-loop-adfærd før ekstraktion

step (stream+fallback), tool (lokal/plan-block/forward), worker (persist+cap).
Sikkerhedsnet: skal forblive grønt efter jc_agent_loop-udskillelsen.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: [CLIENT jarvis-code] Create `jc_agent_loop.py` and delegate from PtkApp

Cut the three method bodies out of `repl_ptk.py` into UI-free module functions on a `host` protocol; make `PtkApp` methods one-line delegators. Prove the module is host-driven and UI-free via a recording `FakeHost` (RED → GREEN), and prove behavior preserved via the Task-2 safety net (stays GREEN).

**Files:**
- Create `/home/bs/jarvis-code/src/jc_agent_loop.py` (new module; bodies moved from repl_ptk lines 811-870, 979-1036, 1176-1238; plus `_is_write_tool` moved from repl_ptk lines 117-131).
- Modify `/home/bs/jarvis-code/src/repl_ptk.py`: replace the three method bodies with delegators; add `from . import jc_agent_loop`; re-export `_is_write_tool` via `from .jc_agent_loop import _is_write_tool` (back-compat — it is module-level and referenced by the loop; keep the name importable from repl_ptk).
- Create `/home/bs/jarvis-code/tests/test_jc_agent_loop.py` (FakeHost unit tests).

No circular import: `jc_agent_loop` imports only `api`, `render`, `session`, `tools` — none import `repl_ptk`; `repl_ptk` imports `jc_agent_loop` at top. `_is_write_tool` moves into `jc_agent_loop` (it needs `tools.is_readonly_command`, already lazy).

- [ ] Step: Write the failing module test. Create `/home/bs/jarvis-code/tests/test_jc_agent_loop.py`:
```python
import json


class FakeHost:
    """Minimal UI-free host that records every sink call — proves jc_agent_loop
    drives behavior purely through the host protocol (no prompt_toolkit)."""
    def __init__(self):
        self.stop_requested = False
        self._stream_text = ""
        self.turn_cost = {}
        self.context = "identity"
        self.timeout = 30
        self.plan_mode = "off"
        self.max_rounds = 60
        self.approval_mode = "auto-edit"
        self._always_approved = set()
        self.cwd = "/tmp"
        self.session_id = "s"
        self.api_url = "http://x"
        self.auth_token = "t"
        self.unlocked = False
        self.undo_stack = []
        self.messages = []
        self.busy = True
        self.deltas = []
        self.emits = []
        self.round_calls = []
        self.frozen = 0
        self.committed = 0
        self._tools = [{"type": "function", "function": {"name": "bash"}}]
    def _tools_for_step(self): return self._tools
    def _stream_delta(self, t): self._stream_text += t; self.deltas.append(t)
    def _invalidate(self): pass
    def _emit(self, t, **k): self.emits.append(t)
    def _set_status(self, s): pass
    def _round_add(self, name, args): self.round_calls.append(("add", name)); return 0
    def _round_update(self, idx, **kw): self.round_calls.append(("update", idx, kw))
    def _round_freeze(self): self.frozen += 1
    def _commit_stream(self): self.committed += 1
    def _refresh_tools(self): pass
    def _maybe_autotest(self): pass
    def _make_tool_display(self): return object()
    def _run_one_step(self, api_url, auth, msgs):
        import src.jc_agent_loop as L
        return L.run_one_step(self, api_url, auth, msgs)
    def _run_one_tool(self, tc, display, msgs, turn_id):
        import src.jc_agent_loop as L
        return L.run_one_tool(self, tc, display, msgs, turn_id)


def test_module_is_ui_free():
    import src.jc_agent_loop as L
    import inspect
    src = inspect.getsource(L)
    assert "prompt_toolkit" not in src
    assert "import core" not in src and "from core" not in src


def test_run_one_step_drives_host_sink(monkeypatch):
    import src.jc_agent_loop as L
    host = FakeHost()
    monkeypatch.setattr("src.api.agent_step_stream",
                        lambda **kw: iter([{"type": "delta", "text": "hi"},
                                           {"type": "done", "content": "hi", "usage": {}}]))
    content, tcs = L.run_one_step(host, "http://x", "t", [])
    assert content == "hi" and tcs == []
    assert host.deltas == ["hi"] and host._stream_text == "hi"


def test_run_one_tool_appends_result_via_host(monkeypatch):
    import src.jc_agent_loop as L
    host = FakeHost()
    monkeypatch.setattr("src.tools.execute_tool",
                        lambda name, args, display, **kw: {"status": "ok", "stdout": "x"})
    msgs = []
    tc = {"id": "1", "function": {"name": "bash", "arguments": "{}"}}
    L.run_one_tool(host, tc, host._make_tool_display(), msgs, "t")
    assert json.loads(msgs[0]["content"])["status"] == "ok"
    assert ("add", "bash") in host.round_calls


def test_run_turn_worker_full_loop_via_host(monkeypatch):
    import src.jc_agent_loop as L
    host = FakeHost()
    monkeypatch.setattr("src.session.save_message", lambda *a: None)
    monkeypatch.setattr(host, "_run_one_step",
                        lambda api_url, auth, msgs: ("svar", []))
    L.run_turn_worker(host, "hej")
    assert host.messages[-1] == {"role": "assistant", "content": "svar"}
    assert host.busy is False
```
- [ ] Step: Run — expect FAIL (`ModuleNotFoundError: No module named 'src.jc_agent_loop'`).
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_agent_loop.py -q -o addopts=""
```
- [ ] Step: Create `/home/bs/jarvis-code/src/jc_agent_loop.py` by moving the bodies (self→host, module-qualified deps):
```python
# src/jc_agent_loop.py
"""UI-fri turn-loop substrat for jarvis-code (Claude Code-model klient-loop).

Udskilt fra repl_ptk.py (Fase 0.5): den rene tur-orkestrering — round-iteration,
model-step, tool-eksekvering, besked-assembly — uden nogen prompt_toolkit-afhængighed.
Alle side-effekter (live-region, foldbar runde-blok, scrollback-emit) sker gennem
`host`-protokollen (PtkApp opfylder den strukturelt). Dette modul er hvor Fase 1's
Tier 0-kontrakter bygges, og hvad desk (code mode) senere konsumerer.

MÅ ALDRIG importere prompt_toolkit eller core.* (klient-repo kan ikke importere core)."""
from __future__ import annotations

import json
import uuid
from typing import Any

from . import api as api_mod
from . import render
from . import session as session_mod
from . import tools as tools_mod


def _is_write_tool(name: str, args: Any) -> bool:
    """Skrivende/farlig? (til plan-mode-blokering). Læse/undersøgelse er tilladt."""
    base = name[len("runtime_"):] if name.startswith("runtime_") else name
    if base in ("write_file", "edit_file"):
        return True
    if name.startswith("operator_") and any(
            k in name for k in ("write", "edit", "kill", "launch", "type", "click")):
        return True
    if base == "bash":
        try:
            from .tools import is_readonly_command
            return not is_readonly_command(str((args or {}).get("command", "")))
        except Exception:
            return True
    return False


def run_one_step(host: Any, api_url: str, auth: str | None,
                 api_messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Kør ÉT model-step STREAMENDE; ved stream-fejl fald tilbage til non-stream
    agent_step for netop dette step. Returnerer (content, tool_calls)."""
    content = ""
    tool_calls: list[dict[str, Any]] = []
    err = None
    host._stream_text = ""
    streamed = False
    try:
        for ev in api_mod.agent_step_stream(api_url=api_url, auth_token=auth,
                                            messages=api_messages, tools=host._tools_for_step(),
                                            context=host.context, timeout=host.timeout):
            if host.stop_requested:
                break
            t = ev.get("type")
            if t == "delta":
                txt = str(ev.get("text") or "")
                if txt:
                    streamed = True
                    host._stream_delta(txt)
            elif t == "tool_calls":
                tool_calls = ev.get("tool_calls") or []
            elif t == "usage":
                host.turn_cost = ev.get("usage") or {k: v for k, v in ev.items() if k != "type"}
                host._invalidate()
            elif t == "done":
                content = str(ev.get("content") or host._stream_text)
                if ev.get("usage"):
                    host.turn_cost = ev["usage"]
                    host._invalidate()
                break
            elif t == "error":
                err = ev.get("error")
                break
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    if not streamed and content:
        host._stream_text = content
    if err is not None:
        resp = api_mod.agent_step(api_url=api_url, auth_token=auth,
                                  messages=api_messages, tools=host._tools_for_step(),
                                  context=host.context, timeout=host.timeout)
        if resp.get("error"):
            host._stream_text = ""
            host._emit(render.sb_error(f"✗ {resp['error']}"))
            return "", []
        content = str(resp.get("content") or "")
        tool_calls = resp.get("tool_calls") or []
        if resp.get("usage"):
            host.turn_cost = resp["usage"]
            host._invalidate()
        host._stream_text = content
    return content, tool_calls


def run_one_tool(host: Any, tc: dict[str, Any], display: Any,
                 api_messages: list[dict[str, Any]], turn_id: str) -> None:
    """Kør ÉT tool_call LOKALT (eller forward'et) og læg det i den LEVENDE runde."""
    fn = tc.get("function") or {}
    name = fn.get("name") or "tool"
    raw_args = fn.get("arguments")
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
    except Exception:
        args = {}
    idx = host._round_add(name, args)
    if host.plan_mode == "readonly" and _is_write_tool(name, args):
        result: dict[str, Any] = {"status": "blocked", "error":
            "plan-mode aktiv: skrivning kræver godkendelse. Foreslå planen; /plan off for at udføre."}
        host._round_update(idx, status="error",
                           output="plan-mode: skrivning blokeret — /plan off for at udføre")
        api_messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                             "name": name, "content": json.dumps(result, ensure_ascii=False)})
        return
    if name == "load_more_tools":
        host.unlocked = True
        host._refresh_tools()
        result = {"status": "unlocked", "count": len(host._tools_for_step())}
    elif name in tools_mod.TOOL_EXECUTORS:
        result = tools_mod.execute_tool(name, args, display, approval_mode=host.approval_mode,
                                        always_approved=host._always_approved, cwd=host.cwd,
                                        sandbox=False, extra_roots=[])
    else:
        result = tools_mod.route_tool_call(
            name, args, api_url=host.api_url, auth_token=host.auth_token,
            session_id=host.session_id, turn_id=turn_id)
        if not isinstance(result, dict):
            result = {"status": "ok", "result": result}
    if isinstance(result, dict) and result.get("_undo_path") is not None:
        host.undo_stack.append((
            result.get("_undo_path"), result.get("_undo_prev") or "",
            bool(result.get("_undo_was_new"))))
    output = ""
    if isinstance(result, dict) and name in ("bash", "runtime_bash"):
        output = str(result.get("stdout") or result.get("output")
                     or result.get("result") or result.get("stderr") or "")
    diff = result.pop("diff", None) if isinstance(result, dict) else None
    add = dele = None
    if diff:
        add, dele = render.diff_counts(diff)
    if isinstance(result, dict):
        for k in ("_undo_prev", "_undo_path", "_undo_was_new"):
            result.pop(k, None)
    status = str((result or {}).get("status", "ok"))
    ok = status in ("ok", "unlocked")
    host._round_update(idx, status=("done" if ok else "error"),
                       diff=diff, output=output if not diff else "",
                       add=add, dele=dele)
    api_messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                         "name": name, "content": json.dumps(result, ensure_ascii=False)})
    base = name[len("runtime_"):] if name.startswith("runtime_") else name
    if base in ("write_file", "edit_file") and status == "ok":
        host._maybe_autotest()


def run_turn_worker(host: Any, user_input: str) -> None:
    """Client-owned tur: stream assistent-tekst, kør tool_calls LOKALT (eller forward'et),
    render kompakte tool-linjer + inline diff, fang cost. Alle side-effekter via host."""
    auth = host.auth_token
    api_url = host.api_url
    turn_id = uuid.uuid4().hex
    display = host._make_tool_display()
    convo = [m for m in host.messages if m.get("role") in ("user", "assistant")]
    model_input = user_input
    if host.plan_mode == "readonly":
        model_input = ("[PLAN-MODE] Foreslå FØRST en kort nummereret plan for hvordan du vil "
                       "løse dette, og VENT på godkendelse. Kald IKKE skrivende værktøjer endnu.\n\n"
                       + user_input)
    convo.append({"role": "user", "content": model_input})
    api_messages = list(convo)
    final_text = ""
    try:
        for _round in range(host.max_rounds):
            if host.stop_requested:
                break
            content, tool_calls = host._run_one_step(api_url, auth, api_messages)
            if content:
                final_text = content
            if not tool_calls:
                break
            host._round_freeze()
            host._commit_stream()
            api_messages.append({"role": "assistant", "content": content,
                                 "tool_calls": tool_calls})
            for tc in tool_calls:
                if host.stop_requested:
                    break
                host._run_one_tool(tc, display, api_messages, turn_id)
        else:
            host._round_freeze()
            host._commit_stream()
            host._emit(render.sb_sys(f"(nåede loftet på {host.max_rounds} tool-runder "
                                     "— skriv 'fortsæt' for at køre videre · hæv med "
                                     "config max_tool_rounds)"))
        if final_text.strip():
            session_mod.save_message(host.session_id, "assistant", final_text)
            host.messages.append({"role": "user", "content": user_input})
            host.messages.append({"role": "assistant", "content": final_text})
    except Exception as exc:  # noqa: BLE001
        host._emit(render.sb_error(f"✗ Uventet fejl: {exc}"))
    finally:
        host.busy = False
        host._set_status("")
        host._invalidate()
```
- [ ] Step: Run module tests — expect PASS.
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_agent_loop.py -q -o addopts=""
```
- [ ] Step: Rewire `PtkApp` to delegate. In `/home/bs/jarvis-code/src/repl_ptk.py`: add `from . import jc_agent_loop` (top imports); replace the OLD module-level `_is_write_tool` (lines ~117-131) with a re-export `from .jc_agent_loop import _is_write_tool`; replace the three method BODIES with delegators (keep signatures/docstrings-as-one-liners):
```python
    def _run_one_step(self, api_url: str, auth: str | None,
                      api_messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """Delegér til det UI-frie substrat (jc_agent_loop.run_one_step)."""
        return jc_agent_loop.run_one_step(self, api_url, auth, api_messages)

    def _run_one_tool(self, tc: dict[str, Any], display: "_PtkToolDisplay",
                      api_messages: list[dict[str, Any]], turn_id: str) -> None:
        """Delegér til det UI-frie substrat (jc_agent_loop.run_one_tool)."""
        return jc_agent_loop.run_one_tool(self, tc, display, api_messages, turn_id)

    def _turn_worker(self, user_input: str) -> None:
        """Delegér til det UI-frie substrat (jc_agent_loop.run_turn_worker)."""
        return jc_agent_loop.run_turn_worker(self, user_input)
```
Delete the now-dead inline bodies of `_run_one_step` (old lines 979-1036), `_run_one_tool` (1176-1238), `_turn_worker` (811-870), and the old `_is_write_tool` (117-131). Keep `_PtkToolDisplay`, `_make_tool_display`, and all render/round/emit sink methods in `PtkApp` unchanged.
- [ ] Step: Run BOTH suites — module tests + characterization safety net — expect ALL PASS (behavior preserved).
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_agent_loop.py tests/test_turnloop_characterization.py -q -o addopts=""
```
- [ ] Step: Commit.
```bash
cd /home/bs/jarvis-code && git add -A && git commit -m "refactor(jc): udskil turn-loop → jc_agent_loop (UI-frit substrat-frø)

Flyt _turn_worker/_run_one_step/_run_one_tool + _is_write_tool ud af repl_ptk
til src/jc_agent_loop.py der drives via en host-protokol (PtkApp opfylder den).
Ingen prompt_toolkit/core-import. PtkApp delegerer nu. Adfærd bevaret (Fase 0.5).
Her bygges Fase 1's Tier 0-kontrakter; desk konsumerer samme kerne.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: [CLIENT jarvis-code] Full-suite verification + UI-free guard

Confirm no regression anywhere and that the module cannot silently regain a UI/core dependency.

**Files:**
- No new source. Optional guard test already present (`test_module_is_ui_free` in `tests/test_jc_agent_loop.py`, Task 3) — verify it is enforced by the full run.

- [ ] Step: Run the ENTIRE jarvis-code test suite — expect all green (the 14 pre-existing driver tests + new files + everything else).
```bash
/opt/conda/envs/ai/bin/python -m pytest tests/ -q -o addopts=""
```
- [ ] Step: Grep-assert the module stays UI-free / core-free (belt-and-suspenders beyond the unit guard):
```bash
cd /home/bs/jarvis-code && ! grep -nE "prompt_toolkit|^import core|from core" src/jc_agent_loop.py && echo "GUARD OK: jc_agent_loop is UI-free and core-free"
```
- [ ] Step: Smoke-import both modules to confirm no circular import at load time:
```bash
cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -c "import src.repl_ptk, src.jc_agent_loop; print('import OK')"
```
- [ ] Step: If any check fails, use superpowers:systematic-debugging before patching. If all green, no commit needed (verification only) — the extraction is complete.

## Acceptance

- `src/jc_agent_loop.py` exists, exports `run_turn_worker`, `run_one_step`, `run_one_tool`, `_is_write_tool`; imports NO `prompt_toolkit` and NO `core.*` (enforced by `test_module_is_ui_free` + grep guard).
- `PtkApp._turn_worker/_run_one_step/_run_one_tool` are one-line delegators; `_make_tool_display` seam added; `_is_write_tool` re-exported from `repl_ptk` for back-compat.
- Characterization tests (`test_turnloop_characterization.py`) are green BEFORE (Task 2, current code) and AFTER (Task 3, delegated code) — proving behavior preserved exactly.
- Module unit tests (`test_jc_agent_loop.py`) pass with a UI-free `FakeHost`, proving the loop is genuinely host-driven.
- Full suite green; `import src.repl_ptk, src.jc_agent_loop` succeeds (no circular import).
- This module is the substrate seed: Fase 1 Tier 0 contracts (A1-A8) land here; desk later consumes the same `host`-protocol kernel. No server change, no flag gate — pure [CLIENT jarvis-code] refactor.