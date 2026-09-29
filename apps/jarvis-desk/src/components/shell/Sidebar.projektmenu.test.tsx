import { describe, it, expect, vi } from 'vitest'
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
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: null }) }))
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
