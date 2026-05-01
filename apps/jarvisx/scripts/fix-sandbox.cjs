#!/usr/bin/env node
/**
 * Postinstall: ensure Electron's chrome-sandbox is SUID root on Linux.
 *
 * On Linux, Electron requires `chrome-sandbox` to be owned by root with
 * mode 4755 — otherwise it aborts with a SUID sandbox error. npm install
 * resets ownership to the install user, so we need to redo the chmod
 * after every install.
 *
 * We try sudo silently; if it fails (no passwordless sudo, CI without
 * root, etc.) we print the manual command and exit 0 so install doesn't
 * break. macOS/Windows skip this entirely.
 */
'use strict'

const { execSync } = require('node:child_process')
const { existsSync, statSync } = require('node:fs')
const { join } = require('node:path')

if (process.platform !== 'linux') {
  process.exit(0)
}

const sandbox = join(__dirname, '..', 'node_modules', 'electron', 'dist', 'chrome-sandbox')

if (!existsSync(sandbox)) {
  // Electron not (yet) installed — nothing to do. Will rerun if needed.
  process.exit(0)
}

// Already SUID root?
try {
  const st = statSync(sandbox)
  const isRoot = st.uid === 0
  const hasSuid = (st.mode & 0o4000) !== 0
  if (isRoot && hasSuid) {
    process.exit(0)
  }
} catch {
  // Fall through to fix attempt
}

const cmd = `sudo -n chown root:root "${sandbox}" && sudo -n chmod 4755 "${sandbox}"`

try {
  execSync(cmd, { stdio: 'pipe' })
  console.log('[jarvisx] chrome-sandbox SUID fixed')
} catch {
  // sudo prompted or failed — leave it to the user.
  console.warn(
    '\n[jarvisx] chrome-sandbox needs SUID. Run once manually:\n' +
      `  sudo chown root:root "${sandbox}"\n` +
      `  sudo chmod 4755 "${sandbox}"\n`,
  )
}
