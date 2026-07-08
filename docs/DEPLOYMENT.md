# DEPLOYMENT — running Jarvis in production

For local development see [`INSTALL.md`](INSTALL.md). This covers a single-host production deployment with systemd, HTTPS, and workspace encryption.

> The unit templates below are sanitized from the **real** running units (2026-07-08). Replace `<user>`, `<repo>`, `<conda>` with your values.

## Model: two long-running services

Both run `uvicorn apps.api.jarvis_api.app:app`; they differ by `JARVIS_ENABLE_RUNTIME_SERVICES`:
- **`jarvis-api`** — the HTTP/SSE/WebSocket surface (`0`: runtime services off), bound to `127.0.0.1:8080`.
- **`jarvis-runtime`** — the runtime owner: heartbeat, schedulers, bridges (`1`: services on).

Splitting them isolates the request surface from the autonomous runtime.

## systemd units

`/etc/systemd/system/jarvis-api.service`:
```ini
[Unit]
Description=Jarvis V2 API (HTTP/SSE/WebSocket only)
After=network-online.target

[Service]
User=<user>
WorkingDirectory=<repo>
Environment=PYTHONPATH=<repo>
Environment=PYTHONUNBUFFERED=1
Environment=JARVIS_ENABLE_RUNTIME_SERVICES=0
Environment=JARVIS_VOICE_ENABLED=0
Environment=JARVISX_ENCRYPT_WORKSPACES=1
Environment=JARVISX_HTTPS_REDIRECT=1
Environment=JARVIS_AGENTIC_LEAN_PROMPT=1
Environment=JARVIS_AGENTIC_ROUND_RETRY=1
ExecStart=<conda>/bin/uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8080 --workers 1 --timeout-graceful-shutdown 30 --timeout-keep-alive 120
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/jarvis-runtime.service` — same as above, but `JARVIS_ENABLE_RUNTIME_SERVICES=1` and its own port (e.g. `--port 8011`).

Enable + start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis-api jarvis-runtime
systemctl is-active jarvis-api jarvis-runtime      # → active / active
```

## HTTPS / reverse proxy
The API binds `127.0.0.1:8080` — never expose it directly. Front it with nginx or Caddy terminating TLS and proxying to `127.0.0.1:8080`. `JARVISX_HTTPS_REDIRECT=1` makes the app assume it sits behind an HTTPS proxy.

## Workspace encryption
`JARVISX_ENCRYPT_WORKSPACES=1` encrypts the per-user workspace state under `~/.jarvis-v2/workspaces/`. Keep it on in production.

## Logs
- App logs: `~/.jarvis-v2/logs/`.
- systemd: `journalctl -u jarvis-api -f` / `journalctl -u jarvis-runtime -f`.
- Note: `logger.warning` may not reach the journal in every path — the codebase uses `print(..., flush=True)` for guaranteed-visible diagnostics.

## Upgrade flow
```bash
cd <repo>
git pull --ff-only                                  # never overwrite; MERGE if the host has local commits
git rev-parse --short HEAD                           # confirm it matches your pushed commit
sudo systemctl restart jarvis-runtime jarvis-api     # restart BOTH
systemctl is-active jarvis-runtime jarvis-api
```
`git pull | tail && restart` masks pull failures (pipe exit = tail = 0) — always guard with an explicit `if git pull --ff-only; then …`.

## The three-repo reality (why upgrades merge)
The reference setup has three checkouts: your **dev machine**, the **server** (where the units run), and **`main`** (the remote). The server can accumulate its own commits (Jarvis may write on its own working tree), so `--ff-only` can fail — **merge, never overwrite/rebase**, and re-verify `HEAD` after the pull. For a simple single-deployer setup, treat it as: develop on your machine → push to `main` → `git pull --ff-only` on the server.

See [`SECURITY.md`](SECURITY.md) for secrets, auth, and the gate model.
