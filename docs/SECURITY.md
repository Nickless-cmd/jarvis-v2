# SECURITY

How Jarvis handles secrets, authorization, and egress. For the config schema see [`reference/CONFIG.md`](reference/CONFIG.md); for contributing safely see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Secrets

- **The only home for secrets is `~/.jarvis-v2/config/runtime.json`** (mode `0600`). They are read at runtime via `core.runtime.secrets.read_runtime_key("<key>", env_override="<ENV>")`, which prefers an env var when set.
- **Hardcoded secrets are forbidden** in the repo. A `detect-secrets` pre-commit hook blocks new secrets; a `Block jvs-* API keys` hook blocks Jarvis-issued keys.
- **False positives:** mark schema/placeholder lines by refreshing the baseline —
  ```bash
  detect-secrets scan --baseline .secrets.baseline
  detect-secrets audit .secrets.baseline
  ```
  Never commit a real value to make the hook pass.
- Run `pre-commit install` after cloning so these run on every commit.

## Authorization model

- **Roles:** `owner` / `member` / `guest`, resolved per-request via ContextVars (`effective_role`); the owner can be elevated with **TOTP**. Tool execution is scoped by role **and** by mode (chat vs code) — enforced inside `execute_tool`, not just at the prompt layer.
- **Commit gates:** every mutating tool call passes the veto gate and the decision gate (`commit_gate_arbiter`) *before* it runs. A `RED` verdict blocks; `YELLOW` warns but proceeds; `GREEN` allows.
- **Governed enforcement:** each gate has a `gate_enforce.<nerve>` kill-switch (default **on**). A `SECURITY`-class gate can **never** be disabled. Toggling is owner-only and audited.
- **Permission classifier (shadow):** predicts whether the owner would approve a mutating action, to eventually reduce approval friction. It is **subordinate to the gates** (never overrides a block), **owner-only**, and ships in shadow mode — it changes nothing until it has earned per-tool trust and the owner flips it active.

## Workspace encryption

Set `JARVISX_ENCRYPT_WORKSPACES=1` (on in production) to encrypt per-user workspace state under `~/.jarvis-v2/workspaces/`.

## Egress / privacy tiers

LLM call-sites are classified into privacy tiers (LOCAL-REQUIRED / CONTROLLED-CLOUD / PUBLIC-SAFE) so sensitive content never leaves the appropriate boundary. See [`llm_privacy_tier_audit.md`](llm_privacy_tier_audit.md). A `PRIVATE_NO_EGRESS` invariant guards the private inner-life layers from leaving the machine.

## Transport

The API binds `127.0.0.1` — it is never meant to be exposed directly. Terminate TLS at a reverse proxy (`JARVISX_HTTPS_REDIRECT=1`). See [`DEPLOYMENT.md`](DEPLOYMENT.md).

## Reporting a vulnerability

This is a personal/self-hosted system. If you run a fork and find a vulnerability, open a private security advisory on your fork's host (GitHub → Security → Report a vulnerability) or contact the maintainer directly — do not open a public issue with exploit details.
