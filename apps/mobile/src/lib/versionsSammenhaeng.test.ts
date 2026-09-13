/**
 * `app.json` og `build.gradle` skal sige det samme.
 *
 * Målt 13/9-2026: de gjorde de ikke. Projektet er prebuild-ejected, så
 * `android/app/build.gradle` er den ENESTE kilde APK'en bygges fra — `app.json`
 * fodrer ikke det native build. Jeg bumpede app.json til 0.2.65/166, byggede,
 * udgav, og APK'en indeholdt stadig 0.2.63/164.
 *
 * Følgen var ikke en byggefejl. Alt så rigtigt ud: bundlen HAVDE den nye kode,
 * udgivelsen efterprøvede filstørrelsen og sagde god for den, og telefonen
 * installerede den uden brok. Men `versionCode` stod stille, så appen blev ved
 * med at tilbyde den opdatering den lige havde taget — to gange.
 *
 * En størrelses-kontrol svarer på «kom filen frem», ikke på «er det den version
 * vi tror». Den her test svarer på det andet.
 */
import { readFileSync } from 'fs'
import { join } from 'path'

const ROD = join(__dirname, '..', '..')

function gradle() {
  const t = readFileSync(join(ROD, 'android', 'app', 'build.gradle'), 'utf8')
  const kode = /\n\s*versionCode\s+(\d+)/.exec(t)
  const navn = /\n\s*versionName\s+"([^"]+)"/.exec(t)
  return { versionCode: kode ? Number(kode[1]) : null, versionName: navn ? navn[1] : null }
}

function appJson() {
  const j = JSON.parse(readFileSync(join(ROD, 'app.json'), 'utf8'))
  return { versionCode: j.expo?.android?.versionCode ?? null, versionName: j.expo?.version ?? null }
}

function pkg() {
  return JSON.parse(readFileSync(join(ROD, 'package.json'), 'utf8')).version ?? null
}

it('build.gradle har overhovedet et versions-nummer at laese', () => {
  const g = gradle()
  expect(g.versionCode).not.toBeNull()
  expect(g.versionName).not.toBeNull()
})

it('app.json og build.gradle er ENIGE om versionCode', () => {
  // build.gradle vinder i praksis — det er den APK'en bygges fra. app.json er
  // det menneskene laeser. Er de uenige, lyver den ene, og det opdages foerst
  // naar en telefon bliver ved med at tilbyde en opdatering den har taget.
  expect(gradle().versionCode).toBe(appJson().versionCode)
})

it('app.json og build.gradle er ENIGE om versionName', () => {
  expect(gradle().versionName).toBe(appJson().versionName)
})

it('package.json foelger med', () => {
  expect(pkg()).toBe(appJson().versionName)
})
