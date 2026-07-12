# jarvis-code prompt_toolkit Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild jarvis-code's render layer from Textual (full-screen) to prompt_toolkit (print-to-scrollback + live bottom region) for the native Claude Code feel, reusing all existing logic.

**Architecture:** A non-full-screen prompt_toolkit `Application` owns a live bottom region (bordered composer `Frame` + footer toolbar + a live status line). Completed messages are emitted ABOVE the live region via `run_in_terminal()` so they join the terminal's native scrollback (copy/scroll/transparency work for free). All turn logic (agent-step, 3-way tool router, diff/undo/cost/plan, catalog, full-context) is reused from `src/api.py` + `src/tools.py`; only rendering is new. Textual (`src/tui.py`) stays as `--legacy`.

**Tech Stack:** Python 3.11, prompt_toolkit 3.0.52 (in `ai` env), existing httpx-based `src/api.py`/`src/tools.py`, pytest.

**Repo:** `/home/bs/jarvis-code` (local, master branch, no remote). Tests: `/opt/conda/envs/ai/bin/python -m pytest <path> -o addopts="" -q`.

**Ground truth (reuse unchanged):**
- `src/api.py`: `agent_step`, `agent_step_stream` (yields `{type: delta|tool_calls|done|error|usage, ...}`), `fetch_catalog`, `execute_native_tool`, `native_tools`, `stream_chat_v2`.
- `src/tools.py`: `LOCAL_TOOLS`, `TOOL_EXECUTORS`, `execute_tool(name,args,display,approval_mode,always_approved,cwd,sandbox,extra_roots)`, `route_tool_call(name,args,*,api_url,auth_token,session_id,turn_id)`, `is_readonly_command`. `local_write_file`/`local_edit_file` return `{status, diff, _undo_path, _undo_prev, _undo_was_new}`.
- `src/session.py`: `save_message(session_id, role, content)`.
- `src/config.py`: `get_auth_token(config)`, `save_config(config, global_scope=True)`, `GLOBAL_CONFIG_FILE`, `VERSION`.
- Reference loop (do NOT edit — mirror its logic): `src/tui.py::_run_turn_client`.

---

## File Structure
- Create `src/render.py` — pure render functions returning prompt_toolkit `FormattedText` / ANSI strings (banner, tool-line, diff, cost/footer, user/assistant). No app state → unit-testable.
- Create `src/repl_ptk.py` — the prompt_toolkit `Application`: banner print, composer Frame, footer, status, input loop, slash dispatch, the client-owned turn driver (reuses api/tools), inline approval, file-picker.
- Modify `src/main.py` — default → `repl_ptk`; `--legacy` → Textual `run_tui`; `--simple` → existing linear repl.
- Leave `src/tui.py` untouched (Textual `--legacy`).
- Tests: `tests/test_render.py`, `tests/test_repl_ptk_driver.py`.

---

### Task 1: Spike — prove streaming-to-scrollback with a live bottom region

**Files:**
- Create: `src/repl_ptk.py` (skeleton)

**Context:** The whole redesign hinges on: can we stream text into the terminal's scrollback WHILE a live composer+footer stays pinned at the bottom, in a non-full-screen prompt_toolkit app? This spike proves the mechanic before building on it. The pattern: an `Application(full_screen=False)` whose layout is `HSplit([Frame(TextArea), Window(footer)])`; output-above is emitted with `app.run_in_terminal(print_fn)` (which clears the live region, prints to scrollback, redraws). Streaming = call `run_in_terminal` per chunk.

- [ ] **Step 1: Write the spike**

```python
# src/repl_ptk.py
"""jarvis-code render-lag i prompt_toolkit (Claude Code-model: scrollback + live bund-region)."""
from __future__ import annotations
import asyncio
import sys

from prompt_toolkit import Application
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.key_binding import KeyBindings


def _spike() -> None:
    kb = KeyBindings()
    input_area = TextArea(height=1, prompt="❯ ", multiline=False)
    footer = Window(FormattedTextControl(lambda: "ctx:full · demo footer"), height=1)
    root = HSplit([Frame(input_area), footer])
    app = Application(layout=Layout(root, focused_element=input_area),
                      key_bindings=kb, full_screen=False)

    @kb.add("c-c")
    @kb.add("c-q")
    def _quit(event):
        event.app.exit()

    @kb.add("enter")
    def _submit(event):
        text = input_area.text
        input_area.text = ""
        if not text.strip():
            return
        async def _emit():
            # stream tokens ABOVE the live region (into scrollback)
            for tok in ("Modtaget: " + text).split():
                await run_in_terminal(lambda t=tok: print(t, end=" ", flush=True))
                await asyncio.sleep(0.03)
            await run_in_terminal(lambda: print())
        event.app.create_background_task(_emit())

    app.run()


if __name__ == "__main__":
    _spike()
```

- [ ] **Step 2: Run the spike interactively (manual) and verify the mechanic**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m src.repl_ptk`
Expected: a bordered input box + footer pinned at the bottom; typing + Enter streams "Modtaget: …" into the scrollback ABOVE the box; you can scroll up and select/copy with the mouse natively; Ctrl+C/Ctrl+Q exits. NOTE: cannot be unit-tested (needs a TTY); the controller verifies visually via a screenshot on Bjørn's screen. If `run_in_terminal` streaming flickers badly, record the finding and switch to buffering a whole message then one `run_in_terminal` per completed block — document the choice in a module comment.

- [ ] **Step 3: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py
git commit -m "spike(jc-ptk): stream-to-scrollback + live bottom region proven"
```

---

### Task 2: `render.py` — pure two-column banner

**Files:**
- Create: `src/render.py`
- Test: `tests/test_render.py`

**Context:** Banner is printed once to scrollback. Two columns: left = logo/welcome/model/cwd, right = commands. Pure function returning plain text (ANSI added by caller) so it's testable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
from src import render


def test_banner_two_column_has_info_left_and_commands_right():
    out = render.banner(version="0.5.0", user="Bjørn", model="deepseek-v4-flash",
                        context="full", cwd="/home/bs/jarvis-code", width=80,
                        commands=["/help", "/context", "/plan", "/files"])
    assert "jarvis-code" in out and "0.5.0" in out
    assert "Bjørn" in out
    assert "deepseek-v4-flash" in out and "full" in out
    assert "~/jarvis-code" in out          # home-forkortet
    assert "/help" in out and "/plan" in out  # kommandoer (højre)
    # to-kolonne: en linje har BÅDE venstre-info og en kommando
    assert any(("jarvis-code" in ln and "/" in ln) or ("Bjørn" in ln and "/" in ln)
               for ln in out.splitlines())


def test_banner_condensed_on_narrow_width():
    out = render.banner(version="0.5.0", user="Bjørn", model="m", context="full",
                        cwd="/home/bs/x", width=40, commands=["/help"])
    assert out.count("\n") <= 1           # condensed = én linje
    assert "jarvis-code" in out and "full" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_render.py -o addopts="" -q`
Expected: FAIL (`ModuleNotFoundError: src.render`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/render.py
"""Rene render-funktioner (banner, tool-linje, diff, cost) → tekst/ANSI. Ingen app-state,
så de kan unit-testes uden en kørende prompt_toolkit-app."""
from __future__ import annotations
import os

_CONDENSED_WIDTH = 60


def _short_cwd(cwd: str) -> str:
    home = os.path.expanduser("~")
    return (cwd or home).replace(home, "~")


def banner(*, version: str, user: str, model: str, context: str, cwd: str,
           width: int, commands: list[str]) -> str:
    scwd = _short_cwd(cwd)
    if width < _CONDENSED_WIDTH:
        return f"✦ jarvis-code v{version} · {context} · {scwd}"
    left = [
        f"✦ jarvis-code v{version}",
        f"Welcome back, {user}!",
        f"{model} · {context}",
        scwd,
    ]
    # kommandoer i højre kolonne, 3 pr. række
    cmd_rows: list[str] = []
    for i in range(0, len(commands), 3):
        cmd_rows.append("  ".join(commands[i:i + 3]))
    right = ["KOMMANDOER"] + cmd_rows
    rows = max(len(left), len(right))
    gutter = max(1, width - 44)
    out = []
    for i in range(rows):
        lcol = left[i] if i < len(left) else ""
        rcol = right[i] if i < len(right) else ""
        out.append(f"{lcol:<{gutter}}{rcol}".rstrip())
    return "\n".join(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_render.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/render.py tests/test_render.py
git commit -m "feat(jc-render): two-column banner (pure, tested)"
```

---

### Task 3: `render.py` — tool-line, diff, cost/footer

**Files:**
- Modify: `src/render.py`
- Test: `tests/test_render.py`

**Context:** Compact Claude Code-style renderers. `tool_line` = `[name: target] meta`. `diff_lines` = colored +/- (as (text, style) pairs for prompt_toolkit FormattedText). `footer` = `ctx · perms · cost … build`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_render.py
def test_tool_target_from_args():
    # mål = arg (path cwd-relativ, command, pattern, query, url) — som Textual _tool_target
    assert render.tool_target("edit_file", {"path": "/home/bs/jarvis-code/src/parser.py"},
                              "/home/bs/jarvis-code") == "src/parser.py"
    assert render.tool_target("bash", {"command": "pytest -q"}, "/x") == "pytest -q"
    assert render.tool_target("grep", {"pattern": "def foo"}, "/x") == "def foo"
    assert render.tool_target("read_file", {}, "/x") == ""


def test_tool_line_compact():
    assert render.tool_line("edit_file", "src/parser.py", "+32/-0") == "[edit_file: src/parser.py] +32/-0"
    assert render.tool_line("bash", "pytest -q", "exit 0") == "[bash: pytest -q] exit 0"
    assert render.tool_line("read_file", "x.py", "") == "[read_file: x.py]"


def test_diff_lines_colors_and_skips_headers():
    diff = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n a=1\n-b=2\n+b=3"
    pairs = render.diff_lines(diff)
    # returns list[(style, text)]; headers ---/+++/@@ skipped
    texts = [t for _s, t in pairs]
    assert not any(t.startswith(("---", "+++", "@@")) for t in texts)
    styles = {t: s for s, t in pairs}
    assert "green" in styles["    +b=3"].lower() or "8cff98" in styles["    +b=3"].lower()
    assert "red" in styles["    -b=2"].lower() or "ff7b7b" in styles["    -b=2"].lower()


def test_footer_has_context_perms_cost_build():
    f = render.footer(context="full", perms="🔓 auto-edit", elapsed=2.1,
                     in_tok=5100, out_tok=180, cost=0.0027, version="0.5.0", width=100)
    assert "ctx:full" in f and "auto-edit" in f
    assert "5,100" in f and "180" in f and "$0.0027" in f
    assert "v0.5.0" in f
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_render.py -o addopts="" -q`
Expected: FAIL (`AttributeError: tool_line`).

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/render.py
import os
_ADD = "fg:#8cff98"
_DEL = "fg:#ff7b7b"
_DIM = "fg:#2f6f4a"
_CYAN = "fg:#00e5ff"


def tool_target(name: str, args: dict, cwd: str) -> str:
    """Kompakt mål fra args (som Textual _tool_target): relativ sti for fil-tools,
    command for bash, pattern/query/url ellers."""
    if not isinstance(args, dict):
        return ""
    for key in ("path", "file_path", "command", "pattern", "query", "url"):
        v = args.get(key)
        if v:
            v = str(v)
            if key in ("path", "file_path"):
                try:
                    from pathlib import Path
                    v = str(Path(v).resolve().relative_to(Path(cwd).resolve()))
                except Exception:
                    v = os.path.basename(v)
            return v[:64]
    return ""


def tool_line(name: str, target: str, meta: str) -> str:
    label = f"[{name}: {target}]" if target else f"[{name}]"
    return f"{label} {meta}".rstrip()


def diff_lines(diff_text: str, *, max_lines: int = 24, max_width: int = 160) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    shown = 0
    for ln in diff_text.splitlines():
        if ln.startswith(("---", "+++", "@@")):
            continue
        style = _DIM
        if ln.startswith("+"):
            style = _ADD
        elif ln.startswith("-"):
            style = _DEL
        out.append((style, "    " + ln[:max_width]))
        shown += 1
        if shown >= max_lines:
            out.append((_DIM, "    …"))
            break
    return out


def diff_counts(diff_text: str) -> tuple[int, int]:
    adds = sum(1 for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    dels = sum(1 for ln in diff_text.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    return adds, dels


def footer(*, context: str, perms: str, elapsed: float, in_tok: int, out_tok: int,
           cost: float, version: str, width: int) -> str:
    left = f"◉ ctx:{context}  ·  {perms}  ·  ◷ {elapsed:.1f}s"
    if in_tok or out_tok:
        left += f" · {in_tok:,}↑ {out_tok:,}↓ tok"
    if cost > 0:
        left += f" · ${cost:.4f}"
    build = f"build v{version}"
    pad = max(1, width - len(left) - len(build))
    return f"{left}{' ' * pad}{build}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_render.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/render.py tests/test_render.py
git commit -m "feat(jc-render): compact tool-line, colored diff, footer (tested)"
```

---

### Task 4: repl_ptk — Application shell (banner, composer Frame, footer, input loop, slash dispatch)

**Files:**
- Modify: `src/repl_ptk.py`
- Test: manual (TTY)

**Context:** Replace the spike with the real shell. On start: print the two-column banner (`render.banner`) to scrollback. Build the `Application(full_screen=False)` with `Frame(TextArea)` composer + a footer `Window` whose text = `render.footer(...)` from live state. Enter submits → dispatch: `/`-commands via a slash handler (reuse `src/commands.py` where possible), else run a turn (Task 5). Ctrl+C = stop-or-quit, Ctrl+Q = quit. Keep app state on a small `PtkState` object: `config, session_id, tool_loop, context, api_url, auth_token, cwd, plan_mode, turn_cost, undo_stack`.

- [ ] **Step 1: Implement the shell** (replace `_spike`; keep the file importable without a TTY — guard `.run()` behind `main()`).

Provide: `class PtkApp` holding state + `_build_footer_text()` (calls `render.footer`), `_print_banner()` (calls `render.banner` + prints via `print`), `_on_submit(text)` dispatching slash vs turn, key bindings (enter/c-c/c-q), and `def run_repl_ptk(*, config, session_id, model, mode, messages, cwd, ...) -> int`. Emit output ABOVE via `run_in_terminal`. Store the resolved `api_url`/`auth_token` (from `get_auth_token(config)`), mirroring `tui.py` `__init__`.

- [ ] **Step 2: Import-safe check**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -c "from src import repl_ptk; print('import OK')"`
Expected: `import OK` (no TTY needed to import).

- [ ] **Step 3: Manual smoke**

Run in a terminal: `/opt/conda/envs/ai/bin/python -c "from src.repl_ptk import run_repl_ptk; run_repl_ptk(config={'api_url':'https://api.srvlab.dk'}, session_id='t', model='deepseek-v4-flash', mode='code', messages=[], cwd='/home/bs/jarvis-code')"`
Expected: banner (two-column) in scrollback, bordered composer + footer at bottom; `/help` prints help; typing a message reaches the turn driver (Task 5 makes it respond).

- [ ] **Step 4: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py
git commit -m "feat(jc-ptk): Application shell — banner, Frame composer, footer, slash dispatch"
```

---

### Task 5: repl_ptk — turn driver (reuse client loop; stream + tool-lines + diff + cost)

**Files:**
- Modify: `src/repl_ptk.py`
- Test: `tests/test_repl_ptk_driver.py`

**Context:** Port the turn logic from `tui.py::_run_turn_client` (mirror it — do NOT edit tui.py). Reuse `api.agent_step_stream`/`agent_step`, `tools.route_tool_call`/`execute_tool`. Render via `render.*` emitted through `run_in_terminal`. Extract the pure decision helper so it's unit-testable: `def classify_tool_result(name, result) -> tuple[str, str, str|None]` returning `(status, meta, diff_text)` — used to decide the compact line + diff. Capture undo payload + strip it before appending to model messages (same as tui.py). Capture usage into `state.turn_cost`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repl_ptk_driver.py
from src import repl_ptk


def test_classify_tool_result_edit_gives_diff_and_counts():
    result = {"status": "ok", "diff": "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a=1\n+a=2",
              "_undo_path": "/x", "_undo_prev": "a=1", "_undo_was_new": False}
    status, meta, diff = repl_ptk.classify_tool_result("edit_file", result)
    assert status == "ok"
    assert meta == "+1/-1"
    assert diff and "+a=2" in diff


def test_classify_tool_result_bash_shows_exit_meta():
    status, meta, diff = repl_ptk.classify_tool_result("bash", {"status": "ok", "exit_code": 0})
    assert status == "ok" and meta == "exit 0" and diff is None


def test_classify_strips_undo_payload_from_model_result():
    result = {"status": "ok", "diff": "x", "_undo_path": "/x", "_undo_prev": "old", "_undo_was_new": True}
    repl_ptk.classify_tool_result("write_file", result)
    # after classify, the heavy undo payload is removed from the dict sent to the model
    assert "_undo_prev" not in result and "diff" not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: FAIL (`AttributeError: classify_tool_result`).

- [ ] **Step 3: Implement `classify_tool_result` + the streaming turn driver**

`classify_tool_result(name, result)`:
```python
def classify_tool_result(name, result):
    from src import render
    if not isinstance(result, dict):
        return "ok", "", None
    diff = result.pop("diff", None)
    # capture undo elsewhere BEFORE calling this (driver pushes to undo_stack); strip here
    result.pop("_undo_prev", None); result.pop("_undo_path", None); result.pop("_undo_was_new", None)
    status = str(result.get("status", "ok"))
    if diff:
        a, d = render.diff_counts(diff)
        return status, f"+{a}/-{d}", diff
    if result.get("error"):
        return status, f"✗ {str(result['error'])[:60]}", None
    if "exit_code" in result:
        return status, f"exit {result['exit_code']}", None
    if "count" in result:
        return status, f"{result['count']} træf", None
    return status, "", None
```
Then the driver (mirror `tui.py::_run_turn_client`): build convo from `state.messages`, prepend PLAN-MODE instruction if `state.plan_mode=='readonly'`, loop up to 15 rounds calling `agent_step_stream` (stream deltas to scrollback), execute tool_calls locally/forwarded, capture undo to `state.undo_stack` BEFORE `classify_tool_result`, emit the compact tool-line + diff via `run_in_terminal`, block writes when plan-mode, run auto-test after edits, capture usage → `state.turn_cost`, and refresh the footer.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Manual e2e smoke** (real server): ask it to read/edit a file → assistant streams into scrollback, `[edit_file: …] +N/-M` + inline diff appear, footer shows cost.

- [ ] **Step 6: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py tests/test_repl_ptk_driver.py
git commit -m "feat(jc-ptk): turn driver — stream to scrollback, compact tool-lines, diff, cost"
```

---

### Task 6: repl_ptk — liveness, inline approval, undo (Ctrl+Z)

**Files:**
- Modify: `src/repl_ptk.py`
- Test: `tests/test_repl_ptk_driver.py`

**Context:** (a) Live status line during a turn (spinner · time · tokens) via an app timer that invalidates the footer. (b) Inline approval: when a local write/dangerous tool needs approval, show an inline prompt line and block the worker on a `threading.Event` (mirror `tui.py` `_request_approval_blocking`); resolve via y/n keys. (c) Undo: `Ctrl+Z` pops `state.undo_stack` and restores/deletes the file (mirror `tui.py::action_undo`).

- [ ] **Step 1: Write the failing test** (undo logic is pure enough to test)

```python
# add to tests/test_repl_ptk_driver.py
import tempfile, os
def test_undo_restores_previous_content():
    d = tempfile.mkdtemp(); f = os.path.join(d, "x.py")
    open(f, "w").write("NEW")
    stack = [(f, "OLD", False)]
    repl_ptk.apply_undo(stack)
    assert open(f).read() == "OLD" and not stack

def test_undo_deletes_new_file():
    d = tempfile.mkdtemp(); f = os.path.join(d, "n.py")
    open(f, "w").write("x")
    stack = [(f, "", True)]
    repl_ptk.apply_undo(stack)
    assert not os.path.exists(f)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: FAIL (`AttributeError: apply_undo`).

- [ ] **Step 3: Implement `apply_undo` + wire liveness/approval**

```python
def apply_undo(undo_stack):
    from pathlib import Path
    if not undo_stack:
        return False
    path, prev, was_new = undo_stack.pop()
    if was_new:
        Path(path).unlink(missing_ok=True)
    else:
        Path(path).write_text(prev, encoding="utf-8")
    return True
```
Wire `Ctrl+Z` → `apply_undo(state.undo_stack)` + emit a note. Add a `set_interval`-style app timer that invalidates the app so the footer's liveness updates while `state.busy`. Add inline approval (block worker on `threading.Event`, resolve via key handler).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py tests/test_repl_ptk_driver.py
git commit -m "feat(jc-ptk): liveness timer, inline approval, undo (Ctrl+Z)"
```

---

### Task 7: repl_ptk — slash commands parity + mode persistence + catalog

**Files:**
- Modify: `src/repl_ptk.py`
- Test: `tests/test_repl_ptk_driver.py`

**Context:** Port slash handlers from `tui.py::_handle_slash`: `/help /context none|identity|full /plan [off] /loop /mode /native /undo /session /version /files /quit`. `/context` + `/loop` persist mode via config-merge (mirror `tui.py::_persist_mode` — read `GLOBAL_CONFIG_FILE`, update `tool_loop`+`context`, `save_config`, preserving token). On start, fetch the curated catalog (`api.fetch_catalog`) into `state.presented_tools` (local tools + companions); `load_more_tools` unlocks runtime_ aliases. Full-context: `/context full` → `context='full'`, `tool_loop='client'` (send `context=full` to agent-step).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_repl_ptk_driver.py
def test_persist_mode_merges_and_preserves_token(tmp_path, monkeypatch):
    import json
    cfgf = tmp_path / "config.json"; cfgf.write_text(json.dumps({"auth_token": "SECRET"}))
    monkeypatch.setattr("src.config.GLOBAL_CONFIG_FILE", cfgf)
    repl_ptk.persist_mode({"auth_token": "SECRET"}, tool_loop="client", context="full")
    saved = json.loads(cfgf.read_text())
    assert saved["auth_token"] == "SECRET" and saved["tool_loop"] == "client" and saved["context"] == "full"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: FAIL (`AttributeError: persist_mode`).

- [ ] **Step 3: Implement `persist_mode` + slash handlers**

```python
def persist_mode(config, *, tool_loop, context):
    import json
    from src.config import GLOBAL_CONFIG_FILE, save_config
    existing = {}
    if GLOBAL_CONFIG_FILE.exists():
        existing = json.loads(GLOBAL_CONFIG_FILE.read_text(encoding="utf-8")) or {}
    existing["tool_loop"] = tool_loop; existing["context"] = context
    config["tool_loop"] = tool_loop; config["context"] = context
    save_config(existing, global_scope=True)
```
Wire the slash dispatcher to call it on `/context`+`/loop`, and implement the other commands (emit help/status via `run_in_terminal`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py tests/test_repl_ptk_driver.py
git commit -m "feat(jc-ptk): slash parity, mode persistence, curated catalog"
```

---

### Task 8: repl_ptk — file-picker (`/files`) + auto-test parity

**Files:**
- Modify: `src/repl_ptk.py`
- Test: `tests/test_repl_ptk_driver.py`

**Context:** `/files` opens a light file-picker (prompt_toolkit `PathCompleter`/fuzzy over the project, or a simple prompt with completion) → chosen path inserted into the composer. Auto-test: mirror `tui.py::_detect_test_command` (pytest/npm/cargo/go + config `test_command`, gated on config `auto_test`), run after a write/edit, emit result as a compact line.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_repl_ptk_driver.py
def test_detect_test_command_pytest(tmp_path):
    (tmp_path / "tests").mkdir()
    assert repl_ptk.detect_test_command(str(tmp_path), {}) == "python -m pytest -q"

def test_detect_test_command_config_override(tmp_path):
    assert repl_ptk.detect_test_command(str(tmp_path), {"test_command": "make test"}) == "make test"

def test_detect_test_command_none(tmp_path):
    assert repl_ptk.detect_test_command(str(tmp_path), {}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: FAIL (`AttributeError: detect_test_command`).

- [ ] **Step 3: Implement `detect_test_command` + file-picker**

```python
def detect_test_command(cwd, config):
    from pathlib import Path
    cfg = str((config or {}).get("test_command") or "").strip()
    if cfg:
        return cfg
    root = Path(cwd)
    if (root / "pytest.ini").exists() or (root / "tests").is_dir() or (root / "pyproject.toml").exists():
        return "python -m pytest -q"
    if (root / "package.json").exists():
        return "npm test --silent"
    if (root / "Cargo.toml").exists():
        return "cargo test -q"
    if (root / "go.mod").exists():
        return "go test ./..."
    return None
```
Wire `/files` (PathCompleter picker) + call `detect_test_command` after edits when `config.auto_test`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_repl_ptk_driver.py -o addopts="" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/bs/jarvis-code
git add src/repl_ptk.py tests/test_repl_ptk_driver.py
git commit -m "feat(jc-ptk): file-picker + auto-test parity"
```

---

### Task 9: main.py wiring — default = ptk, `--legacy` = Textual, `--simple` = repl

**Files:**
- Modify: `src/main.py`
- Test: manual

**Context:** Read `src/main.py` first. Find where it currently launches the TUI (`run_tui`) vs simple repl. Make `run_repl_ptk` the DEFAULT interactive path; `--legacy` → `run_tui` (unchanged Textual); `--simple`/non-TTY → existing linear repl. Pass the same args (config, session_id, model, mode, messages, cwd) as `run_tui` gets today.

- [ ] **Step 1: Implement the dispatch** (add `--legacy` arg via the existing argparse; route default → `run_repl_ptk`).

- [ ] **Step 2: Import + arg smoke**

Run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m src.main --help 2>&1 | head -30`
Expected: help shows `--legacy`; no import errors.

- [ ] **Step 3: Manual: default launches ptk; `--legacy` launches Textual; `--simple` launches repl.**

- [ ] **Step 4: Commit**

```bash
cd /home/bs/jarvis-code
git add src/main.py
git commit -m "feat(jc): default to prompt_toolkit UI; Textual kept as --legacy"
```

---

### Task 10: Full verification — parity + visual + legacy green

**Files:** none (verification)

- [ ] **Step 1: Full test suite** — `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/ -o addopts="" -q` → all PASS (new render + driver tests + existing 185 Textual tests unchanged).

- [ ] **Step 2: Live visual on Bjørn's screen** (controller): launch `jarvis-code` (default = ptk) in gnome-terminal, screenshot; verify: two-column banner, bordered composer + footer, a real turn streams into scrollback with `[tool: target] +N/-M` + inline diff, cost in footer, and that mouse selection/scroll/copy work natively in the terminal.

- [ ] **Step 3: Parity checklist** — confirm each Textual feature works in ptk: context tiers (none/identity/full), mode persistence across `--continue`, curated catalog + runtime_ prefix, diff/undo/cost/plan/auto-test, stop-stream (Ctrl+C)/quit (Ctrl+Q), slash commands, connection indicator. Note any gaps.

- [ ] **Step 4: Use superpowers:finishing-a-development-branch** (jc is on master, no remote — verify tests green + commit history clean; do NOT delete Textual `tui.py`).

---

## Self-Review (plan author)

**Spec coverage:** §2 architecture → Task 1 (spike) + Task 4 (shell). §3.1 banner → Task 2. §3.2 composer/footer → Tasks 3, 4. §3.3 messages/tool-lines/diff → Tasks 3, 5. §3.4 liveness → Task 6. §3.5 approval → Task 6. §3.6 file-tree → Task 8. §4 feature-parity: context tiers/persistence/catalog → Task 7; diff/undo/cost/plan/auto-test → Tasks 5, 6, 8; native copy/scroll → Task 1 (proven) + Task 10 (verified). §6 testing → pure `render.py` + driver helpers unit-tested; legacy suite green in Task 10. §7 open detail (print-over-live-region) → Task 1 spike resolves it.

**Placeholder scan:** No TBD/TODO. Manual-smoke steps are explicit (TTY UI can't be unit-tested — the pure helpers ARE tested, and the controller verifies visually, per the "verify visual before done" rule).

**Type consistency:** `render.banner/tool_line/diff_lines/diff_counts/footer` (Tasks 2-3) used in Tasks 4-5. `classify_tool_result` (Task 5), `apply_undo` (Task 6), `persist_mode` (Task 7), `detect_test_command` (Task 8) — each defined once, signatures stable. `run_repl_ptk(config, session_id, model, mode, messages, cwd)` (Task 4) matches `main.py` call site (Task 9) and mirrors `run_tui`'s signature.
