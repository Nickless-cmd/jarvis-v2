# Docs SP3 — Install / Setup Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let someone else stand up their own Jarvis — a curated dependency manifest + fresh, fact-verified INSTALL / DEPLOYMENT / SECURITY / CONTRIBUTING / CONFIG docs.

**Architecture:** One new buildable piece (`requirements_gen.py` import scanner → a curated `requirements.txt` that fixes the "6-deps-but-needs-100" gap) + five hand-written prose docs, each grounded in verified facts (pyproject, real systemd units, grep of `read_runtime_key`). No runtime code; a link-check + config cross-check is the gate.

**Tech Stack:** Python 3.11 (stdlib AST), pytest, prose. `conda activate ai`.

**Execution note:** Task 1 (import scanner + test) → fresh **haiku** subagent. Tasks 2–8 (curate requirements, write the 5 docs, README links, verify) → **Claude inline** (facts held in context).

---

## Task 1: `scripts/requirements_gen.py` + tests

**Files:**
- Create: `scripts/requirements_gen.py`
- Test: `tests/test_requirements_gen.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_requirements_gen.py
import ast, importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "requirements_gen", Path(__file__).resolve().parents[1] / "scripts" / "requirements_gen.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)


def test_top_level_imports_extracts_roots():
    tree = ast.parse("import fastapi\nfrom pydantic import BaseModel\nimport os.path\n")
    mods = rg.top_level_imports(tree)
    assert "fastapi" in mods and "pydantic" in mods and "os" in mods


def test_top_level_imports_ignores_relative():
    tree = ast.parse("from . import x\nfrom ..core import y\n")
    assert rg.top_level_imports(tree) == set()


def test_third_party_filters_stdlib_and_first_party():
    mods = {"os", "sys", "json", "core", "apps", "scripts", "fastapi", "torch"}
    tp = rg.third_party(mods)
    assert "fastapi" in tp and "torch" in tp
    assert "os" not in tp and "core" not in tp and "json" not in tp
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_requirements_gen.py -q`
Expected: FAIL — module not defined.

- [ ] **Step 3: Write the implementation**

```python
# scripts/requirements_gen.py
"""Scan core/+apps/+scripts for THIRD-PARTY top-level imports (filter stdlib + first-party).
Emits a candidate module list to stdout — curated by hand into requirements.txt (import→PyPI
mapping happens in curation). Stdlib only. Static (AST), no imports of the scanned code."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["core", "apps", "scripts"]
FIRST_PARTY = {"core", "apps", "scripts"}


def top_level_imports(tree: ast.AST) -> set[str]:
    """Root module names of ABSOLUTE imports in one parsed file (relative imports ignored)."""
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name:
                    mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def scan(repo: Path = REPO) -> set[str]:
    found: set[str] = set()
    for d in SCAN_DIRS:
        for p in (repo / d).rglob("*.py"):
            try:
                found |= top_level_imports(ast.parse(p.read_text(errors="ignore")))
            except Exception:
                pass
    return found


def third_party(mods: set[str]) -> list[str]:
    std = set(getattr(sys, "stdlib_module_names", set()))
    return sorted(m for m in mods
                  if m and m not in std and m not in FIRST_PARTY and not m.startswith("_"))


def main() -> int:
    cands = third_party(scan())
    for m in cands:
        print(m)
    print(f"# {len(cands)} third-party top-level modules", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_requirements_gen.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/requirements_gen.py tests/test_requirements_gen.py
git commit -m "feat(docs): SP3 third-party import scanner (for requirements.txt)"
```

---

## Task 2 (Claude inline): curate `requirements.txt`

- [ ] **Step 1: Get the candidate imports**

Run: `conda run -n ai python scripts/requirements_gen.py`
This prints the third-party top-level module names actually imported across core/apps/scripts.

- [ ] **Step 2: Curate + verify → `requirements.txt`**

For each candidate, map the import name to its PyPI package name where they differ (known cases: `yaml`→`PyYAML`, `PIL`→`Pillow`, `cv2`→`opencv-python`, `bs4`→`beautifulsoup4`, `dateutil`→`python-dateutil`, `dotenv`→`python-dotenv`, `discord`→`discord.py`, `telegram`→`python-telegram-bot`, `jwt`→`PyJWT`, `sklearn`→`scikit-learn`). Drop obvious non-packages (e.g. a mistaken local module). **Verify each stays real:** `conda run -n ai python -c "import <name>"` succeeds (the module is present in the working env — proof it's a real dependency). Write a clean, grouped, comment-annotated `requirements.txt` at repo root (core web, data/ML, channels, media/voice, infra/misc), unpinned or with `>=` floors matching `pyproject.toml` where it overlaps. Add a header: `# Curated from scripts/requirements_gen.py (imports actually used) — regenerate the candidate list with that script.`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat(docs): SP3 curated requirements.txt (real deps — fixes the 6-vs-100 gap)"
```

---

## Task 3 (Claude inline): `docs/reference/CONFIG.md`

- [ ] **Step 1: Derive the real key list**

Run: `grep -rhoE "read_runtime_key\(\s*[\"'][a-z_]+[\"']" core/ apps/ scripts/ | grep -oE "[\"'][a-z_]+[\"']" | tr -d "\"'" | sort -u`
This is the authoritative set of `runtime.json` keys (currently 28).

- [ ] **Step 2: Write `docs/reference/CONFIG.md`**

Document every key: purpose (from its call-site context), a **placeholder** value, and its `env_override` if any. Group: **Providers** (huggingface_token, elevenlabs_api_key, stripe_secret_key, kling_access_key/secret_key, pollinations_api_key, piapi_key, arko_api_key/base_url/cheap_agent_id), **Mail** (mail_smtp_host/imap_host/user/password), **Channels/integrations** (telegram_bot_token, home_assistant_token, google_calendar_credentials), **Infra** (pfsense_api_key, pihole_api_password), **Auth/crypto** (jarvisx_auth_secret, control_arm_salt, user_email_pepper), **Models/layers** (vision_model_name, dictation_whisper_model, layer_*). Header: file is `~/.jarvis-v2/config/runtime.json`, must be `chmod 0600`, secrets ONLY here (never in code), read via `core.runtime.secrets.read_runtime_key`. **Placeholders only — no real values.** Footer: `Re-derive the key list: <the grep above>`.

- [ ] **Step 3: Commit** — `git add docs/reference/CONFIG.md && git commit -m "docs(docs): SP3 runtime.json config schema reference (28 keys, placeholders only)"`

---

## Task 4 (Claude inline): `docs/INSTALL.md`

- [ ] **Step 1: Verify the dep-install command** — confirm `pip install -e .` works given `pyproject.toml` ([project]+setuptools present) AND note that `requirements.txt` (Task 2) covers the extras pyproject omits. The documented flow: `pip install -e .` then `pip install -r requirements.txt` (or just the latter + PYTHONPATH). Confirm `scripts/jarvis.py` is the CLI entry.

- [ ] **Step 2: Write `docs/INSTALL.md`** (getting-started) with these verified sections:
  - **Prerequisites:** Python 3.11+, conda/miniconda, git; optional Ollama for a local visible-model.
  - **Clone + env:** clone; `conda create -n ai python=3.11`; `conda activate ai`; `pip install -e .` + `pip install -r requirements.txt`; `pre-commit install`.
  - **Config:** create `~/.jarvis-v2/config/runtime.json` (`mkdir -p`, `chmod 0600`) from [`reference/CONFIG.md`](reference/CONFIG.md). **Required-vs-optional:** it boots with just a visible-model provider configured; mail/channels/infra keys are optional.
  - **First boot:** the DB + state dirs under `~/.jarvis-v2/` auto-create on first run (flag honestly: "verify on your host").
  - **Run the two processes locally** (from the repo, `PYTHONPATH=$PWD`):
    - API: `JARVIS_ENABLE_RUNTIME_SERVICES=0 JARVIS_VOICE_ENABLED=0 uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8080`
    - Runtime owner (heartbeat/schedulers): the runtime process with services ON (document the exact env — mirror the systemd `jarvis-runtime` unit).
  - **Verify:** `curl http://127.0.0.1:8080/health`.
  - **First chat:** `python scripts/jarvis.py`.
  - Link to `DEPLOYMENT.md` for production.

- [ ] **Step 3: Commit** — `git add docs/INSTALL.md && git commit -m "docs(docs): SP3 INSTALL guide (empty machine → running Jarvis, verified)"`

---

## Task 5 (Claude inline): `docs/DEPLOYMENT.md`

- [ ] **Step 1: Write `docs/DEPLOYMENT.md`** (operations), grounded in the real systemd units:
  - The **two systemd unit templates**, sanitized (placeholders for `<user>`, `<repo>`, `<conda>`): `User=`, `WorkingDirectory=<repo>`, `ExecStart=<conda>/bin/uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8080 --workers 1 --timeout-graceful-shutdown 30 --timeout-keep-alive 120`, and the real env: `PYTHONPATH=<repo>`, `PYTHONUNBUFFERED=1`, `JARVISX_ENCRYPT_WORKSPACES=1`, `JARVISX_HTTPS_REDIRECT=1`, `JARVIS_AGENTIC_LEAN_PROMPT=1`, `JARVIS_AGENTIC_ROUND_RETRY=1`; the runtime unit adds services ON.
  - Reverse-proxy + HTTPS (the API binds 127.0.0.1:8080; front it with nginx/caddy; `JARVISX_HTTPS_REDIRECT`).
  - Workspace encryption (`JARVISX_ENCRYPT_WORKSPACES=1`).
  - Logs (`~/.jarvis-v2/logs/`, `journalctl -u jarvis-*`).
  - **Upgrade flow:** `git pull --ff-only` then `sudo systemctl restart jarvis-runtime jarvis-api` (restart BOTH); verify HEAD after pull.
  - The 3-repo model (local dev / target host / main) abstracted to "your dev machine → your server".

- [ ] **Step 2: Commit** — `git add docs/DEPLOYMENT.md && git commit -m "docs(docs): SP3 DEPLOYMENT (systemd templates + upgrade flow, from real units)"`

---

## Task 6 (Claude inline): `docs/SECURITY.md`

- [ ] **Step 1: Write `docs/SECURITY.md`** (fresh):
  - **Secrets:** only in `~/.jarvis-v2/config/runtime.json` (`0600`), read via `core.runtime.secrets.read_runtime_key` — never hardcoded (a pre-commit `detect-secrets` hook + `.secrets.baseline` enforce this; document the false-positive workflow: `detect-secrets scan --baseline .secrets.baseline`).
  - **Auth model:** owner/member/guest roles + TOTP; the commit gates (veto + decision via `commit_gate_arbiter`) run before mutating tools; `gate_enforce.<nerve>` kill-switches (default on; SECURITY class never disable-able); the permission-classifier (shadow) predicts owner-approval.
  - **Workspace encryption:** `JARVISX_ENCRYPT_WORKSPACES=1`.
  - **Egress / privacy tiers:** → [`llm_privacy_tier_audit.md`](llm_privacy_tier_audit.md) (LOCAL-REQUIRED / CONTROLLED-CLOUD / PUBLIC-SAFE).
  - **Reporting a vulnerability:** how/where.

- [ ] **Step 2: Commit** — `git add docs/SECURITY.md && git commit -m "docs(docs): SP3 fresh SECURITY (secrets/auth/gates/egress)"`

---

## Task 7 (Claude inline): `docs/CONTRIBUTING.md`

- [ ] **Step 1: Write `docs/CONTRIBUTING.md`** (fresh):
  - **Dev setup:** the `ai` env (link INSTALL); run tests: `conda run -n ai python -m pytest -q` (full-suite gate ~20min: `-p no:cacheprovider --timeout=45 --timeout-method=signal`).
  - **Pre-commit gates** (all 4): detect-secrets, coverage (every new `core/…` file needs `tests/test_<stem>.py`), block kitchen-sink commits, block jvs-* keys. `pre-commit install`.
  - **Code rules** (from `CLAUDE.md`): no file >1500 lines (split at 1200), no core file >2000, one responsibility per file, no hidden side effects, no dual truth (config vs DB), risky actions need a policy/approval path.
  - **Boy-Scout rule:** touching a >2000-line file → first extract the nearest natural unit (re-export for back-compat) before your change.
  - **Commits/PRs:** the `Co-Authored-By` trailer convention; branch off `main`; commit/push only when asked.

- [ ] **Step 2: Commit** — `git add docs/CONTRIBUTING.md && git commit -m "docs(docs): SP3 fresh CONTRIBUTING (tests/gates/code-rules/boy-scout)"`

---

## Task 8 (Claude inline): README links + verify gate

- [ ] **Step 1: Update `docs/README.md`** — replace the "install guide coming (SP3)" placeholder with real links: Getting started → `INSTALL.md`; Operations → `DEPLOYMENT.md`; add a Security & contributing group → `SECURITY.md`, `CONTRIBUTING.md`, `reference/CONFIG.md`; note `requirements.txt` at repo root.

- [ ] **Step 2: Link-check + config cross-check**

Verify every relative link in the 5 new docs + README resolves (extract `](...)` targets, resolve relative to each doc's dir, assert exists). Then cross-check `reference/CONFIG.md` documents exactly the keys the grep yields (no key documented that isn't referenced; flag any referenced key missing from the doc). Fix mismatches.

- [ ] **Step 3: Generator/scanner tests + compile**

Run: `conda run -n ai python -m pytest tests/test_requirements_gen.py -q && conda run -n ai python -m compileall scripts/requirements_gen.py -q`
Expected: PASS.

- [ ] **Step 4: Commit + push**

```bash
git add -A docs/ && git commit -m "docs(docs): SP3 README links + link/config cross-check"
git push
```
No container deploy (repo-docs + one `scripts/` scanner with a test). Full-suite gate not required (no runtime code); the link-check + config cross-check + scanner test are the gate.

- [ ] **Step 5: Report** to Bjørn (the requirements.txt count, the 5 docs, any step flagged unverifiable) and note SP4 (per-file/function reference, workflow-scale) is the next sub-project.

---

## Self-Review

**Spec coverage:** dependency-manifest finding → `requirements_gen.py` + curated `requirements.txt` (Tasks 1–2) ✓; CONFIG.md 28 grep-derived keys, placeholders only (Task 3) ✓; INSTALL empty→running with the two verified process profiles + required/optional note (Task 4) ✓; DEPLOYMENT systemd templates from real units + upgrade flow (Task 5) ✓; fresh SECURITY (secrets/auth/gates/egress) (Task 6) ✓; fresh CONTRIBUTING (tests/gates/code-rules/boy-scout) (Task 7) ✓; README links + link-check + config cross-check (Task 8) ✓; fact-verification discipline (each task verifies against pyproject/systemd/grep; unverifiable flagged) ✓; no secret leak (CONFIG placeholders) ✓.

**Placeholder scan:** none in the *plan* — the prose docs' content is specified section-by-section with the exact verified facts to include (written at execution, the appropriate granularity for a docs plan); the only literal placeholders are the intentional `<user>/<repo>/<conda>` in the systemd templates and the CONFIG value placeholders (both required by the spec).

**Type consistency:** `top_level_imports(tree)→set`, `scan(repo)→set`, `third_party(mods)→list` in the scanner match the tests. Doc paths (`docs/reference/CONFIG.md`, `docs/INSTALL.md`, etc.) consistent across tasks and the README-links task.
