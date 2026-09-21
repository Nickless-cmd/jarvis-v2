import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { JarvisBrowserPanel } from './JarvisBrowserPanel'

/**
 * Panelet tegner IKKE siden — den er en WebContentsView som Electron lægger
 * oven på vinduet. Det panelet skal kunne, er at MELDE hvor hullet er, og at
 * vise fanerne. Derfor måles netop de to ting her.
 */
// ResizeObserver-stubben bor i src/test/setup.ts — se hvorfor der.

const saetRect = vi.fn(async () => true)
const saetSynlig = vi.fn(async () => true)
const naviger = vi.fn(async () => true)
const tilbage = vi.fn(async () => true)
const frem = vi.fn(async () => true)
const genindlaes = vi.fn(async () => true)
const aabn = vi.fn(async () => ({ id: 3, url: '', titel: '', aktiv: true, kanTilbage: false, kanFrem: false, henter: true }))
const faner = vi.fn(async () => [
  { id: 1, url: 'https://eksempel.dk/a', titel: 'Side A', aktiv: true, kanTilbage: true, kanFrem: false, henter: false },
  { id: 2, url: 'https://eksempel.dk/b', titel: '', aktiv: false, kanTilbage: false, kanFrem: false, henter: false },
])

function broPaa() {
  ;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk = {
    browser: {
      saetRect, saetSynlig, faner, vaelg: vi.fn(), luk: vi.fn(),
      aabn, naviger, tilbage, frem, genindlaes,
    },
  }
}

describe('JarvisBrowserPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
  })

  it('er helt væk når panelet er lukket', () => {
    broPaa()
    const { container } = render(<JarvisBrowserPanel aaben={false} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('siger fra uden desk-broen i stedet for at tegne et tomt hul', () => {
    render(<JarvisBrowserPanel aaben />)
    expect(screen.getByText(/kraever desk-appen/i)).toBeTruthy()
  })

  it('melder hullets rektangel til main — ellers ved visningen ikke hvor den skal ligge', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    await waitFor(() => expect(saetRect).toHaveBeenCalled())
    const arg = saetRect.mock.calls.at(0)?.at(0) as unknown as Record<string, number>
    expect(arg).toBeTruthy()
    for (const n of ['x', 'y', 'width', 'height']) {
      expect(typeof arg[n]).toBe('number')
    }
  })

  it('taender visningen når panelet åbnes', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    await waitFor(() => expect(saetSynlig).toHaveBeenCalledWith(true))
  })

  // Hed før «falder tilbage på sin url» og målte netop dét. Den regel er
  // ÆNDRET med vilje 21/9-2026: en hel url fylder hele fanen og siger mindre
  // end værtsnavnet — «eksempel.dk» frem for «https://eksempel.dk/b?x=1#y».
  it('viser fanerne, og en fane uden titel falder tilbage på sit værtsnavn', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    expect(await screen.findByText('Side A')).toBeTruthy()
    expect(await screen.findByText('eksempel.dk')).toBeTruthy()
    expect(screen.queryByText('https://eksempel.dk/b')).toBeNull()
  })

  /**
   * Adresselinjen.
   *
   * Broen KUNNE navigere hele tiden — `naviger()` lå der ubrugt — men der var
   * ingen vej til den fra fladen. Ruden kunne åbne about:blank og derefter
   * ingenting. Det er ikke en manglende funktion, det er en ukoblet funktion,
   * og det er den slags der ser færdig ud i koden (21/9-2026).
   */
  it('sender adressen videre når man trykker retur', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    const felt = await screen.findByLabelText('Adresse') as HTMLInputElement
    // Fokus foerst — det er dét der holder pollet fra at aede tastningen, og
    // det er ogsaa det en bruger goer. Uden fokus er vaernet ikke i kraft.
    felt.focus()
    fireEvent.change(felt, { target: { value: 'github.com' } })
    fireEvent.keyDown(felt, { key: 'Enter' })
    await waitFor(() => expect(naviger).toHaveBeenCalledWith('github.com'))
  })

  it('følger den aktive fanes adresse — men overskriver ikke det man selv skriver', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    const felt = await screen.findByLabelText('Adresse') as HTMLInputElement
    await waitFor(() => expect(felt.value).toBe('https://eksempel.dk/a'))
    felt.focus()
    fireEvent.change(felt, { target: { value: 'halvt skre' } })
    // Pollet kører hvert 2. sekund; uden værnet ville det æde tastningen.
    await new Promise((r) => setTimeout(r, 60))
    expect(felt.value).toBe('halvt skre')
  })

  it('gør pilen grå når historikken ikke fører nogen steder', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    expect(await screen.findByLabelText('Tilbage')).toBeEnabled()
    expect(screen.getByLabelText('Frem')).toBeDisabled()
  })

  it('kalder tilbage og genindlæs på den aktive fane', async () => {
    broPaa()
    render(<JarvisBrowserPanel aaben />)
    fireEvent.click(await screen.findByLabelText('Tilbage'))
    fireEvent.click(screen.getByLabelText('Genindlæs'))
    await waitFor(() => expect(tilbage).toHaveBeenCalled())
    expect(genindlaes).toHaveBeenCalled()
  })

  /**
   * Lukningen.
   *
   * Webvisningen er et SOESKENDE-lag i vinduet, ikke en del af React-traeet.
   * Den forsvinder ikke af at React holder op med at tegne panelet — nogen
   * skal sige det til main. Fladerne tegner ruden som `{browserOpen && …}`,
   * saa komponenten afmonteres ved lukning og effekten faar aldrig et
   * `aaben === false` at reagere paa. Resultatet: panelet var vaek, og siden
   * blev staaende oven paa vinduet (Bjørn 21/9-2026: «jeg kan ikk lukke
   * browseren … så bliver den stående»).
   */
  it('skjuler visningen naar ruden AFMONTERES — ikke kun naar aaben bliver falsk', async () => {
    broPaa()
    const { unmount } = render(<JarvisBrowserPanel aaben />)
    await waitFor(() => expect(saetSynlig).toHaveBeenCalledWith(true))
    saetSynlig.mockClear()
    unmount()
    expect(saetSynlig).toHaveBeenCalledWith(false)
  })

  it('har samme ⤢ og × som de to andre ruder i skinnen', async () => {
    broPaa()
    const onFuld = vi.fn()
    const onClose = vi.fn()
    render(<JarvisBrowserPanel aaben onFuld={onFuld} onClose={onClose} />)
    fireEvent.click(await screen.findByLabelText('Fuld visning'))
    fireEvent.click(screen.getByLabelText('Luk'))
    expect(onFuld).toHaveBeenCalledWith(true)
    expect(onClose).toHaveBeenCalled()
  })

  it('viser hovedet ogsaa uden broen — ellers kunne man ikke lukke den igen', () => {
    const onClose = vi.fn()
    render(<JarvisBrowserPanel aaben onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('Luk'))
    expect(onClose).toHaveBeenCalled()
  })
})
