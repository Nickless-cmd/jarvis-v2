import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Skillelinjen skal GLIDE ind ved turstart og BLIVE stående
 * (Bjørn 22/10-2026: «det burde komme fra starten og blive … og så skal den
 * være lysere»).
 *
 * Fejlen var ikke at attributten manglede — den var sand fra FØRSTE render i
 * chat mode. En ren `transition` har derfor intet at animere fra, og stregen
 * popper. Vagtens pointe er derfor todelt:
 *
 *  1. reglen skal have en `animation` hvis `from` ER starttilstanden, så
 *     mount-tidspunktet ikke afgør om der animeres, og
 *  2. `both` skal holde sluttilstanden, ellers falder `::after` tilbage til
 *     grundtilstanden (`opacity: 0; transform: scaleX(0)`) når animationen
 *     er færdig — og så forsvinder stregen igen.
 */
describe('TurHoved — skillelinjens livscyklus', () => {
  const css = readFileSync(join(__dirname, '../../styles/turhoved.css'), 'utf8')

  const regel = (selektor: string) => {
    const esc = selektor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const m = new RegExp(esc + '\\s*\\{([^}]*)\\}').exec(css)
    expect(m, `reglen ${selektor} findes ikke`).not.toBeNull()
    return m![1]
  }

  it('keyframes starter ved den usynlige tilstand — ikke ved slutpositionen', () => {
    const m = /@keyframes\s+rv-skillelinje-ind\s*\{([\s\S]*?)\n\}/.exec(css)
    expect(m, '@keyframes rv-skillelinje-ind mangler').not.toBeNull()
    const blok = m![1]
    expect(blok).toMatch(/from\s*\{[^}]*opacity:\s*0/)
    expect(blok).toMatch(/from\s*\{[^}]*transform:\s*scaleX\(0\)/)
    expect(blok).toMatch(/to\s*\{[^}]*transform:\s*scaleX\(1\)/)
  })

  it('den LEVENDE turs streg animerer ind — ikke kun en transition', () => {
    const blok = regel('.rv-tur[data-skillelinje][data-levende]::after')
    expect(blok).toMatch(/animation:\s*rv-skillelinje-ind/)
    expect(blok).toMatch(/\bboth\b/)
  })

  it('persisteret historik animerer IKKE — stregen staar bare der', () => {
    // MÅLT 30/10-2026 i Chromium (Playwright, denne fil, TurHoveds ægte
    // markup): med animationen paa `[data-skillelinje]` alene gav reload af 20
    // persisterede ture 20 `animationstart`-events — alle streger gled ind
    // samtidigt — og én React-remount gen-fyrede animationen midt i samtalen.
    // Derfor er indglidningen bundet til `data-levende`, som kun den
    // streamende tur bærer.
    const blok = regel('.rv-tur[data-skillelinje]::after')
    expect(blok).not.toMatch(/animation:/)
    expect(blok).toMatch(/opacity:\s*1/)
    expect(blok).toMatch(/transform:\s*scaleX\(1\)/)
  })

  it('bruger en hel CSS-pixel, så Firefox og Electron rasteriserer den ens', () => {
    const blok = regel('.rv-tur::after')
    expect(blok).toMatch(/height:\s*1px/)
    expect(blok).toMatch(/bottom:\s*-1px/)
  })

  it('reduced motion slår animationen fra, så stregen ikke glider', () => {
    const m = /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([\s\S]*?)\n\}/.exec(css)
    expect(m, 'reduced-motion-blokken mangler').not.toBeNull()
    expect(m![1]).toMatch(/\.rv-tur::after[^}]*animation:\s*none/)
  })
})
