# Desk: five finishing passes

**Approval:** Bjørn requested all five passes on 2026-09-21. Execute sequentially in this task.
**Goal:** Truthful settings states, readable categories, an introduction, consistent presentation and a current backlog.
**Architecture:** Reuse current API contracts and category navigation. Add a small guarded resource hook and shared feedback. No new backend truth or permissions.
**Stack:** React, TypeScript, CSS, Vitest; browser inspection with deterministic fixtures.

## 1. Truthful states
- [ ] Add `useSettingsResource.ts` with retry, missing-config state and stale-response protection.
- [ ] Add `SettingsState.tsx`; migrate MCP, workbench, memory, apps, account, quota and workspace reads.
- [ ] Catch mutation failures, keep entered values, disable ambiguous actions while state is unavailable. Test failed MCP trust, failed workbench reads, retry and account/session changes.

## 2. Category content
- [ ] Present memory as saved notes, user information and recent observations. Keep source documents behind details; do not invent memory-edit endpoints.
- [ ] Translate common account/app status labels, explain technical controls, label inputs and show save failures.

## 3. Introduction
- [ ] Explain Chat, Code, Arbejde and first actions after the existing AI notice; allow dismissal and reopening in Om og hjælp.
- [ ] Avoid competing first-run dialogs; persist completion and support keyboard focus and Escape.
- [ ] Test completion, reopening and navigation.

## 4. Visual audit
- [ ] Review all ten category destinations and their shared styling; fix field sizing, contrast, wrapping, focus and narrow-window behavior in scoped styles.
- [ ] Inspect representative populated, empty, loading and error states in a browser. Record actual coverage and limitations.
- [ ] Run renderer/Electron build and relevant tests; only expand tests for concrete regressions.

## 5. Backlog
- [ ] Replace stale STUBS.md claims with verified current status and real remaining work, with source references.
- [ ] Keep unfinished backend features distinct from completed UI work. Record verification and commit in focused groups through attribution wrapper.
