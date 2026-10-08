# Member chat storage encryption

## Goal

For every authenticated non-owner, message text and text derived from it must be encrypted with that user's existing data key before durable storage. This applies to the Desk PWA as well as every other client of the same API. TLS protects transport; this design concerns storage. The server must still process plaintext in memory to answer a turn.

## Current state, measured 2026-10-08

The production `chat_messages` table has 1,230 rows in seven member sessions; all 1,230 have `encrypted=1`. The last 23 member rows also have the `enc:v1:` prefix. No member session currently has a `session_events` row. All seven member session titles are readable in `chat_sessions.title`. The ledger write path currently stores message payloads as plaintext JSON and would expose future member sessions. Desk's web build stores composer drafts and up to 200 sent messages in browser `localStorage` as plaintext.

## Storage boundary

- Keep `core.services.chat_crypto` and each user's existing DEK as the sole encryption scheme. Keep owner content unchanged.
- Encrypt member `chat_sessions.title` on every write that can contain user text: first-message title, explicit creation, rename, and generated placeholder replacement. Decrypt only for authorized session reads. A placeholder such as `New chat` may remain unencrypted until ownership is known.
- Encrypt the text-bearing fields of member `session_events` message payloads before the JSON row is inserted. On internal reads, decrypt in memory before projection. Determine the user from an explicit registered member ID or the existing session's owner. An authenticated non-owner whose key cannot be resolved must get a write error, never a plaintext fallback.
- Encrypt member text previews in durable run/work projections with the same key and decrypt for authorized reads. No new plaintext preview of a member message may be persisted.
- Browser PWA must not persist non-owner composer drafts or sent-message history in `localStorage`. On authenticated member startup, remove existing plaintext keys. In-memory text may remain while the page is open. Shell assets may still be cached by the service worker; authenticated API responses must not be cached.

## Read, search, and migration

Session lists and individual session reads decrypt titles and the latest-message preview in memory after user scoping. Search for member conversations must match decrypted titles/content within the requesting user's scoped sessions; SQL `LIKE` cannot match ciphertext. Preserve existing owner search behavior.

Migrate existing member titles in small, idempotent batches using the session's registered member key. Never change an unknown or mixed-owner session by guessing. A dry run reports counts, not text. Read compatibility accepts existing plaintext titles until migration is complete; write paths only create ciphertext for known members.

## Verification and rollout

Tests inspect raw SQLite values after authenticated member writes, including title, ledger payload, and preview fields, and verify the member can read the original text. They cover owner compatibility, unknown users failing closed, renamed sessions, search, and old plaintext migration. Browser tests inspect `localStorage` after typing and sending as a member. A production read-only audit counts ciphertext and plaintext without printing private content. Roll out the server change before the PWA change, then migrate existing titles, deploy the PWA, and repeat the audit.
