// electron-builder afterPack hook — ensure the Linux chrome-sandbox helper is
// setuid-root (mode 4755). Without it, on Ubuntu 24.04 (where the unprivileged
// user-namespace sandbox is mandatory via apparmor_restrict_unprivileged_userns=1)
// Electron aborts BEFORE showing a window:
//   FATAL setuid_sandbox_host.cc: "The SUID sandbox helper binary was found, but
//   is not configured correctly ... owned by root and has mode 4755"
// = the app silently "won't start". The mode is recorded in the packed output, so
// the generated .deb installs chrome-sandbox as root:root 4755 and the sandbox works.
// (2026-07-23 — a build lost this bit and jarvis-desk stopped opening on ChiefOne.)
const fs = require("fs");
const path = require("path");

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== "linux") return;
  const sandbox = path.join(context.appOutDir, "chrome-sandbox");
  try {
    fs.chmodSync(sandbox, 0o4755);
    console.log(`[afterPack] chrome-sandbox set to mode 4755 (setuid): ${sandbox}`);
  } catch (err) {
    console.warn(`[afterPack] could not chmod chrome-sandbox (${err.message}) — the app may not launch on Ubuntu 24.04 until you run: sudo chmod 4755 <install>/chrome-sandbox`);
  }
};
