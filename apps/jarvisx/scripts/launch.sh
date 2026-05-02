#!/usr/bin/env bash
# Launcher for the installed JarvisX desktop entry.
#
# Resolves the repo root from this script's own location, ensures the
# renderer + electron main are built (incremental — only rebuilds if
# missing), and execs Electron in production mode.
#
# Why exec at the end: replaces this shell process with Electron so
# the desktop's "running app" entry tracks the real PID, not a wrapper.
set -euo pipefail

# Resolve repo root: this script lives at apps/jarvisx/scripts/launch.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARVISX_DIR="$(dirname "$SCRIPT_DIR")"

cd "$JARVISX_DIR"

# Ensure node_modules is in place — first launch after a fresh clone
# should not require the user to know about npm install.
if [[ ! -d node_modules ]]; then
  echo "[jarvisx] first launch — installing deps…"
  npm install --silent
fi

# Ensure the renderer + electron main are built. dist/ for Vite output,
# dist-electron/ for the compiled main.js / preload.cjs.
if [[ ! -f dist/index.html ]] || [[ ! -f dist-electron/main.js ]]; then
  echo "[jarvisx] build artifacts missing — running npm run build…"
  npm run build
fi

# Hand off to Electron. NODE_ENV unset → main.ts skips the dev-only
# devtools auto-open and serves the packaged dist/ instead of vite.
exec npx electron . "$@"
