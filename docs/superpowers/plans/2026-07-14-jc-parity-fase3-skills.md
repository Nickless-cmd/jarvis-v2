# jarvis-code Skill-System Trigger (Fase 3) Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Make Jarvis actually *use* his 64 installed skills from inside the jarvis-code client loop by wiring the existing skill engine (never rebuilding it) through six trigger pieces: a skill catalog in the system prompt, a deterministic client-side `skill_gate` auto-call on the first user turn, a promoted companion tool, a visible "using skill X" announcement, revived tool-name translation, and owner-approval governance over auto-surfacing.

**Architecture:** The skill *engine* stays 100% server-side (`core/services/skill_engine.py`, `core/tools/skill_gate_tool.py`) and is reused verbatim. The server injects a compact skill catalog into the system prompt it already builds in `agent_loop._build_system_prompt`, promotes `skill_gate` into the jarvis-code companion catalog, and adds an owner-approved allowlist that gates *which* skills are auto-surfaced (flag-gated, default OFF). The **client** (`jarvis-code`, which CANNOT import `core.*`) reimplements only the glue: on the first user turn it calls the forwarded `skill_gate` tool, translates any Claude-Code tool names in the returned instructions to Jarvis equivalents, prepends the result as context, and renders a green announcement line.

**Tech Stack:** Python 3.11+. Server: FastAPI (`apps/api/jarvis_api`), `core/services` + `core/tools`, pytest (`/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`). Client: `jarvis-code` (`/home/bs/jarvis-code/src`), prompt_toolkit REPL, httpx, pytest in the `ai` conda env. No new dependencies.

## File Structure

### [SERVER jarvis-v2] `/media/projects/jarvis-v2`
- **`core/runtime/settings.py`** (MODIFY, anchors `:96`, `:627`) — add one flag `skill_autosurface_enabled: bool = False` (default OFF; governs the whole auto-surface feature) to the `Settings` dataclass + loader.
- **`core/services/skill_autosurface.py`** (CREATE) — single responsibility: owner-approved allowlist of skills eligible for auto-surfacing (persisted in `~/.jarvis-v2/config/skill_autosurface.json`), plus filter/approve/revoke helpers. Ties governance to `project_self_registering_nerves` (durable, owner-gated component registry).
- **`core/tools/jc_tool_catalog.py`** (MODIFY, anchor `:20` `DEFAULT_COMPANIONS`) — add `"skill_gate"` so the client catalog includes it.
- **`apps/api/jarvis_api/routes/agent_loop.py`** (MODIFY, anchors `:50` `_SYSTEM_PROMPT`, `:120` `_build_system_prompt`) — add `_skill_catalog()` (calls `skill_engine.list_skills()` filtered by `skill_autosurface`), a CC-style "call skill_gate first" instruction, and a CC→Jarvis tool legend; append into the system prompt.
- **`core/tools/skill_gate_tool.py`** (MODIFY, anchors `:94` `_exec_skill_gate`, `:149` suggestions, `:293` params schema) — add an optional `autosurface: bool` arg that restricts candidate skills to the owner-approved allowlist (used only by the client auto-call; backward-compatible, default false).

### [CLIENT jarvis-code] `/home/bs/jarvis-code`
- **`src/skill_trigger.py`** (CREATE) — pure, UI-free glue: build the auto-call query, translate Claude-Code tool names → Jarvis equivalents in returned instructions, and format the context block that gets prepended. Kept out of `repl_ptk.py` (81 KB, over budget — Boy Scout).
- **`src/repl_ptk.py`** (MODIFY, anchors `:811` `_turn_worker`, `:830` convo build, `__init__` `:268`) — read a `skill_auto_gate` config flag; on the first user turn, call `skill_gate` (forwarded via `tools.route_tool_call`), prepend the formatted context, render the announcement.
- **`src/config.py`** (MODIFY, anchor `:42` `DEFAULTS`) — add `"skill_auto_gate": True` + `JARVIS_SKILL_AUTOGATE` env mapping.
- **`src/render.py`** (MODIFY, anchor `:227` `sb_sys`) — add `sb_skill(name, one_liner)` announcement helper.
- **`tests/test_skill_trigger.py`** (CREATE) — unit tests for the client glue.

---

### Task 1: [SERVER jarvis-v2] Owner-approved auto-surface allowlist + governance flag

Build this first — both the catalog injection (Task 3) and the auto-call gate (Task 4) read it. Governance requirement from spec §4: auto-surfacing widens the injection surface, so *which* skills are auto-surfaced requires owner approval; the model can `write_file` a `SKILL.md` and self-modify its own prompt, so the allowlist is the choke point.

**Files:**
- Modify: `core/runtime/settings.py` — dataclass field near `:96` (beside `skill_gate_enabled`), loader near `:627`.
- Create: `core/services/skill_autosurface.py`.
- Test: `tests/test_skill_autosurface.py` (CREATE).

**Reimplementation note:** pure server code; no client involvement.

- [ ] Step: Write failing test `tests/test_skill_autosurface.py`. Use a `tmp_path` monkeypatched config dir. Tests + asserts:
  - `test_flag_defaults_off` — `load_settings().skill_autosurface_enabled is False`.
  - `test_empty_allowlist_by_default` — `list_approved()` returns `[]` on a fresh store.
  - `test_approve_requires_owner` — `approve_skill("tdd", role="user")` raises `PermissionError`; `approve_skill("tdd", role="owner")` returns `True` and persists.
  - `test_approve_rejects_unknown_skill` — `approve_skill("does-not-exist", role="owner")` returns `False` (validated against `skill_engine.skill_exists`).
  - `test_filter_allowlist_flag_off` — with flag OFF, `filter_to_approved(["tdd","brand"])` returns `[]` (feature inert until owner opts in).
  - `test_filter_allowlist_flag_on` — with flag ON and only `tdd` approved, `filter_to_approved(["tdd","brand"])` returns `["tdd"]`.
  - `test_revoke` — approve then `revoke_skill("tdd", role="owner")` → `list_approved()` empty.
- [ ] Step: Run (expected FAIL — module missing): `/opt/conda/envs/ai/bin/python -m pytest tests/test_skill_autosurface.py -o addopts=""`.
- [ ] Step: Add flag to `core/runtime/settings.py`: field `skill_autosurface_enabled: bool = False` after line `:96` with a docstring "Governs jarvis-code skill auto-surfacing (catalog injection + client auto-call restricted to the owner-approved allowlist in skill_autosurface.json). Default OFF: the whole Fase 3 skill-trigger is inert until the owner opts in and approves skills."; loader entry `skill_autosurface_enabled=bool(data.get("skill_autosurface_enabled", defaults.skill_autosurface_enabled))` after line `:629`.
- [ ] Step: Implement `core/services/skill_autosurface.py` with: `_STORE_PATH` = `runtime_paths.config_dir()/"skill_autosurface.json"` (reuse existing `core.runtime.paths`); `list_approved() -> list[str]` (reads JSON `{"approved": [...]}`, empty on missing/corrupt — fail-safe); `approve_skill(name, *, role) -> bool` (raise `PermissionError` unless `role == "owner"`; return `False` unless `skill_engine.skill_exists(name)`; else add + persist + emit a governance nerve `skill.autosurface.approved` if the eventbus is importable, self-safe); `revoke_skill(name, *, role) -> bool` (owner-gated, remove + persist); `filter_to_approved(names: list[str]) -> list[str]` (returns `[]` when `not load_settings().skill_autosurface_enabled`, else `[n for n in names if n in set(list_approved())]`). All disk I/O wrapped self-safe (never crash the prompt path).
- [ ] Step: Run (expected PASS): `/opt/conda/envs/ai/bin/python -m pytest tests/test_skill_autosurface.py -o addopts=""`.
- [ ] Step: Commit `feat(skill-autosurface): owner-approved allowlist governing jarvis-code auto-surfacing (flag default OFF)`.

**Acceptance:** flag defaults OFF; approve/revoke are owner-only and validate against installed skills; `filter_to_approved` is empty unless the owner enabled the flag AND approved skills.

---

### Task 2: [SERVER jarvis-v2] Promote `skill_gate` into `DEFAULT_COMPANIONS`

So the client's fetched catalog (`build_jc_catalog` at `jc_tool_catalog.py:71` → `/v1/tools/catalog`) presents `skill_gate` as a normal companion the model can call, and `is_forwarded_tool` (client `tool_catalog.py:20`) forwards it to `/v1/tools/execute`. `skill_gate` is already globally registered (`simple_tools.py:1776` → `SKILL_GATE_TOOL_HANDLERS`), so no wiring beyond the catalog is needed.

**Files:**
- Modify: `core/tools/jc_tool_catalog.py` — `DEFAULT_COMPANIONS` tuple at `:20-25`.
- Test: `tests/test_jc_tool_catalog.py` (MODIFY — existing file, `test_default_companions_list` at `:8`).

**Reimplementation note:** pure server; client picks it up for free via the catalog endpoint.

- [ ] Step: Update failing test — edit `tests/test_jc_tool_catalog.py::test_default_companions_list` (`:8`) to include `"skill_gate"` in the expected tuple, and add `test_skill_gate_in_catalog_locked`: feed `_all_native_defs` a fake list (via monkeypatch of `cat._all_native_defs`) containing a `skill_gate` def, assert `"skill_gate"` appears in `build_jc_catalog(role="owner", unlocked=False)` names even when locked.
- [ ] Step: Run (expected FAIL): `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts=""`.
- [ ] Step: Add `"skill_gate"` to the `DEFAULT_COMPANIONS` tuple in `core/tools/jc_tool_catalog.py:20` (append after `"read_mood"`). Update the file's module docstring line noting skill_gate is now an always-present companion.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit `feat(jc-catalog): promote skill_gate to DEFAULT_COMPANIONS`.

**Acceptance:** `build_jc_catalog` includes `skill_gate` in both locked and unlocked modes; existing catalog tests still pass.

---

### Task 3: [SERVER jarvis-v2] Inject skill catalog + activation instruction + CC-tool legend into the system prompt

Piece (1), (2)-prompt-backup, and (5)-legend from the spec. The system prompt is built server-side in `agent_loop._build_system_prompt` (`:120`), so the catalog injection lives here (the client cannot import `skill_engine`). ~100 tokens, progressive disclosure: names + `use_when` + tags only, gated by the owner allowlist so the injection surface is governed.

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` — add `_skill_catalog()` after `_SYSTEM_PROMPT` (`:57`); call it inside `_build_system_prompt` (`:120-131`).
- Test: `tests/test_agent_loop_skill_catalog.py` (CREATE).

**Reimplementation note:** server-only; the injected text reaches the client via the normal `/v1/agent/step` system message.

- [ ] Step: Write failing `tests/test_agent_loop_skill_catalog.py`. Import the route module (`from apps.api.jarvis_api.routes import agent_loop`). Tests + asserts:
  - `test_catalog_empty_when_flag_off` — monkeypatch `agent_loop.skill_autosurface.filter_to_approved` (or the settings flag) so nothing is approved → `agent_loop._skill_catalog()` returns `""` (no injection, feature inert).
  - `test_catalog_lists_approved_skills` — monkeypatch `_skill_catalog`'s data sources so `list_skills()` returns two fakes (`{"name":"tdd","use_when":"writing code","tags":["coding"]}`, `{"name":"brand","use_when":"brand voice","tags":["marketing"]}`) and both are approved → returned string contains `tdd`, `writing code`, and the header `TILGÆNGELIGE SKILLS`, and is under ~1200 chars.
  - `test_catalog_respects_allowlist` — only `tdd` approved → string contains `tdd` but not `brand`.
  - `test_system_prompt_includes_catalog_and_instruction` — with the flag on + `tdd` approved, `_build_system_prompt("identity", "fix a bug")` contains both the catalog header and the activation instruction substring `kald skill_gate` and the legend substring `Write → write_file`.
  - `test_system_prompt_none_context_still_gets_catalog` — `_build_system_prompt("none", "x")` still contains the catalog (skills are relevant even in pure-coding tier).
- [ ] Step: Run (expected FAIL): `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_loop_skill_catalog.py -o addopts=""`.
- [ ] Step: Implement `_skill_catalog()` in `agent_loop.py` (after `:57`): self-safe; `from core.services import skill_engine, skill_autosurface`; `skills = skill_engine.list_skills()`; `names = skill_autosurface.filter_to_approved([s["name"] for s in skills])`; if empty return `""`; else render one line per approved skill as `- {name}: {use_when} [{', '.join(tags[:3])}]`, capped at ~15 lines / ~1000 chars, prefixed with a header `\n\n## TILGÆNGELIGE SKILLS (kald skill_gate(query=...) FØR du handler hvis én matcher)\n`. Add module constants `_SKILL_ACTIVATION` (CC-style: "Hvis en skill nedenfor matcher opgaven, kald skill_gate(query=<opgaven>) FØR du gør noget andet — den loader det rette workflow.") and `_CC_TOOL_LEGEND` (from `docs/_archive/skills-jarvis-compat.md`: "Skill-instruktioner kan nævne Claude Code-tools. Oversæt: Write → write_file/bash · Read → read_file · Edit → edit_file · Task → dispatch (subagent) · Worktree → git worktree via bash · TodoWrite → intern plan · Grep/Glob → grep/glob.").
- [ ] Step: In `_build_system_prompt` (`:120`), append `_skill_catalog()` + `_SKILL_ACTIVATION` + `_CC_TOOL_LEGEND` to every return path (none/identity/full). Keep it a single trailing block so prompt-cache prefixes (Fase 4 V) stay stable — append AFTER identity/full context, once.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit `feat(agent-loop): inject owner-approved skill catalog + skill_gate activation + CC-tool legend into system prompt`.

**Acceptance:** with the flag OFF the system prompt is byte-identical to today (no injection); with the flag ON + approved skills, the prompt gains a ≤~1000-char catalog, an activation instruction, and the tool legend.

---

### Task 4: [SERVER jarvis-v2] `skill_gate(autosurface=true)` restricts matching to the allowlist

The client auto-call (Task 6) must not widen the attack surface beyond what the owner approved. Add a backward-compatible `autosurface` arg to `_exec_skill_gate`: when true (and the server flag is on), suggestions are filtered to the owner-approved allowlist BEFORE selection. Default false → every other caller (the model calling `skill_gate` directly) is unchanged.

**Files:**
- Modify: `core/tools/skill_gate_tool.py` — `_exec_skill_gate` (`:94`), after suggestions at `:149-154`; params schema at `:293-322`.
- Test: `tests/test_skill_gate_autosurface.py` (CREATE).

**Reimplementation note:** server-only. Reuses the existing matcher; only the candidate pool is narrowed.

- [ ] Step: Write failing `tests/test_skill_gate_autosurface.py`. Monkeypatch `skill_gate_tool._suggest_skills_for_query` to return a fixed list `[{"name":"brand","score":0.6}, {"name":"tdd","score":0.5}]`. Tests:
  - `test_autosurface_false_unchanged` — `_exec_skill_gate({"query":"x"})` (no autosurface) selects `brand` (top score) exactly as today.
  - `test_autosurface_filters_to_allowlist` — monkeypatch `skill_autosurface.filter_to_approved` to keep only `tdd`; `_exec_skill_gate({"query":"x","autosurface":True})` → `gate_result == "invoked"` with `skill_name == "tdd"` (brand dropped though higher-scored).
  - `test_autosurface_empty_allowlist_no_match` — allowlist filters to `[]`; `autosurface=True` → `gate_result == "no_match"` (nothing surfaced), status ok, no crash.
  - `test_schema_has_autosurface` — `SKILL_GATE_TOOL_DEFINITIONS[0]["function"]["parameters"]["properties"]` contains `autosurface`.
- [ ] Step: Run (expected FAIL): `/opt/conda/envs/ai/bin/python -m pytest tests/test_skill_gate_autosurface.py -o addopts=""`.
- [ ] Step: Implement in `_exec_skill_gate` after the suggestions call (`:154`): read `autosurface = bool(args.get("autosurface"))`; if `autosurface`, `from core.services import skill_autosurface`; `allowed = set(skill_autosurface.filter_to_approved([s["name"] for s in suggestions]))`; `suggestions = [s for s in suggestions if s["name"] in allowed]`. Then the existing `if not suggestions:` no-match branch handles the empty case unchanged. Add `"autosurface": {"type":"boolean","description":"Restrict matching to owner-approved auto-surface skills (used by jarvis-code's first-turn auto-call). Default false."}` to the params schema at `:293`.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit `feat(skill-gate): optional autosurface arg restricts matching to owner-approved allowlist`.

**Acceptance:** direct model calls to `skill_gate` are unchanged; `autosurface=true` narrows candidates to the allowlist and returns a clean `no_match` when nothing is approved.

---

### Task 5: [CLIENT jarvis-code] `skill_trigger.py` — pure glue (query, translation, formatting)

Piece (5) tool-name translation + the pure parts of piece (2). Kept out of `repl_ptk.py` (81 KB, over the 1500-line budget — Boy Scout: extract the natural unit). jarvis-code CANNOT import `core.*`, so the CC→Jarvis mapping is reimplemented here as a client-side table.

**Files:**
- Create: `/home/bs/jarvis-code/src/skill_trigger.py`.
- Test: `/home/bs/jarvis-code/tests/test_skill_trigger.py` (CREATE).

**Reimplementation note:** the mapping table mirrors `docs/_archive/skills-jarvis-compat.md` but is a fresh client-side implementation (we build our own; no core import).

- [ ] Step: Write failing `tests/test_skill_trigger.py`. Tests + asserts:
  - `test_build_query_uses_user_text` — `skill_trigger.build_query("write a red-green TDD test")` returns that string trimmed.
  - `test_translate_cc_tools_appends_legend` — `translate_cc_tools("Use the Write tool then a Task subagent")` returns text that still contains the original AND appends a legend block naming `Write → write_file/bash` and `Task → dispatch` (non-destructive: prose is NOT rewritten in place, a legend is appended so instructions stay intact).
  - `test_translate_no_cc_tools_noop` — text with no CC tool names returns unchanged (no legend appended).
  - `test_format_context_block_invoked` — `format_context_block({"gate_result":"invoked","skill_name":"tdd","score":0.6,"instructions":"do X"})` returns a `[SKILL: tdd]` fenced block containing `do X` and the score.
  - `test_format_context_block_no_match_returns_none` — `gate_result == "no_match"` → returns `None` (nothing prepended).
  - `test_format_context_block_disabled_returns_none` — a disabled/kill-switch stub (`gate_result` absent or `"disabled"`) → `None`.
  - `test_announcement_text` — `announcement({"skill_name":"tdd","skill_use_when":"writing code","score":0.62})` returns `("tdd", "writing code")` tuple (name + one-liner) for the renderer.
- [ ] Step: Run (expected FAIL): `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_skill_trigger.py -o addopts=""`.
- [ ] Step: Implement `src/skill_trigger.py`: `_CC_MAP = {"Write":"write_file/bash","Read":"read_file","Edit":"edit_file","Task":"dispatch (subagent)","Worktree":"git worktree via bash","TodoWrite":"intern plan","Glob":"glob","Grep":"grep"}`; `build_query(user_text)`; `translate_cc_tools(text)` (word-boundary regex `\b(Write|Read|Edit|Task|Worktree|TodoWrite|Glob|Grep)\b`; collect the distinct hits present; if any, append `\n\n[JARVIS-COMPAT] Denne skill nævner Claude Code-tools — oversæt: ` + `· `-joined `X → Y`); `format_context_block(result)` (return `None` unless `result.get("gate_result") == "invoked"`; else a fenced `[SKILL: <name>] (match <score>)` block wrapping `translate_cc_tools(result.get("instructions",""))`); `announcement(result)` → `(name, use_when)`.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit (in jarvis-code repo) `feat(skill-trigger): client-side skill_gate glue — query, CC-tool translation, context formatting`.

**Acceptance:** all glue is pure and unit-tested; translation is non-destructive (appends a legend, never mangles instruction prose); no-match/disabled results prepend nothing.

---

### Task 6: [CLIENT jarvis-code] Auto-call `skill_gate` on the first user turn

Bjørn's decision (spec §4.4, §11.3): the client *drives* the trigger deterministically rather than relying on the model's weaker prompt-based activation. On the first user turn of a session, call the forwarded `skill_gate` tool with `autosurface=true`, prepend the formatted context to the model input, and render the announcement. Gated by a client `skill_auto_gate` flag (default ON) — orthogonal to the server governance flag (which decides *which* skills exist to match).

**Files:**
- Modify: `/home/bs/jarvis-code/src/config.py` — `DEFAULTS` (`:42`) add `"skill_auto_gate": True`; `ENV_MAP` (`:55`) add `"JARVIS_SKILL_AUTOGATE": "skill_auto_gate"`.
- Modify: `/home/bs/jarvis-code/src/repl_ptk.py` — `__init__` (`:268` area) read `self.skill_auto_gate = bool(config.get("skill_auto_gate", True))` and `self._skill_gated = False`; `_turn_worker` (`:811`) between the convo build (`:830`) and the round loop (`:834`).
- Test: extend `tests/test_skill_trigger.py` with an orchestration helper test (keep `_turn_worker` thin by extracting the callable).

**Reimplementation note:** the auto-call reuses `tools.route_tool_call` (`src/tools.py:487`), which forwards `skill_gate` to `/v1/tools/execute` — no new transport. Client cannot import the engine; it only calls the tool.

- [ ] Step: Write failing test in `tests/test_skill_trigger.py`: `test_maybe_autosurface_calls_gate_once`. Implement against a to-be-created pure helper `skill_trigger.maybe_autosurface(route_fn, *, query, enabled)` that returns `(context_block_or_None, announcement_or_None)`. Assert: with `enabled=True` it calls `route_fn` exactly once with `("skill_gate", {"query":query, "autosurface":True})` and, given a fake `route_fn` returning an invoked result, returns a non-None context block + announcement; with `enabled=False` it does NOT call `route_fn` and returns `(None, None)`; if `route_fn` raises, it returns `(None, None)` (auto-call must never break the turn).
- [ ] Step: Run (expected FAIL): `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_skill_trigger.py -o addopts=""`.
- [ ] Step: Implement `maybe_autosurface(route_fn, *, query, enabled)` in `src/skill_trigger.py`: if not `enabled` → `(None, None)`; `try: result = route_fn("skill_gate", {"query": query, "autosurface": True})` (route_fn is a thin closure over `tools.route_tool_call`); `return (format_context_block(result), announcement(result))`; `except Exception: return (None, None)`.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Wire into `repl_ptk._turn_worker` (`:811`): in `__init__` set `self.skill_auto_gate` + `self._skill_gated = False`. In `_turn_worker`, after `convo.append({"role":"user","content":model_input})` (`:830`) and before `api_messages = list(convo)` (`:831`): guard `if self.skill_auto_gate and not self._skill_gated:` → `self._skill_gated = True`; build a closure `route = lambda n, a: tools_mod.route_tool_call(n, a, api_url=api_url, auth_token=auth, session_id=self.session_id, turn_id=turn_id)`; `ctx, ann = skill_trigger.maybe_autosurface(route, query=user_input, enabled=True)`; if `ctx`: prepend it to the model input by inserting a system-ish user-context prefix — set `model_input = ctx + "\n\n" + model_input` and rebuild the last convo entry BEFORE `api_messages = list(convo)`; if `ann`: `self._emit(render.sb_skill(ann[0], ann[1]))` (Task 7). Import `from . import skill_trigger` at module top; `tools_mod` is already imported. Use first-turn detection via `self._skill_gated` (per session) so it fires once, not every turn.
- [ ] Step: Manual verify (per `feedback_verify_visual_before_done`): run `python -m src` against a dev server with `skill_autosurface_enabled=True` + `tdd` approved, type a coding request, confirm the `▸ bruger skill: tdd` line renders and the model receives the `[SKILL: tdd]` block (check via a forwarded-tool log / the round render). Confirm with the flag OFF server-side the auto-call returns no-match and nothing is prepended (silent no-op).
- [ ] Step: Commit `feat(repl): client auto-call skill_gate on first user turn (autosurface), gated by skill_auto_gate`.

**Acceptance:** on the first turn only, the client calls `skill_gate(autosurface=true)` once; a matched skill's instructions are prepended and announced; a no-match/disabled/errored call is a silent no-op that never breaks the turn; `skill_auto_gate=false` disables the client driver entirely.

---

### Task 7: [CLIENT jarvis-code] Render "using skill X" announcement

Piece (6): the spec (§4.6, §7) requires the skill use be *visible* — otherwise the auto-call is invisible magic. Add a green scrollback line.

**Files:**
- Modify: `/home/bs/jarvis-code/src/render.py` — add `sb_skill` near `sb_sys` (`:227`), reusing `paint` + `C_GREEN`/`C_GREEN_DIM` (`:29-30`).
- Test: `/home/bs/jarvis-code/tests/test_render_skill.py` (CREATE) — or extend an existing render test if present.

**Reimplementation note:** client-only cosmetic render; no server involvement.

- [ ] Step: Write failing `tests/test_render_skill.py`: `test_sb_skill_contains_name_and_oneliner` — `render.sb_skill("tdd","writing code")` returns a string containing `tdd`, `writing code`, and the `▸` marker; `test_sb_skill_empty_oneliner` — `render.sb_skill("tdd","")` returns a string containing `tdd` and does not crash. (ANSI codes present — assert substring on the visible text, not exact bytes.)
- [ ] Step: Run (expected FAIL): `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_render_skill.py -o addopts=""`.
- [ ] Step: Implement `sb_skill(name, one_liner="")` in `src/render.py` after `:228`: `label = paint(f"▸ bruger skill: {name}", C_GREEN, bold=True)`; if `one_liner`: `label += paint(f" — {one_liner}", C_GREEN_DIM)`; `return label`.
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit `feat(render): sb_skill announcement line for auto-surfaced skills`.

**Acceptance:** the auto-surfaced skill is visible in scrollback as `▸ bruger skill: <name> — <one-liner>`; empty one-liner degrades gracefully.

---

## Acceptance (Fase 3)

1. **Engine reused, not rebuilt:** no changes to `skill_engine.py` / `skill_engine_tools.py` / `gate_skill.py`; `skill_gate` gains only a backward-compatible `autosurface` arg.
2. **Governed injection surface (flag-gated, default OFF):** with `skill_autosurface_enabled=False` the server system prompt is byte-identical to today and the client auto-call returns no-match — the entire feature is inert. Turning the flag ON and owner-approving skills is what activates it; `approve_skill`/`revoke_skill` are owner-only and validated against installed skills (ties to `project_self_registering_nerves`).
3. **Catalog present:** with the flag ON + approved skills, `/v1/agent/step`'s system prompt carries a ≤~1000-char skill catalog (name + use_when + tags), a `skill_gate`-first activation instruction, and the CC→Jarvis tool legend.
4. **Deterministic client auto-call:** on the first user turn only, the client calls `skill_gate(query=<task>, autosurface=true)` exactly once (Bjørn's decision), prepends a `[SKILL: X]` context block with CC-tool names translated non-destructively, and renders `▸ bruger skill: X`. A no-match/disabled/errored call is a silent no-op that never breaks the turn.
5. **`skill_gate` is a first-class companion:** it appears in `build_jc_catalog` so the model can also call it mid-turn.
6. **Tests green in both repos:** `/opt/conda/envs/ai/bin/python -m pytest tests/test_skill_autosurface.py tests/test_agent_loop_skill_catalog.py tests/test_skill_gate_autosurface.py tests/test_jc_tool_catalog.py -o addopts=""` (jarvis-v2) and `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_skill_trigger.py tests/test_render_skill.py -o addopts=""` (jarvis-code) all pass; visual verification per `feedback_verify_visual_before_done` done before claiming complete.