/**
 * KÆDEN, ikke regnestykket (1/11-2026).
 *
 * `notifAnker.test.ts` beviser at `beregnNotifBund` regner rigtigt. Men et
 * rigtigt regnestykke der aldrig bliver kaldt — eller hvis resultat aldrig når
 * CSS-variablen — er præcis den slags teater der ser færdigt ud i en diff.
 * Denne test går hele vejen: DOM-måling → funktion → `--notif-bund` paa laget.
 *
 * HVORFOR `vi.mock` OG IKKE `vi.spyOn` (maalt 1/11-2026, kostede en runde):
 * komponenten importerer `hentNotifikationer` ved modul-load, saa en spy sat
 * EFTER importen rammer en KOPI af referencen — praecis «from X import Y
 * binder en kopi»-faelden, bare i ESM. Testen bestod af den forkerte grund:
 * mocken blev aldrig kaldt, laget blev aldrig monteret, og `null` blev laest
 * som «ingen toast» i stedet for «ingen maaling». `vi.mock` hoistes og
 * erstatter modulet FOER komponenten ser det.
 *
 * jsdom har ingen layout-motor, saa geometrien MOCKES. Det er ikke en svaghed
 * her: vi vil se OM komponenten bruger de maal den faar, ikke om browseren kan
 * maale. Tallene er Bjoerns skaermbillede 1/11-2026.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { NotifikationsToast } from './NotifikationsToast'

// ── Modul-mocks (hoistes over importerne) ───────────────────────────────────
const { hentMock } = vi.hoisted(() => ({ hentMock: vi.fn() }))

vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: hentMock,
  afgoerNotifikation: vi.fn(async () => ({ ok: true })),
  setNotifikation: vi.fn(async () => ({ ok: true })),
}))

vi.mock('../../lib/agentContractApi', () => ({
  getKontraktFeed: vi.fn(async () => ({ cards: [] })),
  ventendeGodkendelser: vi.fn(() => []),
}))

vi.mock('../../lib/api', () => ({
  openEventSocket: vi.fn(() => ({ onmessage: null, onerror: null, close: vi.fn() })),
}))

// ── Geometri: Bjoerns skaermbillede 1/11-2026 ───────────────────────────────
// Skrivefladen er 820px centreret i 1920 → 550..1370, top 900 i et 1080-vindue.
const COMPOSER = { left: 550, right: 1370, top: 900, width: 820, height: 150 }

function saetGeometri(opts: { composer?: typeof COMPOSER | null; opm?: { height: number } } = {}) {
  const composer = opts.composer === undefined ? COMPOSER : opts.composer

  // ── ELEMENTERNE SKAL FINDES (maalt 1/11-2026, kostede en runde) ─────────
  // At mocke `getBoundingClientRect` er ikke nok: `vaelg()` slaar op med
  // `querySelector('.composer-area')`, og findes elementet ikke, svarer den
  // null — hvorefter `beregnNotifBund` falder tilbage til bundgulvet. Testen
  // bestod da af den FORKERTE grund: den maalte «ingen skriveflade» og kaldte
  // det «plads til hoejre». Praecis den fejlklasse jeg selv advarer om.
  document.body.querySelectorAll('.composer-area, .opm-vaert').forEach((el) => el.remove())
  if (composer) {
    const el = document.createElement('div')
    el.className = 'composer-area'
    document.body.appendChild(el)
  }
  if (opts.opm) {
    const el = document.createElement('div')
    el.className = 'opm-vaert'
    document.body.appendChild(el)
  }

  vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(1080)
  vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(1920)

  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    if (this.classList.contains('composer-area') && composer) {
      return {
        ...composer, bottom: composer.top + composer.height, x: composer.left, y: composer.top,
        toJSON: () => ({}),
      } as DOMRect
    }
    if (this.classList.contains('opm-vaert') && opts.opm) {
      return {
        left: 0, right: 200, top: 0, bottom: opts.opm.height, width: 200, height: opts.opm.height,
        x: 0, y: 0, toJSON: () => ({}),
      } as DOMRect
    }
    // Alt andet: et reelt rektangel, saa `vaelg()`s synlighedsfilter kan svare ja.
    return {
      left: 0, right: 100, top: 0, bottom: 20, width: 100, height: 20,
      x: 0, y: 0, toJSON: () => ({}),
    } as DOMRect
  })

  // `vaelg()` kraever `offsetParent !== null` for at tro paa et element.
  Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
    configurable: true,
    get() { return this.parentElement ?? document.body },
  })
}

/**
 * Monte'r med ÉN synlig toast.
 *
 * Vejen derhen er den aegte: foerste hentning saetter baseline (ingen toasts),
 * anden hentning leverer en NY post, og saa monteres laget.
 */
async function monterMedToast(geometri: Parameters<typeof saetGeometri>[0] = {}): Promise<HTMLElement> {
  saetGeometri(geometri)

  const post = {
    id: 'p1', titel: 'Svar klar', tekst: '', slags: 'run_done',
    kan_afgoere: false, foraeldet: false, session_id: null, data: null,
  }
  let kald = 0
  hentMock.mockImplementation(async () => {
    kald += 1
    return { poster: kald === 1 ? [] : [post], antal: kald === 1 ? 0 : 1 }
  })

  const { container } = render(
    <NotifikationsToast config={{ apiBaseUrl: 'http://test.local', authToken: null } as never} />,
  )

  // Baseline er sat af mount-hentningen. Den NAESTE hentning ligger 8 sekunder
  // ude (polleren) — for langt for en test. `visibilitychange` kalder `hentNu`
  // DIREKTE og uden om ro-loftet, saa vi kommer til anden hentning med det
  // samme i stedet for at vente paa et ur der ikke er sat.
  await waitFor(() => expect(hentMock).toHaveBeenCalled(), { timeout: 2000 })
  document.dispatchEvent(new Event('visibilitychange'))

  await waitFor(() => {
    expect(container.querySelector('.notif-toast-lag')).not.toBeNull()
  }, { timeout: 2000 })

  return container.querySelector('.notif-toast-lag') as HTMLElement
}

beforeEach(() => { hentMock.mockReset() })
afterEach(() => {
  vi.restoreAllMocks()
  document.body.querySelectorAll('.composer-area, .opm-vaert').forEach((el) => el.remove())
})

describe('NotifikationsToast — ankeret naar CSS-variablen', () => {
  it('sætter --notif-bund til bundgulvet naar toasten ligger ved siden af skrivefeltet', async () => {
    // Bjoerns skaerm: toasten (1630..1898) er HELT til hoejre for skrivefeltet
    // (550..1370). Foer fixet blev den alligevel loftet til 1080-900+10 = 190.
    const lag = await monterMedToast()
    expect(lag.style.getPropertyValue('--notif-bund')).toBe('14px')
  })

  it('løfter naar skrivefeltet fylder hele bredden', async () => {
    const lag = await monterMedToast({ composer: { ...COMPOSER, left: 40, right: 1880 } })
    expect(lag.style.getPropertyValue('--notif-bund')).toBe('190px') // 1080 - 900 + 10
  })

  it('lægger sig over opmærksomhedslinjen naar den er synlig', async () => {
    const lag = await monterMedToast({ opm: { height: 34 } })
    expect(lag.style.getPropertyValue('--notif-bund')).toBe('56px') // 14 + 34 + 8
  })
})
