/**
 * macOS notarization hook for electron-builder.
 *
 * Invoked automatically by electron-builder after the .app is signed
 * but before the .dmg is built. Submits the .app to Apple's notary
 * service and staples the result. Without notarization, macOS users
 * see the dreaded "JarvisX cannot be opened because the developer
 * cannot be verified" Gatekeeper dialog.
 *
 * No-op when:
 *   - We're not on macOS (Linux/Windows builds skip this stage)
 *   - The required env vars are missing — local dev / unsigned builds
 *     should NOT try to notarize and fail noisily.
 *
 * Required env vars (set in CI / your shell before running
 * `npm run package`):
 *   APPLE_ID           — Apple ID email
 *   APPLE_APP_SPECIFIC_PASSWORD  — app-specific password
 *                                  (generated at appleid.apple.com)
 *   APPLE_TEAM_ID      — your Developer Program team ID
 *
 * See apps/jarvisx/README.md → "Code signing" section for the full
 * setup walkthrough.
 */
exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir, packager } = context
  if (electronPlatformName !== 'darwin') {
    return
  }
  const required = [
    'APPLE_ID',
    'APPLE_APP_SPECIFIC_PASSWORD',
    'APPLE_TEAM_ID',
  ]
  const missing = required.filter((v) => !process.env[v])
  if (missing.length > 0) {
    console.warn(
      `[notarize] skipping — missing env vars: ${missing.join(', ')}. ` +
        `This is fine for unsigned local builds; release builds for ` +
        `distribution must set all of: ${required.join(', ')}.`,
    )
    return
  }

  let notarize
  try {
    notarize = require('@electron/notarize').notarize
  } catch (e) {
    console.error(
      '[notarize] @electron/notarize is not installed. Run ' +
        '`npm install --save-dev @electron/notarize` before publishing.',
    )
    throw e
  }

  const appName = packager.appInfo.productFilename
  console.log(`[notarize] submitting ${appName}.app to Apple…`)
  await notarize({
    appPath: `${appOutDir}/${appName}.app`,
    appleId: process.env.APPLE_ID,
    appleIdPassword: process.env.APPLE_APP_SPECIFIC_PASSWORD,
    teamId: process.env.APPLE_TEAM_ID,
  })
  console.log('[notarize] success.')
}
