import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Windows auto-update læser `latest.yml` fra release'en og henter den fil
 * `path:` peger på. GitHub OMDOEBER ved upload: alt uden for [A-Za-z0-9._-]
 * bliver til et punktum. Maalt 11/11-2026: electron-builder skrev
 * `J.A.R.V.I.S-Setup-0.6.335.exe` i latest.yml, mens asset'en landede som
 * `J.A.R.V.I.S.Setup.0.6.335.exe` — den ene gav 404, den anden 302.
 *
 * Aarsagen er at `productName` er `J.A.R.V.I.S.` (slutter med punktum), saa
 * electron-builder's eget navn indeholder tegn GitHub ikke bevarer. En
 * eksplicit `artifactName` uden om de tegn tager begge sider samme vej.
 */

const SAFE = /^[A-Za-z0-9._-]+$/

function build(): Record<string, unknown> {
  const sti = join(__dirname, '..', 'package.json')
  return JSON.parse(readFileSync(sti, 'utf8')).build ?? {}
}

describe('Windows-artefaktets navn', () => {
  it('er sat eksplicit — ellers normaliserer electron-builder det ud fra productName', () => {
    const win = (build().win ?? {}) as Record<string, unknown>
    expect(win.artifactName).toBeTruthy()
  })

  it('indeholder kun tegn GitHub bevarer ved upload', () => {
    const win = (build().win ?? {}) as Record<string, unknown>
    const skabelon = String(win.artifactName ?? '')
    // Substituér de pladsholdere electron-builder selv fylder ud.
    const udfyldt = skabelon.replace(/\$\{version\}/g, '0.0.0').replace(/\$\{ext\}/g, 'exe')
    expect(udfyldt).toMatch(SAFE)
  })

  it('matcher den form latest.yml peger paa — punktummer i productName maa ikke lække ind', () => {
    const win = (build().win ?? {}) as Record<string, unknown>
    const udfyldt = String(win.artifactName ?? '')
      .replace(/\$\{version\}/g, '0.0.0')
      .replace(/\$\{ext\}/g, 'exe')
    expect(udfyldt).toBe('J.A.R.V.I.S-Setup-0.0.0.exe')
  })
})
