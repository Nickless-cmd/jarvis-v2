# Docs Programme SP3 — Install / Setup Guide

**Date:** 2026-07-08
**Status:** Approved (design)
**Programme:** Prod-ready docs/. SP1 (audit) `7c1e85f6` + SP2 (structure+generators) `34dce785` LANDED. This is SP3. Then SP4 per-file/function reference → SP5 drift-sikring.

## Goal

Make it possible for **someone else** to stand up their own Jarvis. SP1 archived `DEPLOYMENT.md` (droppet), `SECURITY.md` + `CONTRIBUTING.md` (forældet) as stale — SP3 rewrites them **fresh, from verified reality**, and adds a config-schema reference so a newcomer can go from an empty machine to a running Jarvis and contribute safely.

## Ground truth (verified 2026-07-08)

- `pyproject.toml`: `requires-python = ">=3.11"`, ~8 top-level dependencies.
- Two processes, both `uvicorn apps.api.jarvis_api.app:app`, differentiated by env:
  - **jarvis-api** — `--host 127.0.0.1 --port 8080 --workers 1`, `JARVIS_ENABLE_RUNTIME_SERVICES=0`, `JARVIS_VOICE_ENABLED=0`.
  - **jarvis-runtime** — runtime owner (heartbeat/schedulers/bridges), services ON.
  - Shared env (real, from the systemd units): `PYTHONPATH=<repo>`, `PYTHONUNBUFFERED=1`, `JARVISX_ENCRYPT_WORKSPACES=1`, `JARVISX_HTTPS_REDIRECT=1`, `JARVIS_AGENTIC_LEAN_PROMPT=1`, `JARVIS_AGENTIC_ROUND_RETRY=1`. `User=bs`, `WorkingDirectory=<repo>`, conda env `ai`.
- Runtime state lives in `~/.jarvis-v2/` (`config/`, `state/`, `logs/`, `cache/`, `sessions/`, `auth/`, `workspaces/`) — the code repo is not the runtime home.
- Config: `~/.jarvis-v2/config/runtime.json`; **28 distinct keys** referenced via `core.runtime.secrets.read_runtime_key("<key>", env_override=...)` (grep-derivable) — providers (`huggingface_token`, `elevenlabs_api_key`, `stripe_secret_key`, `kling_*`, `pollinations_api_key`, `piapi_key`, `arko_*`), mail (`mail_smtp_host/imap_host/user/password`), channels (`telegram_bot_token`, `home_assistant_token`, `google_calendar_credentials`), infra (`pfsense_api_key`, `pihole_api_password`), auth/crypto (`jarvisx_auth_secret`, `control_arm_salt`, `user_email_pepper`), models/layers. `runtime.json` must be `0600`.
- CLI: `scripts/jarvis.py`. Pre-commit hooks: detect-secrets, coverage (core/→tests/), kitchen-sink, jvs-keys — need `pre-commit install`.
- Source material: `docs/_archive/{DEPLOYMENT,SECURITY,CONTRIBUTING}.md` (stale, but structural starting points).

## Deliverables (in the SP2 information architecture)

1. **`docs/INSTALL.md`** (getting-started) — empty machine → running Jarvis, locally:
   prerequisites (Python 3.11, conda/miniconda, git; optional Ollama for a local model) → clone → create the `ai` conda env + install the `pyproject.toml` dependencies into it → the code runs via `PYTHONPATH=<repo>` (as the systemd units do), not as an installed package — the plan verifies the exact dep-install command at write-time (`pip install` of the deps list vs `pip install -e .`) → `pre-commit install` → create `~/.jarvis-v2/config/runtime.json` from the schema (→ `reference/CONFIG.md`) → first boot auto-creates the DB/state dirs → run the two processes locally (exact `uvicorn` commands + the two env profiles) → verify (`curl http://127.0.0.1:8080/health`) → first chat via `python scripts/jarvis.py`. Honest "minimal viable" note: which keys are *required* to boot vs optional (a Jarvis boots with just a visible-model provider key; channels/mail/infra keys are optional).
2. **`docs/DEPLOYMENT.md`** (operations) — production on a single host: the two **systemd unit templates** (sanitized from the real ones — placeholders for User/paths), reverse-proxy + HTTPS (`JARVISX_HTTPS_REDIRECT`), workspace encryption (`JARVISX_ENCRYPT_WORKSPACES`), log locations, the upgrade flow (`git pull --ff-only` + `systemctl restart` both), and the 3-repo model (local / target-host / main) abstracted for a single deployer.
3. **`docs/SECURITY.md`** (fresh) — secrets model (only `runtime.json` via `read_runtime_key`, `0600`, never hardcoded), the detect-secrets hook + `.secrets.baseline` workflow, the auth model (owner/member/guest roles, TOTP, the commit/veto/decision gates + `gate_enforce` kill-switches), workspace encryption, egress/privacy tiers (→ `llm_privacy_tier_audit.md`), how to report a vuln.
4. **`docs/CONTRIBUTING.md`** (fresh) — dev workflow: env setup, run tests (`conda run -n ai python -m pytest`), the four pre-commit gates, the coverage rule (new `core/…` file ⇒ `tests/test_<stem>.py`), the Boy-Scout rule (>2000-line files), the code rules (no file >1500 lines, one responsibility, no dual truth config/DB), commit trailer + PR conventions.
5. **`docs/reference/CONFIG.md`** — the `runtime.json` schema: the 28 real keys (grep-derived from `read_runtime_key` call-sites, so the list can't be invented or drift), each with purpose + a **placeholder** value + its `env_override`, grouped. **Schema/placeholders only — zero real secrets.** A one-line "regenerate the key list: `grep -rhoE ...`" note keeps it honest for SP5.

## Verification discipline

Every concrete claim is **fact-verified against reality**, not asserted:
- deps ← `pyproject.toml`; run-commands + env ← the real systemd units; config keys ← grep of `read_runtime_key`; entry points ← `scripts/jarvis.py` + the uvicorn target; the app imports cleanly (already confirmed in SP2 via `api_reference_gen`).
- **NOT** a fresh-env throwaway boot — that would touch the local `~/.jarvis-v2` runtime state (risk). Any step that cannot be confirmed from facts is **flagged explicitly** in the doc (e.g. "the DB auto-initializes on first boot — verify on your host").
- Final link-check: every relative link in the 5 docs resolves; the CONFIG.md key list is cross-checked against a fresh grep.

## Files

- **New:** `docs/INSTALL.md`, `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, `docs/CONTRIBUTING.md`, `docs/reference/CONFIG.md`.
- **Update:** `docs/README.md` — link the new getting-started/operations/security docs (the "install guide coming (SP3)" placeholder becomes real links).
- No runtime code, no generators, no container deploy. Prose grounded in verified facts.

## Scope boundary

SP3 = how to install/run/secure/contribute. It does NOT document per-file/function internals (SP4) or build a docs-drift checker (SP5). It reuses SP2's generated reference (`API_REFERENCE`, `CAPABILITIES`) rather than duplicating it.

## Deploy

Repo-docs only. Full-suite gate not required (no code) — but a link-check + config-key cross-check gate the correctness. Lands on `main`; container picks up docs on next ordinary pull.
