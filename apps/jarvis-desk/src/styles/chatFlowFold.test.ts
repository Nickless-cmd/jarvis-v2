import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Foldet skal GLIDE, ikke forsvinde i én frame.
 *
 * Bjørn 20/10-2026: «synteser og runder forsvinder i et blink». Årsagen var
 * ikke en animation der fejlede — der var ingen. `hidden` er `display: none`,
 * så gruppen blev fjernet momentant, og hele billedet rykked sammen med
 * præcis linjernes højde.
 *
 * Vagtens vigtigste påstand er den fjerde: `hidden` må ikke komme tilbage.
 * Uden den kan nogen «rydde op» og genindføre den gamle kontrakt uden at en
 * eneste komponent-test fælder det — de måler hvad der rendres, ikke hvordan
 * det forsvinder.
 */

const css = readFileSync(join(__dirname, 'chat-flow.css'), 'utf8')
  // Kommentarerne nævner selv `hidden` og `display: none`; de skal ikke tælle.
  .replace(/\/\*[\s\S]*?\*\//g, '')

function regel(selektor: string): string {
  const escaped = selektor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return css.match(new RegExp(`^${escaped} \\{([^}]*)\\}`, 'm'))?.[1] ?? ''
}

describe('chat mode — foldet glider i stedet for at blinke', () => {
  it('den ydre ramme er et grid med animeret rækkehøjde', () => {
    const r = regel('.chat-flow-gruppe-ydre')
    expect(r).toMatch(/display:\s*grid/)
    expect(r).toMatch(/grid-template-rows:\s*1fr/)
    expect(r).toMatch(/transition:\s*grid-template-rows\s+var\(--dur-(snap|fast|base|sheet|slow)\)/)
  })

  it('lukket tilstand er 0fr — det er rækken der animerer, ikke synligheden', () => {
    expect(regel(".chat-flow-gruppe-ydre[data-aaben='false']"))
      .toMatch(/grid-template-rows:\s*0fr/)
  })

  it('barnet kan krympe under sit indhold — ellers lukker rækken aldrig', () => {
    const r = regel('.chat-flow-gruppe-ydre > .chat-flow-gruppe')
    expect(r).toMatch(/min-height:\s*0/)
    expect(r).toMatch(/overflow:\s*clip/)
  })

  it('den lukkede gruppe lander på 0 — padding må ikke blive tilbage som et hop', () => {
    // Målt 20/10-2026 i Chromium: uden denne regel landede den lukkede gruppe
    // på 3,19 px, fordi `overflow: clip` fjerner indholdet men ikke gruppens
    // egen `padding-top` (0.2rem). Det er præcis det hop reglen skal fjerne.
    expect(regel(".chat-flow-gruppe-ydre[data-aaben='false'] > .chat-flow-gruppe"))
      .toMatch(/padding-top:\s*0/)
    expect(regel('.chat-flow-gruppe-ydre > .chat-flow-gruppe'))
      .toMatch(/transition:\s*padding-top/)
  })

  it('den gamle kontrakt må ikke komme tilbage', () => {
    expect(css).not.toMatch(/\.chat-flow-gruppe\[hidden\]/)
  })

  it('den lukkede fold forlader ALDRIG layoutet — så har åbningen altid en før-tilstand', () => {
    // 18/11-2026. Tre løsninger blev målt i Chromium og forkastet før denne:
    //   1. `display: none` alene — intet at animere, folden hoppede.
    //   2. `display: none` + `allow-discrete` — lukningen gled, åbningen hoppede.
    //   3. samme + `@starting-style` — rækken startede korrekt på 0px, men
    //      `hovedTilSvar` sprang alligevel fra 4px til 14,39px i frame 0.
    //
    // Fælles rod: et element der fjernes fra layoutet har ingen før-tilstand.
    // Så snart `display` skifter til `grid`, er elementet tilbage som grid-item
    // og grid-gappet slår ind med det samme — svaret rykker 10px ned, FØR
    // glidningen begynder. Det var hoppet, hele tiden.
    //
    // Løsningen er at elementet bliver stående: nul-plads kommer fra `0fr`,
    // nulstillet `padding-top` på barnet (ellers er gulvet 3,19px) og en
    // gap-kompensation på svaret — ikke fra at fjerne det fra layoutet.
    expect(css).not.toMatch(/\.chat-flow-gruppe-ydre[^{]*\{[^}]*display:\s*none/)
    expect(css).not.toMatch(/display\s+var\(--dur-[a-z]+\)\s+allow-discrete/)
    // Uden `align-self: start` STRÆKKES elementet som grid-item, og så bliver
    // den lukkede gruppe højere end nul (målt 16,78px = summen af dens margins).
    expect(regel('.chat-flow-gruppe-ydre')).toMatch(/align-self:\s*start/)
  })

  it('svaret bærer gap-kompensationen — ellers rykker positionen i frame 0', () => {
    // Målt 18/11-2026: den lukkede gruppe er et nul-højt grid-item og koster
    // stadig TO grid-gaps (20,8px). Kun det ene neutraliseres af `-6.4px` på
    // svaret. En negativ margin på GRUPPEN hjælper ikke: `align-self: start`
    // flytter den ganske vist, men grid-rækkens højde clampes til 0, så gap'et
    // under den bliver stående — målt 14,39px uanset hvor meget der blev
    // trukket op.
    //
    // Kompensationen sidder derfor på det element der faktisk skal flyttes,
    // og er med i transitionen, så positionen står stille i frame 0 og glider
    // i takt med at rækken folder ud. Målt efter rettelsen: 3,98px lukket,
    // 3,98px i frame 0 og 1 — derefter jævn kurve opad.
    expect(regel('.chat-flow > .rv-tur ~ .chat-flow-answer')).toMatch(
      /transition:[^;]*margin-top/,
    )
    expect(
      regel(".chat-flow > .rv-tur ~ .chat-flow-gruppe-ydre[data-aaben='false'] ~ .chat-flow-answer"),
    ).toMatch(/margin-top:\s*calc\(-0\.65rem - 6\.4px\)/)
  })

  it('respekterer prefers-reduced-motion', () => {
    expect(css).toMatch(
      /prefers-reduced-motion[\s\S]{0,200}?\.chat-flow-gruppe-ydre\s*\{\s*transition:\s*none/,
    )
  })
})
