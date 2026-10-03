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

/**
 * Miljøfeltet og de tre ruder deler ÉN højre-stak (3/10-2026).
 *
 * Bjørn: «så skal de 3 paneler kunne vises under miljøfeltet .. som det er nu og
 * jeg trykker et af dem frem så forsvinder miljøfeltet». Før havde hver rude en
 * vagt der skjulte feltet (`envOpen && !jobsOpen && !changesOpen && …`), så de
 * to aldrig stod sammen. Testen er på KILDEN fordi den handler om rækkefølgen i
 * JSX'en — hvad der ligger inde i hvilken beholder — og det kan en DOM-test i
 * jsdom ikke se, da feltet ikke lader sig åbne programmatisk der.
 */
describe('miljøfeltet og ruderne deler én stak (3/10-2026)', () => {
  it('CodeView tegner miljøfeltet ØVERST inde i den fælles stak', () => {
    const kilde = (p: string) => readFileSync(resolve(__dirname, p), 'utf8')
    const k = kilde('../views/CodeView.tsx')
    // Rækkefølgen ER ærindet: greb → miljøfelt → ændrings-ruden.
    const greb = k.indexOf('{!fuldRude && <SkinneGreb />}')
    const miljoe = k.indexOf('<EnvironmentPanel')
    const aendring = k.indexOf("{changesOpen && (!fuldRude || fuldRude === 'changes')")
    expect(greb, 'trækgrebet blev ikke fundet').toBeGreaterThan(-1)
    expect(miljoe, 'miljøfeltet blev ikke fundet i CodeView').toBeGreaterThan(greb)
    expect(aendring, 'ændrings-ruden blev ikke fundet').toBeGreaterThan(miljoe)
  })

  it('ruden skjuler IKKE længere miljøfeltet — den stakker under', () => {
    const kilde = (p: string) => readFileSync(resolve(__dirname, p), 'utf8')
    const k = kilde('../views/CodeView.tsx')
    // Den gamle vagt, ordret. Kommer den tilbage, forsvinder feltet igen i
    // samme øjeblik man åbner en rude.
    expect(k).not.toMatch(/envOpen\s*&&\s*!jobsOpen/)
    expect(k).toContain('const stackAaben = miljoeVises || skinneAaben')
    // Én stak — ikke en `.code-right-stack` for feltet ved siden af.
    expect((k.match(/className="code-right-stack"/g) ?? []).length).toBe(0)
  })
})
