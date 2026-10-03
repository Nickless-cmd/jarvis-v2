import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * `artifact`, `plan` og `pr` er RIGTIGE paneler ved samtalen (3/10-2026).
 *
 * De tre stod i `IKKE_I_DESK` med statiske afvisninger — «Desk har intet
 * plan-panel» og to mere. Bjørn: «desk har artefakter og vist osse de andre..
 * eller skal den have det». Han havde ret: `ArtifactsView`, `PlansPane` og
 * git-status-kilden fandtes hele tiden. Afvisningen var en påstand om desk,
 * ikke om data — og den var forkert.
 *
 * Testen laaser at de bliver ved med at vaere aabne i BEGGE flader: en
 * afvisning er let at genindfoere, og den er usynlig naar den foerst staar der.
 */
const kilde = (p: string) => readFileSync(resolve(__dirname, p), 'utf8')

const FLADER = ['../views/ChatView.tsx', '../views/CodeView.tsx']

// Den FULDE vis-gren — ikke bare `p === 'plan'`. Den korte form matcher ogsaa
// `luk()`-grenen nedenfor, og saa bestaar testen selv naar vis-grenen fjernes.
// Maalt 3/10-2026: foerste udgave gjorde praecis det og maalte ingenting.
const VIS_GREN: Record<string, string> = {
  artifact: "if (p === 'artifact') { setArtifactsOpen(true); return null }",
  plan: "if (p === 'plan') { setPlansOpen(true); return null }",
  pr: "if (p === 'pr') { setPrOpen(true); return null }",
}

describe('artifact, plan og pr som paneler ved samtalen', () => {
  it('afvisnings-tabellen findes ikke laengere', () => {
    expect(kilde('../lib/skaermRegister.ts')).not.toMatch(/IKKE_I_DESK/)
  })

  it('begge flader aabner alle tre gennem vis()', () => {
    for (const v of FLADER) {
      const k = kilde(v)
      for (const [p, gren] of Object.entries(VIS_GREN)) {
        expect(k, `${v} mangler vis-gren for ${p}`).toContain(gren)
      }
    }
  })

  it('begge flader lukker dem igen', () => {
    for (const v of FLADER) {
      const k = kilde(v)
      for (const s of ['setArtifactsOpen(false)', 'setPlansOpen(false)', 'setPrOpen(false)']) {
        expect(k, `${v} mangler ${s}`).toContain(s)
      }
    }
  })

  it('de tre komponenter genbruger de eksisterende visninger — ingen anden sandhed', () => {
    expect(kilde('../components/panel/ArtifactsPanel.tsx')).toContain('ArtifactsView')
    expect(kilde('../components/panel/PlansPanel.tsx')).toContain('PlansPane')
    expect(kilde('../components/panel/PrPanel.tsx')).toContain('getGitStatus')
  })
})
