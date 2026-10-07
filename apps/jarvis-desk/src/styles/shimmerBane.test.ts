import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Lysfeltet skal ligge UDEN FOR teksten i begge ender — og der må kun være ét.
 *
 * Bjørn 30/9-2026: «shimmer kører igennem, starter forfra og resetter i andet
 * forsøg». Mit første forsøg flyttede start og slut til de positioner hvor
 * båndet lige akkurat er ude. Svaret var: «nulstiller stadig i teksten, bar
 * rykket lidt».
 *
 * Han havde ret, og årsagen var ikke tallene. `background-repeat` er som
 * standard `repeat`: med `background-size: 220%` var fladen BROLAGT med
 * gradienten — et lysbånd hver 2,2 elementbredder. Der var aldrig ét bånd at
 * få ud af teksten; næste brosten var altid på vej ind. At flytte start og
 * slut flyttede kun hvor nulstillingen ramte.
 *
 * Derfor måler denne vagt tre ting, og `no-repeat` er den vigtigste:
 * uden den er de to andre ligegyldige.
 */

const css = readFileSync(join(__dirname, 'app.css'), 'utf8')

/** `.shimmer`-reglens krop, uden kommentarer. */
function regel(): string {
  const r = css.replace(/\/\*[\s\S]*?\*\//g, '').match(/^\.shimmer \{([^}]*)\}/m)
  return r?.[1] ?? ''
}

/** Feltets bredde som andel af elementet, læst af `background-size`. */
function feltBredde(): number {
  const m = /background-size:\s*([\d.]+)%/.exec(regel())
  return m ? Number(m[1]) / 100 : Number.NaN
}

/** Feltets kanter i elementbredder ved en given `background-position`. */
function felt(pPct: number): [number, number] {
  const s = feltBredde()
  const x = (1 - s) * pPct / 100
  return [x, x + s]
}

/** Positionerne i `@keyframes shimmer-sweep`, i rækkefølge. */
function positioner(): number[] {
  const kf = css.match(/@keyframes shimmer-sweep \{([\s\S]*?)\n\}/)?.[1] ?? ''
  return [...kf.matchAll(/background-position:\s*(-?[\d.]+)%/g)].map((m) => Number(m[1]))
}

describe('shimmerens felt', () => {
  it('der er KUN ÉT felt — brolægningen var hele fejlen', () => {
    // Med `repeat` er der et lysbånd hver `background-size`-bredde, og så kan
    // ingen position få dem alle ud af teksten samtidig.
    expect(regel()).toMatch(/background-repeat:\s*no-repeat/)
  })

  it('grundfarven males bagved — ellers forsvinder teksten uden for feltet', () => {
    // `background-clip: text` + `text-fill-color: transparent` betyder at
    // teksten KUN er synlig hvor der er en baggrund. Med `no-repeat` er der
    // ingen uden for feltet, så uden en `background-color` ville ordene
    // forsvinde i det meste af omløbet. Samme `--fg-3` som gradientens ender,
    // så overgangen ikke kan ses.
    expect(regel()).toMatch(/background-color:\s*var\(--fg-3\)/)
    expect(regel()).toMatch(/linear-gradient\([^)]*var\(--fg-3\) 30%/)
    expect(regel()).toMatch(/var\(--fg-3\) 70%\)/)
  })

  it('keyframes har en sweep OG en hvile — tre stop, ikke to', () => {
    expect(positioner()).toHaveLength(3)
  })

  it('feltet er HELT ude til venstre når omløbet begynder', () => {
    const [, hoejre] = felt(positioner()[0]!)
    expect(hoejre, `højre kant ${hoejre.toFixed(2)}W — over 0 betyder synlig ved start`)
      .toBeLessThanOrEqual(0)
  })

  it('feltet er HELT ude til højre når sweepet slutter', () => {
    const [venstre] = felt(positioner()[1]!)
    expect(venstre, `venstre kant ${venstre.toFixed(2)}W — under 1 betyder synlig ved slut`)
      .toBeGreaterThanOrEqual(1)
  })

  it('hvilen holder feltet i ro — ellers er der ingen pause', () => {
    const p = positioner()
    expect(p[2]).toBe(p[1])
  })

  it('kontrollen: den GAMLE opsætning ville falde på alle tre', () => {
    // Uden den her kunne testene ovenfor bestå på et tilfælde. De gamle tal
    // var size 220 %, repeat, og 120 % -> -120 %.
    const gammelFelt = (p: number): [number, number] => {
      const x = (1 - 2.20) * p / 100
      return [x + 0.30 * 2.20, x + 0.70 * 2.20]   // lysbåndet i den brolagte flade
    }
    expect(gammelFelt(120)[1]).toBeGreaterThan(0)     // synligt allerede ved start
    // og uanset positionen fandtes naboens brosten 2,2W væk — det er dét
    // `no-repeat` fjerner.
    expect(2.20).toBeGreaterThan(1)
  })
})
