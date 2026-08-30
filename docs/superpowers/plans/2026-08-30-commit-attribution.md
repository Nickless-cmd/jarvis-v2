# Commit Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every new `jarvis-v2` commit carry validated actor, run, session, origin, and approval metadata in Git trailers.

**Architecture:** A focused domain module owns the actor registry plus render/parse/validation rules. A separate commit executor writes an attributed message and invokes normal `git commit`, while versioned CLI adapters serve humans, agents, hooks, and workstation bridges. `commit-msg` validates one message; pre-push validates the pushed range after an explicit grandfather baseline. Git remains source of truth.

**Tech Stack:** Python 3.11+, `dataclasses`, `subprocess`, `git interpret-trailers`, pre-commit hook framework, pytest with real temporary Git repositories.

**Spec:** `docs/superpowers/specs/2026-08-30-commit-attribution-design.md`

## Global Constraints

- All six trailers are mandatory: `Actor`, `Actor-Type`, `Run-ID`, `Session-ID`, `Origin`, `Approved-By`.
- Initial actor ids are exactly `bjorn`, `jarvis`, `codex`, and `opus`.
- Actor types are exactly `human` and `agent`.
- Origins are exactly `manual`, `interactive`, `autonomous`, and `delegated`, restricted by the actor registry.
- Missing session is the literal `none`; missing run context gets a generated `manual-<UTC>-<suffix>` id.
- Git commit text is source of truth; DB or Mission Control may only project it.
- This is audit attribution, not cryptographic identity. Do not add signing keys or OS users.
- Commit attribution must not stage files, weaken pathspec use, or claim write ownership.
- Historical commits at or before `.commit-attribution-baseline` are grandfathered.
- Tests of Git semantics use real temporary repositories, not subprocess mocks alone.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `core/services/commit_attribution.py` | Actor registry, attribution value object, canonical trailer rendering, Git-trailer parsing, pure rule validation. |
| `core/services/attributed_git_commit.py` | Execute one attributed commit without staging or selecting unrelated paths. |
| `scripts/commit_with_attribution.py` | CLI used by Bjorn, Codex, Opus, workstation bridge, and shell-driven agents. |
| `scripts/validate_commit_attribution.py` | `commit-msg` and pre-push/range validation adapter. |
| `scripts/install_git_hooks.py` | Install and verify the three required pre-commit hook types. |
| `.commit-attribution-baseline` | Parent commit after which range enforcement applies. |
| `.pre-commit-config.yaml` | Register `commit-msg` and pre-push attribution hooks. |
| Existing commit call sites | Supply explicit actor/run/session/origin/approval context to the shared executor. |

---

### Task 1: Attribution Domain Contract

**Files:**
- Create: `core/services/commit_attribution.py`
- Create: `tests/test_commit_attribution.py`
- Regenerate: `docs/reference/DOCSTRING_COVERAGE.md`
- Regenerate: matching `docs/reference/api/core.services.*.md` chunk and index

**Interfaces:**
- Produces: `ActorRule`, `CommitAttribution`, `AttributionError`.
- Produces: `new_manual_run_id(now: datetime | None = None, suffix: str | None = None) -> str`.
- Produces: `render_attributed_message(message: str, attribution: CommitAttribution) -> str`.
- Produces: `parse_git_trailers(message: str) -> tuple[tuple[str, str], ...]`.
- Produces: `validate_trailers(trailers: Sequence[tuple[str, str]]) -> tuple[str, ...]`.
- Produces: `validate_commit_message(message: str) -> tuple[str, ...]`.

- [ ] **Step 1: Write failing registry and validation tests**

```python
from core.services.commit_attribution import (
    ACTOR_REGISTRY,
    CommitAttribution,
    new_manual_run_id,
    render_attributed_message,
    validate_commit_message,
)


def test_initial_actor_registry_is_exact():
    assert set(ACTOR_REGISTRY) == {"bjorn", "jarvis", "codex", "opus"}
    assert ACTOR_REGISTRY["bjorn"].actor_type == "human"
    assert all(ACTOR_REGISTRY[name].actor_type == "agent" for name in ("jarvis", "codex", "opus"))


def test_rendered_message_round_trips_through_validator():
    attribution = CommitAttribution(
        actor="jarvis",
        actor_type="agent",
        run_id="autonomous-abc123",
        session_id="chat-f01cf0c",
        origin="autonomous",
        approved_by="policy:auto-commit-v1",
    )
    message = render_attributed_message("fix(trainman): filtrer dreams", attribution)
    assert validate_commit_message(message) == ()
    assert message.count("Actor: jarvis") == 1


def test_duplicate_and_mismatched_trailers_are_rejected():
    message = """fix: x

Actor: bjorn
Actor: jarvis
Actor-Type: agent
Run-ID: r1
Session-ID: none
Origin: autonomous
Approved-By: bjorn
"""
    errors = validate_commit_message(message)
    assert any("Actor" in error and "exactly once" in error for error in errors)
    assert any("Actor-Type" in error or "Origin" in error for error in errors)


def test_manual_run_id_is_stable_shape_and_unique():
    first = new_manual_run_id(suffix="aaaa1111")
    second = new_manual_run_id(suffix="bbbb2222")
    assert first.startswith("manual-")
    assert first != second
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_commit_attribution.py`

Expected: collection fails because `core.services.commit_attribution` does not exist.

- [ ] **Step 3: Implement the domain model and canonical trailer contract**

Use these public shapes:

```python
@dataclass(frozen=True)
class ActorRule:
    actor_type: Literal["human", "agent"]
    origins: frozenset[str]


@dataclass(frozen=True)
class CommitAttribution:
    actor: str
    actor_type: str
    run_id: str
    session_id: str
    origin: str
    approved_by: str


ACTOR_REGISTRY = {
    "bjorn": ActorRule("human", frozenset({"manual", "interactive"})),
    "jarvis": ActorRule("agent", frozenset({"autonomous", "interactive"})),
    "codex": ActorRule("agent", frozenset({"interactive", "delegated"})),
    "opus": ActorRule("agent", frozenset({"interactive", "delegated"})),
}
```

`render_attributed_message` must remove only the six managed keys from the existing final trailer block, preserve unrelated trailers such as `Co-Authored-By`, and append the six managed trailers in the spec's order. `parse_git_trailers` must call `git interpret-trailers --parse` with the message on stdin. `validate_trailers` is the pure rule layer and returns every error rather than stopping at the first.

- [ ] **Step 4: Add edge-case tests**

Cover empty values, newline injection, unknown actors, unknown policies, origin mismatch, actor-type mismatch, duplicate managed keys, preserved `Co-Authored-By`, and deterministic replacement of old managed trailers.

- [ ] **Step 5: Run tests and regenerate API docs**

Run:

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_commit_attribution.py
/home/bs/miniconda3/envs/ai/bin/python scripts/api_docs_gen.py
git diff --check
```

Expected: attribution tests pass and docs drift reports no stale generated API page.

- [ ] **Step 6: Commit the domain contract**

```bash
git add core/services/commit_attribution.py tests/test_commit_attribution.py docs/reference
git commit -m "feat(git): define commit attribution contract"
```

This commit predates enforcement and is grandfathered by the activation baseline in Task 7.

---

### Task 2: Shared Commit Executor and CLI

**Files:**
- Create: `core/services/attributed_git_commit.py`
- Create: `scripts/commit_with_attribution.py`
- Create: `tests/test_attributed_git_commit.py`
- Regenerate: generated API docs for `core.services`

**Interfaces:**
- Consumes: `CommitAttribution`, `new_manual_run_id`, `render_attributed_message`, `validate_commit_message` from Task 1.
- Produces: `AttributedCommitResult(returncode: int, stdout: str, stderr: str, sha: str)`.
- Produces: `commit_with_attribution(*, repo: Path, message: str, attribution: CommitAttribution, paths: Sequence[str] = (), author: str = "", timeout: int = 120) -> AttributedCommitResult`.
- Produces CLI arguments: `--repo`, `--message`, `--actor`, `--run-id`, `--session-id`, `--origin`, `--approved-by`, repeatable `--path`, optional `--author`.

- [ ] **Step 1: Write a failing real-repository test**

```python
def test_commit_with_attribution_creates_only_requested_commit(git_repo):
    (git_repo / "one.py").write_text("one = 2\n")
    (git_repo / "two.py").write_text("two = 2\n")
    git(git_repo, "add", "one.py")
    result = commit_with_attribution(
        repo=git_repo,
        message="fix: update one",
        attribution=CommitAttribution(
            actor="codex", actor_type="agent", run_id="task-1",
            session_id="none", origin="delegated", approved_by="bjorn",
        ),
        paths=("one.py",),
    )
    assert result.returncode == 0
    body = git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "two.py" in git(git_repo, "status", "--short").stdout
```

The fixture must initialize a real repository, configure test user name/email, and create an initial commit.

- [ ] **Step 2: Run the test and verify RED**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_attributed_git_commit.py`

Expected: import failure for `attributed_git_commit`.

- [ ] **Step 3: Implement commit execution without staging side effects**

The executor must:

1. validate attribution before invoking Git;
2. write the canonical message to a `0600` temporary file;
3. invoke `git -C str(repo) commit -F str(message_path)`;
4. append `--author` only when explicitly supplied;
5. append `-- <paths...>` only when paths were supplied;
6. resolve `HEAD` only after return code zero;
7. always remove the temporary message file;
8. never run `git add`, `restore`, `reset`, or `push`.

- [ ] **Step 4: Implement the CLI adapter**

When `--run-id` is absent, generate it with `new_manual_run_id()`. When `--session-id` is absent, use `none`. Infer actor type from `ACTOR_REGISTRY`; do not accept actor type as a user-controlled CLI flag. Return Git's exit code and relay concise stderr without printing secrets or environment variables.

- [ ] **Step 5: Test CLI and Git special cases**

Add real-repo tests for a normal commit, a pathspec commit, `--author`, amend by replacing managed trailers, and an invalid actor returning non-zero without creating a commit.

- [ ] **Step 6: Run tests and regenerate docs**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_commit_attribution.py tests/test_attributed_git_commit.py
/home/bs/miniconda3/envs/ai/bin/python scripts/api_docs_gen.py
git diff --check
```

- [ ] **Step 7: Commit through the new wrapper**

```bash
git add core/services/attributed_git_commit.py scripts/commit_with_attribution.py tests/test_attributed_git_commit.py docs/reference
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "feat(git): add attributed commit executor"
```

Expected: the new commit already carries all six trailers.

---

### Task 3: Commit-Message and Push-Range Enforcement

**Files:**
- Create: `scripts/validate_commit_attribution.py`
- Create: `scripts/install_git_hooks.py`
- Modify: `.pre-commit-config.yaml`
- Create: `tests/test_commit_attribution_hooks.py`

**Interfaces:**
- Consumes: `validate_commit_message` from Task 1.
- Produces: `validate_message_file(path: Path) -> tuple[str, ...]`.
- Produces: `commits_in_enforced_range(repo: Path, baseline: str, from_ref: str, to_ref: str) -> tuple[str, ...]`.
- Produces CLI modes: `--message-file <path>`, `--pre-push`, and `--check-installation`.
- Uses pre-commit environment: `PRE_COMMIT_FROM_REF`, `PRE_COMMIT_TO_REF`, `PRE_COMMIT_LOCAL_BRANCH`.

- [ ] **Step 1: Write failing message-file and range tests**

```python
def test_message_file_reports_hash_independent_errors(tmp_path):
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text("fix: missing trailers\n")
    errors = validate_message_file(path)
    assert any("Actor" in error for error in errors)


def test_range_validates_only_after_baseline(git_repo):
    baseline = git(git_repo, "rev-parse", "HEAD").stdout.strip()
    unattributed = commit_raw(git_repo, "legacy after test setup")
    attributed = commit_attributed(git_repo, actor="codex")
    commits = commits_in_enforced_range(git_repo, baseline, baseline, "HEAD")
    assert commits == (unattributed, attributed)
```

Add a validator assertion that the first hash fails and the second passes. Add a divergent-history test that fails closed when baseline is not an ancestor of `to_ref`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_commit_attribution_hooks.py`

Expected: import failure for `scripts.validate_commit_attribution`.

- [ ] **Step 3: Implement hook CLI behavior**

`--message-file` reads exactly the file supplied by pre-commit. `--pre-push` reads `.commit-attribution-baseline`; while that file is absent it exits zero with `commit attribution: audit mode (no baseline)` so Tasks 3-6 can be committed. Once present, it resolves the pushed range from `PRE_COMMIT_FROM_REF` and `PRE_COMMIT_TO_REF`; for a new branch, resolve `PRE_COMMIT_LOCAL_BRANCH`. Validate the intersection of pushed commits and `baseline..to_ref`, in oldest-first order. Print one block per bad hash and exit one if any fail.

- [ ] **Step 4: Register versioned hooks**

Extend the install types:

```yaml
default_install_hook_types: [pre-commit, commit-msg, pre-push]
```

Add these local hooks:

```yaml
- id: commit-attribution-message
  name: Require commit attribution trailers
  entry: /opt/conda/envs/ai/bin/python scripts/validate_commit_attribution.py --message-file
  language: system
  stages: [commit-msg]

- id: commit-attribution-range
  name: Validate pushed commit attribution range
  entry: /opt/conda/envs/ai/bin/python scripts/validate_commit_attribution.py --pre-push
  language: system
  pass_filenames: false
  always_run: true
  stages: [pre-push]
```

The message hook receives the commit message filename as its positional argument after `--message-file`.

- [ ] **Step 5: Implement installation verification**

`scripts/install_git_hooks.py` supports `--check`. Normal mode runs:

```bash
/opt/conda/envs/ai/bin/python -m pre_commit install \
  --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Check mode resolves `git rev-parse --git-path hooks/<type>`, verifies all three files exist and are executable, and verifies the generated pre-commit marker. It must report each missing hook separately.

- [ ] **Step 6: Exercise bypass and special-history cases in real repos**

Tests must prove:

- a valid merge commit passes;
- revert, cherry-pick, and amend pass after wrapper rewriting;
- `git commit --no-verify` creates an invalid commit but `--pre-push` rejects its hash;
- commits at/before baseline are skipped;
- missing baseline is audit mode, not accidental enforcement;
- installed hook check distinguishes a plain file from an active executable pre-commit hook.

- [ ] **Step 7: Run hook tests**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_commit_attribution.py \
  tests/test_attributed_git_commit.py \
  tests/test_commit_attribution_hooks.py
git diff --check
```

- [ ] **Step 8: Commit enforcement in audit mode**

```bash
git add .pre-commit-config.yaml scripts/validate_commit_attribution.py scripts/install_git_hooks.py tests/test_commit_attribution_hooks.py
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "feat(git): validate commit attribution hooks"
```

Do not create `.commit-attribution-baseline` yet.

---

### Task 4: Jarvis Autonomous Commit Call Sites

**Files:**
- Modify: `core/services/run_closure_gate.py:297-380`
- Modify: `core/services/autonomy_proposal_queue.py:150-245,408-550`
- Modify: `tests/test_run_closure_gate.py`
- Create: `tests/test_autonomy_proposal_commit_attribution.py`
- Regenerate: generated API docs for `core.services`

**Interfaces:**
- Consumes: `commit_with_attribution` and `CommitAttribution` from Tasks 1-2.
- Run-closure attribution: actor `jarvis`, origin `autonomous`, approval `policy:auto-commit-v1`.
- Approved proposal attribution: actor `jarvis`, approval `bjorn`, run id from proposal or proposal id, session id from proposal or `none`.

- [ ] **Step 1: Replace mocked Git success with attribution assertions in closure tests**

Patch `commit_with_attribution`, call `_try_auto_commit`, and assert:

```python
attribution = mocked.call_args.kwargs["attribution"]
assert attribution.actor == "jarvis"
assert attribution.run_id == "rid-1"
assert attribution.session_id == "sid-1"
assert attribution.origin == "autonomous"
assert attribution.approved_by == "policy:auto-commit-v1"
assert mocked.call_args.kwargs["paths"] == ("core/services/run_closure_gate.py",)
```

Keep existing tests for clean baseline, staged changes, deletion, and pathspec isolation.

- [ ] **Step 2: Run the closure test and verify RED**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest -q tests/test_run_closure_gate.py`

Expected: `_try_auto_commit` still invokes raw `git commit` and never calls the shared executor.

- [ ] **Step 3: Migrate run closure**

Keep its existing `git add`, staging verification, candidate filtering, failure restore, nudge, and event behavior. Replace only the raw commit subprocess with `commit_with_attribution`. Convert `AttributedCommitResult` into the existing error and short-hash flow. Do not loosen its clean-baseline gate or remove pathspecs.

- [ ] **Step 4: Preserve proposal context through execution**

Before calling a registered executor, copy the payload and add a reserved `_proposal_context` object:

```python
execution_payload["_proposal_context"] = {
    "proposal_id": proposal_id,
    "run_id": str(proposal.get("run_id") or ""),
    "session_id": str(proposal.get("session_id") or ""),
    "approved_by": "bjorn",
}
```

Built-in executors ignore unknown keys except the commit executor, which consumes and removes this object. Do not change the public executor callable signature.

- [ ] **Step 5: Add proposal attribution tests and migrate both proposal commits**

Test `_auto_commit_after_source_edit` and `_execute_git_commit_proposal` separately. Both must call the shared executor with actor `jarvis`, origin `autonomous`, approval `bjorn`, actual session when available, and `run_id or proposal_id`. Preserve their existing staging, event publication, nothing-to-commit handling, and explicit `Jarvis <jarvis@srvlab.dk>` author.

- [ ] **Step 6: Run autonomous commit tests and regenerate docs**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_run_closure_gate.py \
  tests/test_autonomy_proposal_commit_attribution.py
/home/bs/miniconda3/envs/ai/bin/python scripts/api_docs_gen.py
git diff --check
```

- [ ] **Step 7: Commit autonomous integration**

```bash
git add core/services/run_closure_gate.py core/services/autonomy_proposal_queue.py tests/test_run_closure_gate.py tests/test_autonomy_proposal_commit_attribution.py docs/reference
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "refactor(git): attribute Jarvis autonomous commits"
```

---

### Task 5: Human-Initiated API and Code-Mode Commits

**Files:**
- Modify: `apps/api/jarvis_api/routes/system_health.py:78-110`
- Modify: `apps/api/jarvis_api/routes/chat.py:285-335,373-390`
- Modify: `core/services/git_actions.py`
- Modify: `tests/test_chat_file.py`
- Modify: `tests/test_git_actions.py`
- Create: `tests/test_system_git_commit.py`
- Regenerate: generated API docs for changed packages

**Interfaces:**
- Consumes: shared executor for container-side commits.
- Consumes: `scripts/commit_with_attribution.py` for workstation bridge commits.
- Human button/API attribution: actor `bjorn`, type `human`, origin `interactive`, approval `bjorn`, generated manual run id, session `none` unless route context supplies one.

- [ ] **Step 1: Write failing API and service assertions**

Update real-repo tests to inspect `%B`, not only `%s`:

```python
body = git(repo, "log", "-1", "--pretty=%B").stdout
assert "Actor: bjorn" in body
assert "Actor-Type: human" in body
assert "Origin: interactive" in body
assert "Approved-By: bjorn" in body
```

In `test_git_actions.py`, assert container commit calls the shared executor and workstation command contains `scripts/commit_with_attribution.py --actor bjorn` rather than raw `git commit`.

- [ ] **Step 2: Run targeted tests and verify RED**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_chat_file.py tests/test_git_actions.py tests/test_system_git_commit.py
```

Expected: raw commit call sites produce no trailers.

- [ ] **Step 3: Migrate container API commits**

Replace raw commit subprocesses in `system_git_commit` and `_commit_file_sync` with the shared executor. Keep existing add strategy and path jail. The route action itself is the human approval, so use `Approved-By: bjorn`; do not infer actor from Git config or user display name.

- [ ] **Step 4: Migrate `git_actions` container and workstation paths**

For container operations, use the shared Python executor. For workstation operations, build a shell-safe command with `shlex.join` targeting `Path(root) / "scripts/commit_with_attribution.py"`. Pass actor `bjorn`, origin `interactive`, approval `bjorn`, and message. `create_pr` must use the same path before push. Preserve bridge uid routing and existing result shapes.

- [ ] **Step 5: Run tests and regenerate docs**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_chat_file.py tests/test_git_actions.py tests/test_system_git_commit.py
/home/bs/miniconda3/envs/ai/bin/python scripts/api_docs_gen.py
git diff --check
```

- [ ] **Step 6: Commit human/API integration**

```bash
git add apps/api/jarvis_api/routes/system_health.py apps/api/jarvis_api/routes/chat.py core/services/git_actions.py tests/test_chat_file.py tests/test_git_actions.py tests/test_system_git_commit.py docs/reference
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "refactor(git): attribute human initiated commits"
```

---

### Task 6: Codex, Opus, and Shell Guidance

**Files:**
- Modify: `core/tools/claude_dispatch/runner.py:20-55`
- Modify: `core/tools/simple_tools_enforcement.py:55-135`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Create: `tests/test_claude_dispatch_commit_attribution.py`
- Create: `tests/test_simple_tools_enforcement.py`

**Interfaces:**
- Claude-dispatch actor: `opus`, origin `delegated`, run id `task_id`, session `none`, approval `policy:claude-dispatch-v1`.
- Codex instruction actor: `codex`; Opus instruction actor: `opus`; interactive work is approved by `bjorn`.

- [ ] **Step 1: Write failing delegated-agent prompt tests**

```python
def test_claude_dispatch_prompt_requires_attributed_wrapper():
    prompt = _build_prompt(spec, task_id="task-abc123")
    assert "scripts/commit_with_attribution.py" in prompt
    assert "--actor opus" in prompt
    assert "--run-id task-abc123" in prompt
    assert "git add -A && git commit" not in prompt
```

Add a simple-tools test proving a successful command containing `commit_with_attribution.py` resets the per-session edit counter exactly like legacy `git commit`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_claude_dispatch_commit_attribution.py \
  tests/test_simple_tools_enforcement.py
```

`tests/test_simple_tools_enforcement.py` is the single focused coverage module for this extracted service; no existing test imports it directly.

- [ ] **Step 3: Pass task identity into Claude dispatch**

Change `_build_prompt(spec: TaskSpec, task_id: str) -> str`, call it after `_new_task_id()`, and derive a deterministic subject with `commit_subject = f"feat(worker): {spec.goal.strip()[:58]}"`. Render that subject shell-safely with `shlex.quote(commit_subject)` while instructing the worker to stage only scoped paths plus invoke:

```bash
python scripts/commit_with_attribution.py \
  --repo . --actor opus --run-id task-abc123 --session-id none \
  --origin delegated --approved-by policy:claude-dispatch-v1 \
  --message 'feat(worker): inspect bounded cache regression'
```

The code example shows the rendered output for a goal named `inspect bounded cache regression`; production substitutes the actual task id and subject derived from `spec.goal`. Remove the existing `git add -A && git commit` instruction because it violates both scope and attribution.

- [ ] **Step 4: Update commit-success detection and repository guidance**

Teach `_is_successful_git_commit` to recognize either raw `git commit` or `commit_with_attribution.py`, while retaining its existing exit/output guards. Add a `Commit attribution` section to both `AGENTS.md` and `CLAUDE.md` with exact commands for their actor. State that raw `git commit`, `--no-verify`, and hand-written trailers are not the normal path.

- [ ] **Step 5: Run delegated-agent and guidance checks**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_claude_dispatch_commit_attribution.py \
  tests/test_simple_tools_enforcement.py
rg -n "commit_with_attribution.py|--actor (codex|opus)" AGENTS.md CLAUDE.md core/tools/claude_dispatch/runner.py
git diff --check
```

- [ ] **Step 6: Commit agent integration**

```bash
git add core/tools/claude_dispatch/runner.py core/tools/simple_tools_enforcement.py AGENTS.md CLAUDE.md tests/test_claude_dispatch_commit_attribution.py tests/test_simple_tools_enforcement.py
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "docs(git): route agents through attributed commits"
```

---

### Task 7: Activation, Real-Git Acceptance, and Deployment

**Files:**
- Create: `.commit-attribution-baseline`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/CONTRIBUTING.md`
- Create: `tests/acceptance/test_commit_attribution_e2e.py`

**Interfaces:**
- Consumes all prior tasks.
- Produces the one-time baseline parent hash and installed active hooks.

- [ ] **Step 1: Add end-to-end acceptance tests**

The test creates a real temporary repository containing the scripts/config required for hooks, then proves:

1. wrapper commits from `bjorn`, `jarvis`, `codex`, and `opus` all validate;
2. raw unattributed commit is rejected by `commit-msg` after installation;
3. `--no-verify` can create one locally but pre-push range validation rejects it;
4. a valid merge commit and amended commit validate;
5. commits before baseline are not checked.

- [ ] **Step 2: Run full attribution and affected-call-site suite**

```bash
/home/bs/miniconda3/envs/ai/bin/python -m pytest -q \
  tests/test_commit_attribution.py \
  tests/test_attributed_git_commit.py \
  tests/test_commit_attribution_hooks.py \
  tests/test_run_closure_gate.py \
  tests/test_autonomy_proposal_commit_attribution.py \
  tests/test_chat_file.py \
  tests/test_git_actions.py \
  tests/test_system_git_commit.py \
  tests/test_claude_dispatch_commit_attribution.py \
  tests/test_simple_tools_enforcement.py \
  tests/acceptance/test_commit_attribution_e2e.py
/home/bs/miniconda3/envs/ai/bin/python -m compileall core apps/api scripts
git diff --check
```

Expected: zero failures and compileall exit zero.

- [ ] **Step 3: Record the grandfather baseline**

Record the current pre-activation HEAD, with no whitespace:

```bash
git rev-parse HEAD > .commit-attribution-baseline
test "$(wc -l < .commit-attribution-baseline)" -eq 1
git cat-file -e "$(cat .commit-attribution-baseline)^{commit}"
```

Update contributor and agent docs to state that every later commit is enforced and that hook installation is:

```bash
/home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py
/home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py --check
```

- [ ] **Step 4: Create the activation commit with attribution**

```bash
git add .commit-attribution-baseline AGENTS.md CLAUDE.md docs/CONTRIBUTING.md tests/acceptance/test_commit_attribution_e2e.py
/home/bs/miniconda3/envs/ai/bin/python scripts/commit_with_attribution.py \
  --repo . --actor codex --origin delegated --approved-by bjorn \
  --message "feat(git): enforce commit attribution"
```

Verify the activation commit is exactly one commit after the baseline and validates:

```bash
test "$(git rev-parse HEAD^)" = "$(cat .commit-attribution-baseline)"
/home/bs/miniconda3/envs/ai/bin/python scripts/validate_commit_attribution.py --message-file <(git show -s --format=%B HEAD)
```

If process substitution is unsupported by the validator's path handling, write `git show -s --format=%B HEAD` to a temporary file and pass that file.

- [ ] **Step 5: Install and verify hooks locally**

```bash
/home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py
/home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py --check
PRE_COMMIT_FROM_REF="$(cat .commit-attribution-baseline)" \
PRE_COMMIT_TO_REF="$(git rev-parse HEAD)" \
  /home/bs/miniconda3/envs/ai/bin/python scripts/validate_commit_attribution.py --pre-push
```

- [ ] **Step 6: Push and deploy with hash verification**

```bash
git push origin main
ssh -i ~/.ssh/id_ed25519 bs@10.0.0.39 '
  cd /media/projects/jarvis-v2 &&
  git pull --ff-only &&
  /home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py &&
  /home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py --check &&
  sudo systemctl restart jarvis-api
'
```

Then verify local, origin, and remote hashes match; service start is after the activation commit; `/health` on port 8080 returns 200.

- [ ] **Step 7: Run four-actor canary in disposable repositories**

Use the CLI to create one commit per actor in fresh temporary repositories, then run `validate_commit_message` over `%B`. Do not create four noise commits on `main`. Report actor, run id, origin, and validation result without printing unrelated environment state.

- [ ] **Step 8: Final audit**

```bash
git status --short --branch
git log -5 --format='%h%n%B%n---'
/home/bs/miniconda3/envs/ai/bin/python scripts/install_git_hooks.py --check
```

Expected: clean working tree; every commit after baseline carries six valid trailers; hooks active; local/origin/remote HEAD equal; API health 200.
