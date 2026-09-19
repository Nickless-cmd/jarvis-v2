import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Vinduesknapper } from './Vinduesknapper'

/**
 * Vinduet har ingen OS-ramme. Det gør de her knapper til de ENESTE knapper —
 * fejler de, kan vinduet ikke lukkes uden at dræbe processen.
 *
 * Fire ting kan gå galt uden at nogen ser det:
 *  1. de tegnes i en browser-fane, hvor de ikke kan gøre noget
 *  2. de tegnes oven i macOS' egen lyskurv
 *  3. ikonet siger «forstør» mens vinduet ER forstørret (tilstand udefra)
 *  4. body-klassen bliver hængende og æder 152 px af headeren uden ramme
 */
type Lyt = (maksimeret: boolean) => void

function lavBro(platform = 'linux', start = false) {
  let lytter: Lyt | undefined
  const bro = {
    minimer: vi.fn(async () => {}),
    vekselMaksimer: vi.fn(async () => !start),
    luk: vi.fn(async () => {}),
    erMaksimeret: vi.fn(async () => start),
    paaMaksimeretAendret: vi.fn((cb: Lyt) => { lytter = cb; return () => { lytter = undefined } }),
  }
  ;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk = { vindue: bro, platform }
  return { bro, meld: (m: boolean) => act(() => lytter?.(m)) }
}

beforeEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })
afterEach(() => {
  delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
  document.body.classList.remove('egen-ramme')
})

describe('Vinduesknapper', () => {
  it('tegner INTET i en browser uden broen', () => {
    const { container } = render(<Vinduesknapper />)
    expect(container).toBeEmptyDOMElement()
    // Og headeren får ikke plads reserveret til knapper der ikke findes.
    expect(document.body.classList.contains('egen-ramme')).toBe(false)
  })

  it('tegner INTET på macOS — dér er lyskurven systemets egen', () => {
    lavBro('darwin')
    const { container } = render(<Vinduesknapper />)
    expect(container).toBeEmptyDOMElement()
    expect(document.body.classList.contains('egen-ramme')).toBe(false)
  })

  it('de tre knapper rammer hver sin handling', async () => {
    const { bro } = lavBro()
    const bruger = userEvent.setup()
    render(<Vinduesknapper />)

    await bruger.click(screen.getByRole('button', { name: 'Minimer' }))
    expect(bro.minimer).toHaveBeenCalledTimes(1)

    await bruger.click(screen.getByRole('button', { name: 'Forstør' }))
    expect(bro.vekselMaksimer).toHaveBeenCalledTimes(1)

    await bruger.click(screen.getByRole('button', { name: 'Luk' }))
    expect(bro.luk).toHaveBeenCalledTimes(1)
    // Luk må ikke kunne forveksles med de to andre — den er den eneste
    // af dem der ikke kan fortrydes.
    expect(bro.minimer).toHaveBeenCalledTimes(1)
  })

  it('knappen følger tilstanden når vinduet maksimeres UDEN OM den', async () => {
    const { meld } = lavBro()
    render(<Vinduesknapper />)
    await screen.findByRole('button', { name: 'Forstør' })

    meld(true)   // dobbeltklik på bjælken, genvej, vindueshåndtering
    await waitFor(() => expect(screen.getByRole('button', { name: 'Gendan' })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Forstør' })).not.toBeInTheDocument()

    meld(false)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Forstør' })).toBeInTheDocument())
  })

  it('starter i den tilstand vinduet FAKTISK har', async () => {
    lavBro('linux', true)
    render(<Vinduesknapper />)
    expect(await screen.findByRole('button', { name: 'Gendan' })).toBeInTheDocument()
  })

  it('body-klassen sættes med ramme og ryddes når komponenten går', async () => {
    lavBro()
    const { unmount } = render(<Vinduesknapper />)
    await waitFor(() => expect(document.body.classList.contains('egen-ramme')).toBe(true))
    unmount()
    expect(document.body.classList.contains('egen-ramme')).toBe(false)
  })
})

describe('vinduesknapperne ligger EFTER appen i DOM (19/9-2026)', () => {
  it('ellers daekker headerens traek-omraade dem, og intet klik rammer', async () => {
    // Chromium: traek-omraader samles i dokument-raekkefoelge; et senere
    // `drag` overskriver et tidligere `no-drag`. Maalt paa det koerende
    // vindue med xdotool: med knapperne foerst var der hverken hover eller klik.
    const fs = await import('node:fs')
    const path = await import('node:path')
    const ts = await import('typescript')
    const kilde = fs.readFileSync(path.resolve(__dirname, '../../main.tsx'), 'utf8')
    const sf = ts.createSourceFile('main.tsx', kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    const orden: string[] = []
    const besoeg = (n: import('typescript').Node) => {
      if (ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n)) orden.push(n.tagName.getText(sf))
      ts.forEachChild(n, besoeg)
    }
    besoeg(sf)
    // Den normale gren (ikke #figur): App skal komme foer Vinduesknapper.
    expect(orden.indexOf('App')).toBeGreaterThanOrEqual(0)
    expect(orden.indexOf('Vinduesknapper')).toBeGreaterThan(orden.indexOf('App'))
  })
})
