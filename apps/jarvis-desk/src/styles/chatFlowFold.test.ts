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
    expect(r).toMatch(/transition:\s*grid-template-rows\s+\d+ms/)
  })

  it('lukket tilstand er 0fr — ikke display: none', () => {
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
    expect(css).not.toMatch(/\.chat-flow-gruppe\s*\{[^}]*display:\s*none/)
  })

  it('respekterer prefers-reduced-motion', () => {
    expect(css).toMatch(
      /prefers-reduced-motion[\s\S]{0,200}?\.chat-flow-gruppe-ydre\s*\{\s*transition:\s*none/,
    )
  })
})
