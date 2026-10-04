import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hent = vi.fn()
const hentHistorik = vi.fn()
const afgoer = vi.fn()
const set = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  hentTidligere: (...a: unknown[]) => hentHistorik(...a),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => set(...a),
}))

// V5: samme stub-moenster som Klokke.test.tsx — hvert openEventSocket()-kald
// laegger sin stub i `sockets`, saa en test kan finde den senest oprettede
// og udloese `onmessage` selv.
const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))

import { NotifikationsFeed } from './NotifikationsFeed'
import { notificationAttention } from '../../lib/notificationAttention'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const post = (o: Partial<Record<string, unknown>> = {}) => ({
  id: '1', slags: 'approval', titel: 'Vil du tillade bash?',
  tekst: 'Jarvis vil køre en kommando.', session_id: 's-1',
  oprettet: new Date().toISOString(), kan_afgoere: true, foraeldet: false, ...o,
})

/** En AFGJORT post — samme felter plus udfaldet. `kan_afgoere` er false: der
 *  er intet at svare paa, og det er hele forskellen til listen ovenfor.
 *
 *  `...o` staar SIDST. Ligger overstyringen foer standarden, vinder standarden
 *  — og en test der bad om «afvist» fik «godkendt» uden at nogen opdagede
 *  hvorfor (maalt 26/9-2026: praecis det skete, og testen fangede det). */
const afgjortPost = (o: Partial<Record<string, unknown>> = {}) => ({
  ...post({ kan_afgoere: false }),
  klaret: new Date().toISOString(),
  udfald: 'godkendt',
  udfald_tekst: 'Godkendt af dig',
  ...o,
})

describe('NotifikationsFeed', () => {
  beforeEach(() => {
    hent.mockReset(); hentHistorik.mockReset(); afgoer.mockReset(); set.mockReset()
    localStorage.clear()
    sockets.length = 0
    // Historikken er tom som udgangspunkt — de fleste tests handler om
    // «venter», og uden en default ville `.then` ramme undefined.
    hentHistorik.mockResolvedValue({ poster: [], antal: 0 })
  })

  it('swipe højre markerer læst, swipe venstre sletter; hjørnekrydset bruger samme sletning', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    set.mockResolvedValue(undefined)
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    const card = (await screen.findByTestId('notif-svar-1')).closest('li')!
    expect(notificationAttention(['1']).unread).toBe(true)
    fireEvent.touchStart(card, { touches: [{ clientX: 50, clientY: 100 }] })
    fireEvent.touchEnd(card, { changedTouches: [{ clientX: 140, clientY: 104 }] })
    expect(notificationAttention(['1']).unread).toBe(false)
    await waitFor(() => expect(card).toHaveClass('er-laest'))
    expect(set).not.toHaveBeenCalled()
    fireEvent.touchStart(card, { touches: [{ clientX: 140, clientY: 100 }] })
    fireEvent.touchEnd(card, { changedTouches: [{ clientX: 50, clientY: 104 }] })
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, '1'))
    expect(screen.getByRole('button', { name: 'Fjern notifikation' })).toBeInTheDocument()
  })

  it('viser stadig individuel fjernelse for spørgsmål', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'question', kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const card = (await screen.findByTestId('notif-1')).closest('li')!
    expect(card).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fjern notifikation' })).toBeInTheDocument()
  })

  it('fastholder et muse-swipe og lader lodret bevægelse scrolle', async () => {
    class TestPointerEvent extends MouseEvent {
      pointerId: number
      pointerType: string
      constructor(type: string, init: PointerEventInit = {}) {
        super(type, init)
        this.pointerId = init.pointerId ?? 0
        this.pointerType = init.pointerType ?? 'mouse'
      }
    }
    vi.stubGlobal('PointerEvent', TestPointerEvent)
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    const card = (await screen.findByTestId('notif-svar-1')).closest('li')!
    const capture = vi.fn()
    Object.defineProperty(card, 'setPointerCapture', { configurable: true, value: capture })
    Object.defineProperty(card, 'releasePointerCapture', { configurable: true, value: vi.fn() })
    fireEvent.pointerDown(card, { pointerId: 1, pointerType: 'mouse', clientX: 50, clientY: 50 })
    expect(capture).toHaveBeenCalledWith(1)
    fireEvent.pointerMove(card, { pointerId: 1, clientX: 53, clientY: 120 })
    fireEvent.pointerUp(card, { pointerId: 1, clientX: 53, clientY: 120 })
    expect(notificationAttention(['1']).unread).toBe(true)
    fireEvent.pointerDown(card, { pointerId: 2, pointerType: 'mouse', clientX: 50, clientY: 50 })
    fireEvent.pointerMove(card, { pointerId: 2, clientX: 112, clientY: 53 })
    fireEvent.pointerUp(card, { pointerId: 2, clientX: 112, clientY: 53 })
    expect(notificationAttention(['1']).unread).toBe(false)
    vi.unstubAllGlobals()
  })

  it('rydder kun læste informative poster', async () => {
    const posts = [post({ id: 'reply', slags: 'run_done', kan_afgoere: false }),
      post({ id: 'pending', slags: 'approval' }), post({ id: 'new', slags: 'run_done', kan_afgoere: false })]
    hent.mockResolvedValueOnce({ poster: posts, antal: 3 })
      .mockResolvedValue({ poster: posts.slice(1), antal: 2 })
    set.mockResolvedValue(undefined)
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    fireEvent.click(await screen.findByTestId('notif-svar-reply'))
    fireEvent.click(screen.getByRole('button', { name: /Ryd læste/ }))
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, 'reply'))
    expect(set).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.queryByTestId('notif-svar-reply')).toBeNull())
  })

  it('en fejl ser IKKE ud som en tom feed', async () => {
    hent.mockRejectedValue(new Error('offline'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
    expect(screen.queryByText(/Ingen notifikationer/)).toBeNull()
  })

  it('siger det pænt naar der faktisk ikke er noget', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText(/Ingen notifikationer/)).toBeInTheDocument()
  })

  it('viser hvor svaret er når Venter er tom', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText('Intet venter på dig. 1 svar under Svar.')).toBeInTheDocument()
  })

  it('godkender og fjerner posten fra listen', async () => {
    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [], antal: 0 })
    afgoer.mockResolvedValue({ ok: true, fejl: '' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, '1', true))
    await waitFor(() => expect(screen.queryByText('Vil du tillade bash?')).toBeNull())
  })

  it('siger det hoejt naar et svar ikke kunne sendes — og beholder posten', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    afgoer.mockResolvedValue({ ok: false, fejl: 'Kørslen er væk.' })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Afvis' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Kørslen er væk.')
    expect(screen.getByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('en foraeldet post kan ikke afgoeres', async () => {
    hent.mockResolvedValue({ poster: [post({ foraeldet: true, kan_afgoere: false })], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText('Vil du tillade bash?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    expect(screen.getByText(/kunne ikke opdateres/i)).toBeInTheDocument()
  })

  it('baerer den fulde tekst som hover-information', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const raekke = await screen.findByTestId('notif-1')
    expect(raekke.getAttribute('title')).toBe('Jarvis vil køre en kommando.')
  })

  it('viser indholdet i feedet og kan afslutte en post uden samtale', async () => {
    hent.mockResolvedValueOnce({ poster: [post({ slags: 'run_done', kan_afgoere: false, session_id: null })], antal: 1 })
      .mockResolvedValue({ poster: [], antal: 0 })
    set.mockResolvedValue(undefined)
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByText('Jarvis vil køre en kommando.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Fjern notifikation' }))
    await waitFor(() => expect(set).toHaveBeenCalledWith(cfg, '1'))
    await waitFor(() => expect(screen.queryByText('Vil du tillade bash?')).toBeNull())
  })

  it('kan opdatere listen manuelt, mens feedet er åbent', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 }).mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText(/Ingen notifikationer/)
    fireEvent.click(screen.getByRole('button', { name: 'Opdater notifikationer' }))
    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('et spoergsmaal foerer hen til samtalen — det kan ikke svares her', async () => {
    hent.mockResolvedValue({
      poster: [post({ slags: 'question', kan_afgoere: false, titel: 'Hvilken fil?' })],
      antal: 1,
    })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    await screen.findByText('Hvilken fil?')
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Færdig' })).toBeNull()
    fireEvent.click(screen.getByTestId('notif-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
    expect(set).not.toHaveBeenCalled()
  })

  it('aabner samtalen naar man trykker paa en post uden handling', async () => {
    hent.mockResolvedValue({ poster: [post({ slags: 'run_done', kan_afgoere: false })], antal: 1 })
    set.mockResolvedValue(undefined)
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    fireEvent.click(await screen.findByTestId('notif-svar-1'))
    expect(aabn).toHaveBeenCalledWith('s-1')
    expect(set).not.toHaveBeenCalled()
  })

  // V1: en `foraeldet` post har `kan_afgoere: false` (ejeren kunne ikke
  // hydreres), saa raekkens onClick gaar samme vej som "run_done" ovenfor —
  // MEN et klik her maa ALDRIG lukke posten paa serveren. Den venter stadig;
  // en utilgaengelig ejer maa ikke faa den til at ligne en klaret opgave.
  it('en foraeldet post sender IKKE /set naar man klikker den — den er ikke klaret', async () => {
    hent.mockResolvedValue({
      poster: [post({ slags: 'run_failed', kan_afgoere: false, foraeldet: true })],
      antal: 1,
    })
    const aabn = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabn} />)
    fireEvent.click(await screen.findByTestId('notif-1'))
    // Navigation maa gerne ske...
    expect(aabn).toHaveBeenCalledWith('s-1')
    // ...men /set maa ALDRIG sendes for en foraeldet raekke.
    await new Promise((r) => setTimeout(r, 10))
    expect(set).not.toHaveBeenCalled()
  })

  // V5: ruden staar IKKE stille mens den er aaben — den deler klokkens
  // live-signal (samme WS-bus, samme `notifikation.*`-filter).
  it('opdaterer listen paa en haendelse — uden at man lukker og aabner ruden igen', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 })
       .mockResolvedValue({ poster: [post()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByText(/Ingen notifikationer/)

    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })

    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
  })

  it('ignorerer haendelser der ikke er vores', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    const s = sockets[sockets.length - 1]!
    s.onmessage?.({ data: JSON.stringify({ kind: 'runtime.tick' }) })
    await new Promise((r) => setTimeout(r, 30))
    expect(hent).toHaveBeenCalledTimes(1)
  })

  // ── Fanerne (Bjoern 26/9-2026) ─────────────────────────────────────────
  //
  // Foer var feeden ÉN liste: svarede man, forsvandt posten — ogsaa
  // historikken over hvad man havde svaret. Disse fire tests laaser den
  // adskillelse fast.

  it('«Tidligere» viser de afgjorte — med udfaldet, og uden handlingsknapper', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    hentHistorik.mockResolvedValue({ poster: [afgjortPost()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)

    fireEvent.click(await screen.findByRole('tab', { name: /Tidligere/ }))

    expect(await screen.findByText('Godkendt af dig')).toBeInTheDocument()
    // Afgjort = laesning. Et kort der SER ud som om det kan trykkes, men ikke
    // kan, er samme fejlklasse som en tom klokke der ser brudt ud.
    expect(screen.queryByRole('button', { name: 'Godkend' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Færdig' })).toBeNull()
  })

  it('et godkendt og et afvist svar staar IKKE som det samme ord', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    hentHistorik.mockResolvedValue({
      poster: [afgjortPost({ udfald: 'afvist', udfald_tekst: 'Afvist af dig' })],
      antal: 1,
    })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /Tidligere/ }))
    expect(await screen.findByText('Afvist af dig')).toBeInTheDocument()
  })

  it('fanerne baerer deres tal — man ser at der ER en historik uden at aabne den', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    hentHistorik.mockResolvedValue({ poster: [afgjortPost()], antal: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)

    expect(await screen.findByRole('tab', { name: /Venter på dig/ })).toHaveTextContent('1')
    expect(screen.getByRole('tab', { name: /Tidligere/ })).toHaveTextContent('1')
  })

  it('historikken fejler for sig selv — «venter» staar uberoert', async () => {
    hent.mockResolvedValue({ poster: [post()], antal: 1 })
    hentHistorik.mockRejectedValue(new Error('offline'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)

    // De aabne er hentet fint, og de bliver ikke skjult af at historikken
    // fejler. Det er to lister med hver sin fejl-tilstand.
    expect(await screen.findByText('Vil du tillade bash?')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: /Tidligere/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/kunne ikke hentes/i)
  })

  // ── «Svar»-fanen (Bjoern 26/9-2026) ────────────────────────────────────
  //
  // Et svar er ikke en opgave. Maalt 26/9-2026 stod 100 aabne `run_done` i
  // «Venter paa dig» sammen med de 24 der faktisk ventede — og tilboed en
  // «Faerdig»-knap for noget der allerede var faerdigt.

  const svarPost = (o: Partial<Record<string, unknown>> = {}) => ({
    ...post({
      id: 'r-1', slags: 'run_done', titel: 'Svar klar i «hey..»',
      tekst: 'Her er hvad jeg gjorde.', kan_afgoere: false, session_id: 'chat-x',
    }),
    ...o,
  })

  it('«Svar» har sin egen liste — de staar ikke i «Venter på dig»', async () => {
    hent.mockResolvedValue({ poster: [post(), svarPost()], antal: 2, venter: 1 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)

    expect(await screen.findByRole('tab', { name: /Venter på dig/ })).toHaveTextContent('1')
    expect(screen.getByRole('tab', { name: /^Svar/ })).toHaveTextContent('1')

    fireEvent.click(screen.getByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByText('Her er hvad jeg gjorde.')).toBeInTheDocument()
  })

  it('et svar er laesning — ingen handlingsknapper', async () => {
    hent.mockResolvedValue({ poster: [svarPost()], antal: 1, venter: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    fireEvent.click(await screen.findByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByText('Her er hvad jeg gjorde.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Færdig' })).toBeNull()
  })

  it('sender den aktive samtale med, saa serveren kan springe dens svar over', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0, venter: 0 })
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}}
                              aktivSession="chat-her" />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(hent.mock.calls[0]![1]).toBe('chat-her')
  })
})
