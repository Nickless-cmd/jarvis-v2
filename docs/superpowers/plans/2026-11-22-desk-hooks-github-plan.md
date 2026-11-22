# Desk Hooks and GitHub Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make shell-hook state/logging/sandbox coverage and GitHub PR state/actions visible in Desk without adding an execution surface.

**Architecture:** Add thin FastAPI adapters over `tool_shell_hooks` and the existing GitHub tool handlers, then consume them from a settings component and the existing code-mode Git panel. Propagate bash confinement from the execution result into the existing hook observer payload and rotate the JSONL log synchronously at 10 MB with one retained generation.

**Tech Stack:** FastAPI/Pydantic, React/TypeScript, pytest, Vitest/Testing Library.

**Spec:** Assignment `asg-18cebb2e3ad74d85` (2026-11-22).

## Global Constraints

- Preserve hook exit semantics, stdin argument transport, environment allowlist, and fail-open bash behavior.
- Do not expose a hook dry-run or arbitrary shell execution route.
- Do not commit, push, or deploy.

## Review Focus

- Missing/malformed JSONL lines are skipped without breaking the log endpoint.
- Sandbox counts use the decision emitted by bash, never infer it later.
- Rotation preserves one prior generation and reports its presence.
- GitHub reads call existing tool handlers and PR creation returns an approval request before execution.
- Disabled/missing hook config is conspicuous in Desk.

### Task 1: Hook API, log metadata, and rotation

**Files:** `tests/test_tool_hooks_api.py`, `tests/test_tool_shell_hooks.py`, `apps/api/jarvis_api/routes/tool_hooks.py`, `core/services/tool_shell_hooks.py`, `core/tools/simple_tools_web.py`, `apps/api/jarvis_api/app.py`.

- [ ] Write failing route/rotation/confinement tests and run them.
- [ ] Implement status, reload and structured log endpoints plus 10 MB/one-generation rotation.
- [ ] Forward bash result confinement into after-hook metadata and verify tests pass.

### Task 2: Hooks settings surface

**Files:** `apps/jarvis-desk/src/components/settings/HooksSection.test.tsx`, `HooksSection.tsx`, `apps/jarvis-desk/src/lib/toolHooksApi.ts`, `apps/jarvis-desk/src/views/CoworkView.tsx`.

- [ ] Write a failing component behavior test and run it.
- [ ] Implement hook list/reload/log/coverage UI and mount it under Systemstatus.
- [ ] Verify component tests pass.

### Task 3: Direct GitHub API and existing Git panel extension

**Files:** `tests/test_tool_hooks_api.py`, `apps/api/jarvis_api/routes/github.py`, `core/tools/github_pr_tools.py`, `apps/api/jarvis_api/app.py`, `apps/jarvis-desk/src/lib/gitPr.ts`, `apps/jarvis-desk/src/components/panel/GitPanel.tsx`.

- [ ] Write failing API tests for open PRs, CI, and approval-gated creation.
- [ ] Add handler wrappers and thin routes; extend the existing Git tab with open PRs and their CI.
- [ ] Verify focused tests, then run the assignment's full Python and frontend commands.

