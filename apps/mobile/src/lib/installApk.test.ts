import { downloadAndInstall } from './installApk'

it('downloadAndInstall er en funktion (importerbar + mocks loader)', () => {
  expect(typeof downloadAndInstall).toBe('function')
})

it('kalder install-intent efter download', async () => {
  const IntentLauncher = require('expo-intent-launcher')
  await downloadAndInstall(
    { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' },
    { version: '0.1.29', version_code: 30, notes: '', filename: 'a.apk' }
  )
  expect(IntentLauncher.startActivityAsync).toHaveBeenCalled()
})
