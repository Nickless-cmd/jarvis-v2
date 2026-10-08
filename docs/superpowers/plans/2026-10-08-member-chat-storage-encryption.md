# Member Chat Storage Encryption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Encrypt member message-derived text before every durable server or PWA write, while preserving authorized reads.

**Architecture:** Extend the existing per-user `chat_crypto` boundary to session metadata, ledger payloads, and run previews. PWA member drafts and sent-message history remain in memory only. Migrate existing titles after deploying backward-compatible readers.

**Tech Stack:** Python 3.11, SQLite, FastAPI, React/TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-10-08-member-chat-storage-encryption-design.md`

## Global Constraints

- Keep the existing per-user DEK and `enc:v1:` format.
- Do not modify owner data or encrypt an unknown session using a guessed key.
- Do not print private text in tests, migration logs, or production audits.
- Preserve both legacy and ledger session modes.
- Stage and commit intended paths with `scripts/commit_with_attribution.py`.

## Review Focus

- A member's first message has no prior session rows: resolve its registered user ID before storing a title or ledger event.
- A message row tagged `default` within a known member session inherits that session's key.
- A failed key lookup during an authenticated member write never falls back to plaintext.
- An old plaintext title remains readable until the idempotent migration encrypts it.
- PWA logout/login across accounts does not revive another account's local draft or history.

---

### Task 1: Session metadata encryption

**Files:** `core/services/chat_crypto.py`, `core/services/chat_session_private_metadata.py` (new), `core/services/chat_sessions.py`, `tests/test_chat_crypto.py`.

**Interfaces:** `encrypt_session_text(text: str, session_id: str, *, user_id: str = "", workspace_name: str = "") -> str` and `decrypt_session_text(text: str, session_id: str) -> str`.

- [ ] Add a failing SQLite test that writes a member's first message and asserts `chat_sessions.title` excludes its literal text and begins `enc:v1:`; assert list/get return the plaintext title.
- [ ] Run that single test and confirm failure on raw title.
- [ ] Add the smallest helper and wire first-message, create, rename, and read paths. Preserve owner/placeholder behavior.
- [ ] Run the focused test, then all chat session and crypto tests.
- [ ] Add a failing scoped member-search test; make search decrypt candidate titles and messages in memory, then verify owner search remains unchanged.

### Task 2: Ledger payload encryption

**Files:** `core/runtime/db_session_ledger.py`, `core/services/ledger_write_path.py`, `core/services/shadow_ledger_writer.py`, `tests/test_db_session_ledger.py`.

**Interfaces:** `protect_member_message_event(session_id: str, event: dict) -> dict` at both append boundaries; `read_session_events` returns in-memory decrypted payloads for projection.

- [ ] Write a failing test that creates a registered member ledger session, appends a message, inspects raw `session_events.payload_json`, and asserts no literal content appears.
- [ ] Run the test and confirm it fails on the raw payload.
- [ ] Protect message payload text fields before both owned and shadow inserts; decrypt on internal reads so projection remains unchanged.
- [ ] Add a test where an authenticated non-owner key is missing and assert the append fails without a row.
- [ ] Run ledger/projection tests and verify raw SQLite storage plus reconstructed chat.

### Task 3: Durable preview encryption

**Files:** `core/runtime/db_visible.py`, `core/services/visible_runs_outcomes.py`, their existing focused tests.

**Interfaces:** Run preview writes use the same member key; scoped read helpers decrypt before returning.

- [ ] Write a failing test that stores a member run preview and inspects raw `visible_work_notes`, `visible_work_units`, and `visible_runs` text fields.
- [ ] Run the test and confirm plaintext is present before the fix.
- [ ] Encrypt member preview fields at each write boundary and decrypt only in user-scoped reads.
- [ ] Run visible-work and cross-session-continuity tests.

### Task 4: PWA local text retention

**Files:** `apps/jarvis-desk/src/components/shell/Composer.tsx`, `apps/jarvis-desk/src/hooks/usePersistedState.ts`, `apps/jarvis-desk/src/contexts/SettingsContext.tsx`, their focused tests.

**Interfaces:** Member web composer text/history remains in component memory; persisted member keys are deleted after `whoami` confirms a non-owner. Electron and owner preferences remain unchanged.

- [ ] Write failing web-mode tests that type/send as a member and assert no draft/history value exists in `localStorage`; test cleanup of legacy keys on login.
- [ ] Run the tests and confirm the plaintext values are present before the fix.
- [ ] Make persistence optional for the composer and clear existing member web keys after authentication.
- [ ] Run the full Desk suite and `npm run build:web`.

### Task 5: Migration, audit, and rollout

**Files:** `scripts/migrate_member_session_titles.py` (new), tests for that script, deployment notes.

**Interfaces:** `--dry-run` reports counts only; normal run encrypts known member titles idempotently and skips unknown/mixed sessions.

- [ ] Write failing migration tests with member, owner, unknown, and already-encrypted titles.
- [ ] Implement bounded transaction batches and test a second run makes zero changes.
- [ ] Run Python compile and relevant/full tests, the production dry run, and a read-only row-count audit.
- [ ] Commit through attribution wrapper, deploy server, run migration, deploy web build, and repeat the ciphertext audit without printing message text.
