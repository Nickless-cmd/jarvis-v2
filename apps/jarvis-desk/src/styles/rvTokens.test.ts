import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Raekkevisningens tre afstands-tokens (punkt 7 i Codex-speccen, 29/9-2026).
 *
 * Opgaven var oprindelig «saml ALLE afstande i tokens». Maalt foerst: 1.608
 * afstands-deklarationer, 37 unikke px-vaerdier, og hvert heltal fra 1 til 14
 * i brug. Et token pr. tal er en omdoebning, ikke et system — og at snappe til
 * en skala ville flytte 843 deklarationer synligt. Derfor kun de tre hvor det
 * SAMME tal staar for det SAMME.
 *
 * Det vigtigste testen bevogter er at INTET tal flyttede sig. En «oprydning»
 * der aendrer udseendet er ikke en oprydning.
 */

const css = () => readFileSync(join(__dirname, 'raekkevisning.css'), 'utf8')
const uden = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, '')

const AFSTAND = /(?<![\w-])(gap|row-gap|column-gap|padding|padding-top|padding-right|padding-bottom|padding-left|margin|margin-top|margin-right|margin-bottom|margin-left|left|right)\s*:\s*([^;}]+)/g

/** Hvad hver afstands-deklaration faktisk indeholder, talt op. */
function tael(kilde: string): Record<string, number> {
  const ud: Record<string, number> = {}
  for (const m of uden(kilde).matchAll(AFSTAND)) {
    for (const px of (m[2] ?? '').match(/-?\d+(?:\.\d+)?px/g) ?? []) ud[px] = (ud[px] ?? 0) + 1
    for (const v of (m[2] ?? '').matchAll(/var\((--[\w-]+)\)/g)) {
      const k = `var:${v[1]}`
      ud[k] = (ud[k] ?? 0) + 1
    }
  }
  return ud
}

describe('rækkevisningens afstands-tokens', () => {
  it('de tre tokens er defineret med de tal de erstattede', () => {
    const c = css()
    // Vaerdien staar HER, ikke kun i en kommentar. Aendrer nogen tallet,
    // aendrer de udseendet — og saa skal de vide det.
    expect(c).toMatch(/--rv-pad-side:\s*11px/)
    expect(c).toMatch(/--rv-pad-lodret:\s*9px/)
    expect(c).toMatch(/--rv-gap:\s*12px/)
  })

  /* Tallene nedenfor er IKKE et fastfrosset øjebliksbillede. Første udgave
   * pinnede de absolutte antal, og så fejlede den i samme øjeblik punkt 5
   * lagde to nye regler ind der BRUGTE tokenet — altså præcis når koden gjorde
   * det rigtige. En test der skal rettes hver gang nogen skriver en ny regel
   * måler ikke en invariant; den måler filens længde.
   *
   * Invarianten er: ingen LITERAL står tilbage i den rolle tokenet dækker, og
   * antallet af token-brug kan kun vokse. */
  it('INGEN afstand blev flyttet — kun navngivet', () => {
    // Facittet er maalt paa filen FOER aendringen (29/9-2026). Hver token-brug
    // skal svare til praecis ét forsvundet px-tal.
    const n = tael(css())
    const brug = (k: string) => n[`var:${k}`] ?? 0
    const px = (k: string) => n[k] ?? 0

    // 11px: 24 foer (22 padding/margin + 2 `left:` paa markoererne)
    // -> 0 literale, alle 24 gennem tokenet.
    expect(px('11px')).toBe(0)
    expect(brug('--rv-pad-side')).toBeGreaterThanOrEqual(24)

    // 12px: 6 foer -> 1 literal (tom-tilstandens LODRETTE luft, en anden
    // rolle) + 5 gap gennem tokenet
    expect(px('12px')).toBeLessThanOrEqual(1)     // kun tom-tilstandens lodrette luft
    expect(brug('--rv-gap')).toBeGreaterThanOrEqual(5)

    // 9px: 10 foer -> 3 literale (to gap og ét venstre-indryk, andre roller)
    // + 7 blok-padding gennem tokenet
    expect(px('9px')).toBeLessThanOrEqual(3)      // to gap og ét venstre-indryk
    expect(brug('--rv-pad-lodret')).toBeGreaterThanOrEqual(7)
  })

  it('`8px` er bevidst IKKE tokeniseret — samme tal, fem roller', () => {
    // Prik-margin, overskrifts-gap, foldet turs bundmargin, kolonne-padding.
    // Et faelles navn ville binde dem sammen, og saa flytter én rettelse fire
    // andre steder. Testen findes for at en senere «oprydning» ikke goer det.
    // Antallet er ikke pointen — at der ikke findes et NAVN for 8px er.
    expect(tael(css())['8px']).toBeGreaterThan(0)
    expect(css()).not.toMatch(/--rv-[\w-]*:\s*8px/)
  })

  it('tokenet bruges ALDRIG til en skriftstørrelse', () => {
    // 11px er ogsaa font-size elleve steder i filen. Blandes de to, flytter en
    // aendring af indrykket teksten med.
    expect(uden(css())).not.toMatch(/font(-size)?\s*:[^;}]*--rv-pad-side/)
  })

  it('markørerne ligger på den kant de skal flugte med', () => {
    // `::before`-prikkerne er absolut placeret paa raekkens venstre indryk.
    // Staar de med et tal mens paddingen staar med tokenet, skrider de fra
    // hinanden foerste gang nogen retter det ene.
    const m = uden(css()).match(/::before\s*\{[^}]*left:\s*([^;}]+)/g) ?? []
    expect(m.length).toBeGreaterThanOrEqual(2)
    for (const r of m) expect(r).toMatch(/left:\s*var\(--rv-pad-side\)/)
  })
})
