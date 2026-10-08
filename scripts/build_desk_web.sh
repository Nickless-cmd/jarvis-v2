#!/usr/bin/env bash
# Build the web renderer from the same source as the Electron app.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/apps/jarvis-desk"
npm ci
npm run build:web
