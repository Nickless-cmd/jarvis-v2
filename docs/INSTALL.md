# INSTALL — from an empty machine to a running Jarvis

This gets Jarvis running **locally**. For production (systemd, HTTPS, encryption) see [`DEPLOYMENT.md`](DEPLOYMENT.md). For the config schema see [`reference/CONFIG.md`](reference/CONFIG.md).

> Verified against `pyproject.toml`, the live route set, and the real systemd units (2026-07-08). Where a step depends on your host, it says so.

## Prerequisites
- **Python 3.11+** (`requires-python = ">=3.11"`).
- **conda / miniconda** (the reference deployment uses a conda env named `ai`).
- **git**.
- *Optional:* **Ollama** if you want a local visible-model instead of a cloud provider.

## 1. Clone + environment
```bash
git clone <your-fork-or-repo-url> jarvis-v2
cd jarvis-v2
conda create -n ai python=3.11 -y
conda activate ai
pip install -e .                 # packaging deps from pyproject.toml
pip install -r requirements.txt  # the full curated runtime deps (see the file header)
pre-commit install               # secret-scan + coverage + kitchen-sink gates
```
The code runs from the repo with `PYTHONPATH=$PWD` (as the production units do); `pip install -e .` also makes `core`/`apps` importable.

## 2. Configure
Runtime state (DB, logs, sessions, workspaces) lives in `~/.jarvis-v2/` — **not** in the repo. Create the config file and lock it down:
```bash
mkdir -p ~/.jarvis-v2/config && chmod 700 ~/.jarvis-v2/config
touch ~/.jarvis-v2/config/runtime.json && chmod 600 ~/.jarvis-v2/config/runtime.json
```
Populate `runtime.json` from [`reference/CONFIG.md`](reference/CONFIG.md).

**Required vs optional:** Jarvis boots with just a **visible-model provider** configured (a cloud provider key, or a local Ollama with no key). Mail, channels (Telegram/Discord), and infra keys are all optional — add them only when you enable that feature.

## 3. First boot
The DB and the `~/.jarvis-v2/` state directories auto-create on first run. *(Verify on your host — if the state dir doesn't appear, check permissions on `~/.jarvis-v2/`.)*

## 4. Run
Two processes, both `uvicorn apps.api.jarvis_api.app:app`, distinguished by one env var:

**A. The API (chat + Mission Control) — minimal, gets chat working:**
```bash
PYTHONPATH=$PWD JARVIS_ENABLE_RUNTIME_SERVICES=0 JARVIS_VOICE_ENABLED=0 \
  uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8080
```

**B. The runtime owner (heartbeat, schedulers, bridges) — add for autonomy:**
```bash
PYTHONPATH=$PWD JARVIS_ENABLE_RUNTIME_SERVICES=1 JARVIS_VOICE_ENABLED=0 \
  uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8011
```
Run A alone for a chat-only Jarvis; run both (different ports) for the full runtime. In production these are two systemd units — see [`DEPLOYMENT.md`](DEPLOYMENT.md).

## 5. Verify
```bash
curl http://127.0.0.1:8080/health          # → {"ok": true, ...}
```
The full route list is in [`reference/API_REFERENCE.md`](reference/API_REFERENCE.md).

## 6. First interaction
```bash
python scripts/jarvis.py                    # the jc CLI
```

## Troubleshooting
- `ModuleNotFoundError` on boot → a dependency is missing; re-run `pip install -r requirements.txt`, and see the "optional" section in that file for feature-specific extras.
- Nothing at `/health` → the API didn't bind; check the uvicorn output and that port 8080 is free.
- Secrets not picked up → confirm `~/.jarvis-v2/config/runtime.json` is valid JSON and `chmod 600`.
