import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Projekt-menuen maa ikke arve en gennemsigtighed.
 *
 * 29/9-2026: menuen bag «⋮» i projekt-overskriften stod 80 % gennemsigtig —
 * samtale-titlerne bagved skinnede igennem og laa oven i menuens egen tekst.
 * Menuens EGEN opacity var 1 og dens baggrund uigennemsigtig (`--bg-2`), saa
 * baade markup og `.session-menu` saa rigtige ud i kilden. Fejlen laa i
 * foraelderen: `.sidebar-label { opacity: .8 }`, og opacity gaelder hele
 * undertraeet — ogsaa en `position: absolute`-popup, der ellers slipper for
 * alt andet foraelderen goer ved sit indhold.
 *
 * Testen maaler den rigtige markup (den rigtige Sidebar, klikket aabnet) mod
 * den rigtige app.css, og gaar OP gennem forfaedrene. Den ville ikke fange
 * noget hvis den kun saa paa `.session-menu` selv — det var jo netop der alt
 * var i orden.
 */

const SESSIONER = [
  { id: 's1', title: 'Hvad er den samlet status', updated_at: 'x',
    kind: 'code', workspace_kind: 'workstation', workspace_root: '/media/projects/jarvis-v2' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
    setPinned: vi.fn(), setArchived: vi.fn(), setWorkspace: vi.fn(), releaseWorkspace: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  // Udsnits-abonnementet gaar gennem SAMME tilstand (4/10-2026):
  // Sidebar laeser nu ÉT felt, saa den ikke rendrer hele listen om
  // ved hver stream-chunk.
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

/** app.css lagt ind i dokumentet, saa getComputedStyle svarer paa rigtige regler. */
function medAppCss() {
  const css = readFileSync(join(__dirname, '../../styles/app.css'), 'utf8')
  const s = document.createElement('style')
  s.textContent = css
  document.head.appendChild(s)
}

/** Aabn projekt-overskriftens menu og giv menu-elementet tilbage. */
function aabenProjektMenu(): HTMLElement {
  render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)
  const knap = screen.getByLabelText('Projekt-handlinger')
  fireEvent.click(knap)
  const menu = knap.parentElement?.querySelector('.session-menu')
  expect(menu, 'menuen aabnede ikke').toBeTruthy()
  return menu as HTMLElement
}

/** Hver forfader fra menuen og op til <html>, med sin egen opacity. */
function forfaedresOpacity(menu: HTMLElement): { klasser: string; opacity: string }[] {
  const ud: { klasser: string; opacity: string }[] = []
  let n: HTMLElement | null = menu.parentElement
  while (n && n !== document.documentElement) {
    ud.push({ klasser: n.className || n.tagName, opacity: getComputedStyle(n).opacity || '1' })
    n = n.parentElement
  }
  return ud
}

describe('projekt-menuen er ikke gennemsigtig', () => {
  it('menuen selv staar fuldt daekkende', () => {
    medAppCss()
    const menu = aabenProjektMenu()
    const s = getComputedStyle(menu)
    expect(s.opacity === '' || s.opacity === '1').toBe(true)
    expect(s.backgroundColor).not.toBe('transparent')
  })

  it('INGEN forfader daemper undertraeet — det var hele fejlen', () => {
    medAppCss()
    const menu = aabenProjektMenu()
    const daempere = forfaedresOpacity(menu)
      .filter((f) => f.opacity !== '' && Number(f.opacity) < 1)
    expect(daempere, `disse forfaedre tegner menuen gennemsigtig: ${JSON.stringify(daempere)}`)
      .toEqual([])
  })

  it('overskriftens EGEN tekst er stadig daempet — rettelsen maa ikke lyse den op', () => {
    medAppCss()
    render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)
    const navn = document.querySelector('.sidebar-projekt-navn') as HTMLElement
    const sti = document.querySelector('.sidebar-projekt-sti') as HTMLElement
    expect(navn, 'projekt-navnet mangler').toBeTruthy()
    // jsdom svarer '' naar opacity IKKE er sat — og `Number('')` er 0, saa et
    // `toBeLessThan(1)` bestod ogsaa uden daempningen. Foerste udgave af denne
    // test var hul af netop den grund; mutationen afsloerede den.
    for (const [navnet, el] of [['navn', navn], ['sti', sti]] as const) {
      const raa = getComputedStyle(el).opacity
      expect(raa, `${navnet}: opacity er slet ikke sat`).not.toBe('')
      expect(Number(raa), `${navnet}: opacity=${raa}`).toBeGreaterThan(0)
      expect(Number(raa), `${navnet}: opacity=${raa}`).toBeLessThan(1)
    }
  })

  it('overskriften staar paa samme venstre kant som raekkerne under den', () => {
    // Bjoern 29/9-2026: «den er rykket saa langt ind... ser aandssvagt ud».
    // Overskriften havde `padding-left: 18px` OVEN I etikettens egne 10px og
    // stod dermed 18px laengere inde end sine egne samtaler.
    medAppCss()
    render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)
    const h = document.querySelector('.sidebar-projekt') as HTMLElement
    const raekke = document.querySelector('.session-item') as HTMLElement
    expect(h, 'projekt-overskriften mangler').toBeTruthy()
    expect(raekke, 'ingen samtale-raekke at maale mod').toBeTruthy()
    const px = (v: string) => Number(String(v).replace('px', '')) || 0
    expect(px(getComputedStyle(h).paddingLeft))
      .toBe(px(getComputedStyle(raekke).paddingLeft))
  })
})

/* ── Menuen vender opad naar listen ville klippe den ────────────────────────
 *
 * Jarvis' rettelse (`aa2aa1c09`, 29/9-2026): `.sessions` har
 * `overflow-y: auto`, saa en menu der aabner nedad fra en raekke naer bunden
 * bliver KLIPPET — den findes, men kan ikke ses. Pladsen maales i
 * `useLayoutEffect` og klassen `opad` saettes hvis der ikke er plads.
 *
 * Den kom uden test, og i jsdom er ALLE rektangler nul: `0 - 0 < 0 + 12` er
 * sandt, saa menuen faar `opad` uanset hvad. En test der bare laeste klassen
 * ville altsaa bestaa uden at maale noget. Derfor stilles rektanglerne op
 * eksplicit — ét tilfaelde med plads, ét uden. */

/** Giv `.sessions`, ankeret og menuen hver sit rektangel. */
function medPlads(pladsUnderAnkeret: number, menuHoejde: number) {
  const rect = (top: number, bottom: number) =>
    ({ top, bottom, left: 0, right: 0, width: 0, height: bottom - top,
       x: 0, y: top, toJSON: () => ({}) }) as DOMRect
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    const k = this.className?.toString() ?? ''
    if (k.includes('sessions')) return rect(0, 500)
    if (k.includes('session-menu-anchor')) return rect(0, 500 - pladsUnderAnkeret)
    if (k.includes('session-menu')) return rect(0, menuHoejde)
    return rect(0, 0)
  })
}

describe('menuen vender opad naar der ikke er plads', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('rigelig plads under raekken → menuen bliver nedad', () => {
    medPlads(300, 80)
    const menu = aabenProjektMenu()
    expect(menu.className).not.toMatch(/\bopad\b/)
  })

  it('for lidt plads → menuen vendes opad, ellers klipper listen den', () => {
    medPlads(20, 80)
    const menu = aabenProjektMenu()
    expect(menu.className).toMatch(/\bopad\b/)
  })

  it('maalingen bruger menuens EGEN hoejde, ikke en fast konstant', () => {
    // Samme plads, to menu-hoejder: kun den hoeje maa vendes. En implementering
    // med en magisk konstant ville svare det samme begge gange.
    medPlads(100, 40)
    expect(aabenProjektMenu().className).not.toMatch(/\bopad\b/)
    vi.restoreAllMocks()
    document.body.innerHTML = ''
    medPlads(100, 200)
    expect(aabenProjektMenu().className).toMatch(/\bopad\b/)
  })
})

/* ── Fodens flade og projektnavnets stoerrelse (Bjoern 29/9-2026) ───────────
 *
 * «det graa felt bag badge, name, owner skal vaek — og projekt navn skal vaere
 * lidt stoerre». Den graa flade var `.sidebar-foot .who`s hover/aaben-baggrund;
 * det var den eneste regel der malte noget bag de tre. */

const appCss = () =>
  readFileSync(join(__dirname, '../../styles/app.css'), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')   // kommentarer vaek — de naevner ordene selv

describe('sidepanelets fod og projekt-overskrift', () => {
  it('konto-knappen maler INGEN flade — hverken ved hover eller aaben', () => {
    // :hover kan ikke maales i jsdom, saa reglen laeses fra kilden. Begge
    // tilstande skal med: en af dem alene ville lade den anden staa.
    const css = appCss()
    for (const tilstand of [':hover', '[aria-expanded="true"]']) {
      const re = new RegExp(`\\.sidebar-foot \\.who${tilstand.replace(/[[\]"]/g, '\\$&')}[^{]*\\{([^}]*)\\}`)
      const krop = re.exec(css)?.[1]
      expect(krop, `ingen regel for ${tilstand}`).toBeTruthy()
      expect(krop, `${tilstand} maler stadig en flade: ${krop}`)
        .not.toMatch(/background(-color)?\s*:\s*(?!none\b|transparent\b)/)
    }
  })

  it('knappen svarer stadig — teksten loefter sig, saa den ikke bliver doed', () => {
    const css = appCss()
    const krop = /\.sidebar-foot \.who:hover[^{]*\{([^}]*)\}/.exec(css)?.[1] ?? ''
    expect(krop).toMatch(/color\s*:\s*var\(--fg-1\)/)
  })

  it('projektnavnet er stoerre end etiketten omkring det', () => {
    medAppCss()
    render(<Sidebar surface="code" onSurface={() => {}} userName="Bjørn" />)
    const navn = document.querySelector('.sidebar-projekt-navn') as HTMLElement
    const sti = document.querySelector('.sidebar-projekt-sti') as HTMLElement
    const px = (el: HTMLElement) => Number(getComputedStyle(el).fontSize.replace('px', ''))
    // 11px er `.sidebar-label`s egen stoerrelse — den stien stadig staar paa.
    expect(px(sti)).toBe(11)
    expect(px(navn)).toBeGreaterThan(px(sti))
  })
})
