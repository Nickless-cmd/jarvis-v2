import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { _saetUr, _nulstil, vaagn, maaPolle, ROLIG_EFTER_MS } from '../../lib/ro'

const hent = vi.fn()
const afgoer = vi.fn()
const afslut = vi.fn()

vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  afgoerNotifikation: (...a: unknown[]) => afgoer(...a),
  setNotifikation: (...a: unknown[]) => afslut(...a),
}))

// Samme stub-moenster som Klokke.test.tsx: hver openEventSocket() laegger sin
// stub i `sockets`, saa en test kan finde den senest oprettede og udloese
// `onmessage` selv.
const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))

// Lyden er ikke det testen maaler, og jsdom har ingen AudioContext at spille
// i. Mock'en holder testen paa adfaerden og ikke paa lydkortet.
vi.mock('../../lib/toastLyd', () => ({ spilToastKlang: vi.fn() }))

// Agent-approvals er den ANDEN kilde (14/10-2026). Toasten henter nu ogsaa
// kontrakt-feedet — samme moenster som NotifikationsFeed.agents.test.tsx: den
// rigtige modul spredes, saa `bucketLabel` m.m. virker, og kun de to kald vi
// maaler paa overrides.
const kontraktFeed = vi.fn()
const afgoerAgent = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>('../../lib/agentContractApi')
  return {
    ...rigtig,
    getKontraktFeed: (...a: unknown[]) => kontraktFeed(...a),
    afgoerAgentApproval: (...a: unknown[]) => afgoerAgent(...a),
  }
})

import { NotifikationsToast } from './NotifikationsToast'
import fixture from '../../lib/__fixtures__/agentContract.json'
import type { FeedCard } from '../../lib/agentContractApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function post(over: Record<string, unknown> = {}) {
  return {
    id: 'p1', slags: 'approval', titel: 'Godkendelse', tekst: 'Noget',
    kan_afgoere: true, foraeldet: false, oprettet: '', session_id: 's1', ...over,
  }
}

/** Baseline foerst, saa en NY post — og udloes hentningen via bussen.
 *  To kald er hele pointen: den foerste saetter baseline og skal give NULL
 *  toasts, den anden er den nye post. */
async function medNyPost(ny: Record<string, unknown>) {
  hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
     .mockResolvedValue({ poster: [post(), post(ny)], antal: 2 })
  render(<NotifikationsToast config={cfg} />)
  await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
  const s = sockets[sockets.length - 1]!
  s.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
  return screen.findByText(String(ny.titel ?? 'Godkendelse'))
}

// ── Agent-approvals: den anden kilde (14/10-2026) ─────────────────────────
//
// Kortformen er den RIGTIGE rute-respons — `agentContract.json` genereres af
// backend-testen, saa et felt der forsvinder fra serveren ogsaa forsvinder her.
const agentSkabelon = fixture.feed.approval_card as unknown as FeedCard
const agentKort = (o: Partial<FeedCard> = {}): FeedCard => ({ ...agentSkabelon, ...o })
const TOMT_KONTRAKT_FEED = {
  status: 'ok' as const, cards: [] as FeedCard[],
  counts: { venter: 0, svar: 0, aktiv: 0, unread: 0 }, contract_version: '1',
}
const kontraktFeedMed = (cards: FeedCard[]) => ({
  status: 'ok' as const, cards,
  counts: { venter: cards.length, svar: 0, aktiv: 0, unread: 0 }, contract_version: '1',
})

/** Baseline foerst, saa en NY agent-approval — hentet gennem
 *  visibility-skiftet, som er den vej der gaar UDEN om ro-loftet.
 *
 *  Der findes intet WS-signal for agent-approvals: `notifikation.ny` udsendes
 *  naar en notifikations-raekke foedes, og en agent-approval foeder ingen. */
async function medNyAgentApproval(kort: FeedCard) {
  kontraktFeed.mockResolvedValueOnce(TOMT_KONTRAKT_FEED).mockResolvedValue(kontraktFeedMed([kort]))
  render(<NotifikationsToast config={cfg} />)
  await waitFor(() => expect(kontraktFeed).toHaveBeenCalledTimes(1))
  fireEvent(document, new Event('visibilitychange'))
  return screen.findByText(kort.title)
}

describe('NotifikationsToast', () => {
  beforeEach(() => {
    hent.mockReset(); hent.mockResolvedValue({ poster: [], antal: 0 })
    afgoer.mockReset(); afgoer.mockResolvedValue({ ok: true, fejl: '' })
    afslut.mockReset(); afslut.mockResolvedValue(undefined)
    kontraktFeed.mockReset(); kontraktFeed.mockResolvedValue(TOMT_KONTRAKT_FEED)
    afgoerAgent.mockReset(); afgoerAgent.mockResolvedValue({})
    sockets.length = 0
    localStorage.clear()
  })

  afterEach(() => { _saetUr(() => Date.now()); _nulstil() })

  // ── Baseline ────────────────────────────────────────────────────────────
  //
  // Uden baseline ville et opstart med fyrre aabne poster dumpe fyrre toasts
  // i hovedet paa brugeren i samme sekund. Det er ikke et varsel, det er en
  // larm — og det er den fejl der er lettest at lave her.
  it('viser INGEN toast for poster der laa der i forvejen', async () => {
    hent.mockResolvedValue({ poster: [post(), post({ id: 'p2', titel: 'Gammel' })], antal: 2 })
    render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    expect(screen.queryByText('Godkendelse')).toBeNull()
    expect(screen.queryByText('Gammel')).toBeNull()
  })

  it('viser en toast naar en NY post lander', async () => {
    expect(await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: false }))
      .toBeInTheDocument()
  })

  it('bevarer live-forbindelsen naar kun config-objektets identitet skifter', async () => {
    const view = render(<NotifikationsToast config={{ ...cfg }} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    expect(sockets).toHaveLength(1)

    view.rerender(<NotifikationsToast config={{ ...cfg }} />)
    expect(sockets).toHaveLength(1)
    expect(hent).toHaveBeenCalledTimes(1)
  })

  it('holder toasten synlig mens vinduet er skjult og henter igen naar det vises', async () => {
    let synlighed = 'visible'
    vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => synlighed as DocumentVisibilityState)
    try {
      await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: false })
      const nedtaelling = document.querySelector('.notif-toast-nedtaelling') as HTMLElement
      synlighed = 'hidden'
      fireEvent(document, new Event('visibilitychange'))
      expect(nedtaelling.style.animationPlayState).toBe('paused')

      const foer = hent.mock.calls.length
      synlighed = 'visible'
      fireEvent(document, new Event('visibilitychange'))
      await waitFor(() => expect(hent.mock.calls.length).toBeGreaterThan(foer))
      expect(nedtaelling.style.animationPlayState).not.toBe('paused')
    } finally {
      vi.restoreAllMocks()
    }
  })

  // Klokken springer bevidst `run_done` over (1152 aabne 4/10). En toast maa
  // vise den alligevel — den viser noget ÉN gang og forsvinder, saa den
  // gentager ikke det problem klokken havde. Denne test laaser den forskel.
  it('viser run_done — i modsaetning til klokken', async () => {
    expect(await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: false }))
      .toBeInTheDocument()
  })

  // ── Nedtaellingen: forsvinder ≠ afviser ────────────────────────────────
  //
  // Denne er den vigtigste i filen. Foerste udgave kaldte «Afvis» naar
  // nedtaellingen loeb ud — saa en godkendelse man bare ikke naaede at se
  // paa i syv sekunder blev AFVIST paa serveren. At lade noget ligge er ikke
  // det samme som at sige nej, og fejlen er tavs: feltet forsvandt jo.
  it('naar nedtaellingen loeber ud forsvinder feltet — UDEN at afvise posten', async () => {
    await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: true })
    fireEvent.animationEnd(document.querySelector('.notif-toast-nedtaelling')!)
    await waitFor(() => expect(screen.queryByText('Svar klar')).toBeNull())
    expect(afgoer).not.toHaveBeenCalled()
    expect(afslut).not.toHaveBeenCalled()
  })

  it('«Luk» (X) fjerner feltet — ogsaa uden at roere serveren', async () => {
    await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: true })
    fireEvent.click(screen.getByRole('button', { name: 'Luk feltet' }))
    await waitFor(() => expect(screen.queryByText('Svar klar')).toBeNull())
    expect(afgoer).not.toHaveBeenCalled()
    expect(afslut).not.toHaveBeenCalled()
  })

  // ── De to veje ud: afgoer eller afslut ─────────────────────────────────
  //
  // `kan_afgoere` er hele forskellen. En post der KRAEVER et svar skal
  // afgoeres (approved=false); en ren orientering lukkes. Bytter man om,
  // svarer klienten «nej» til noget der ikke var et spoergsmaal.
  it('«Afvis» paa en post der kraever svar AFGOER den', async () => {
    await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: true })
    fireEvent.click(screen.getByRole('button', { name: 'Afvis' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, 'p2', false))
    expect(afslut).not.toHaveBeenCalled()
  })

  it('«Afvis» paa en ren orientering LUKKER den i stedet', async () => {
    await medNyPost({ id: 'p2', titel: 'Svar klar', slags: 'run_done', kan_afgoere: false })
    fireEvent.click(screen.getByRole('button', { name: 'Luk' }))
    await waitFor(() => expect(screen.queryByText('Svar klar')).toBeNull())
    expect(afgoer).not.toHaveBeenCalled()
  })

  // ── Åbne-vejen ─────────────────────────────────────────────────────────
  it('«Aabn» giver session-id videre og kvitterer posten', async () => {
    const aabn = vi.fn()
    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [post(), post({ id: 'p2', titel: 'Svar klar', slags: 'run_done' })], antal: 2 })
    render(<NotifikationsToast config={cfg} onAabenSession={aabn} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
    await screen.findByText('Svar klar')

    fireEvent.click(screen.getByRole('button', { name: 'Åbn' }))
    await waitFor(() => expect(aabn).toHaveBeenCalledWith('s1'))
  })

  // ── Bussen ─────────────────────────────────────────────────────────────
  //
  // /ws baerer ALT — indre stemme, raesonnement, hvad som helst. En fremmed
  // haendelse maa ikke udloese en hentning, eller lytter vi reelt til hele
  // bussen i stedet for kun `notifikation.*`. Samme vaern som Klokke har.
  it('ignorerer haendelser der ikke er vores', async () => {
    hent.mockResolvedValue({ poster: [], antal: 0 })
    render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'runtime.tick' }) })
    await new Promise((r) => setTimeout(r, 30))
    expect(hent).toHaveBeenCalledTimes(1)
  })

  it('foraeldede poster giver ingen toast', async () => {
    hent.mockResolvedValueOnce({ poster: [], antal: 0 })
       .mockResolvedValue({ poster: [post({ id: 'p2', titel: 'Foraeldet', foraeldet: true })], antal: 1 })
    render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
    await new Promise((r) => setTimeout(r, 30))
    expect(screen.queryByText('Foraeldet')).toBeNull()
  })

  // ── Ro-loftet maa ikke sluge en haendelse (målt 8/10-2026) ──────────────
  //
  // Bjørn: «klokken i feedet ringer og lyden kommer.. og en sjælen gang
  // imellem kommer toast i desk». Aarsagen var praecis dette: klokken kaldte
  // `hentNu` (uden om loftet) fra sin WS-lytter, mens toasten kaldte `hent`
  // — som foerst spoerger `maaPolle('notifikationer', 8000)`. Klokken og
  // toasten deler noeglen, saa naar klokkens poll lige har sat sit stempel,
  // svarer loftet nej for toasten, og posten bliver sprunget over. Lyden kom
  // (klokken), toasten udeblød.
  //
  // Samme test-moenster som Klokke.test.tsx: i jsdom er `sidsteLivstegn`
  // altid frisk, saa `roFaktor()` er 1 og loftet er aldrig reelt i kraft.
  // `_saetUr` + `vaagn()` tvinger det i kraft, og `maaPolle`-kaldet BEVISER
  // at det blokerer — ellers maalte testen ingenting.
  it('haendelsen gaar UDENOM ro-loftet — et poll i samme oejeblik ville vaere blokeret', async () => {
    let ur = 1_000_000_000
    _saetUr(() => ur)
    vaagn()
    ur += ROLIG_EFTER_MS + 1_000 // roFaktor() er fra nu af FAKTOR_RO

    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [post(), post({ id: 'p2', titel: 'Svar klar', slags: 'run_done' })], antal: 2 })
    render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))
    expect(screen.queryByText('Svar klar')).toBeNull()

    // Bevis at loftet reelt blokerer NU.
    expect(maaPolle('notifikationer', 8000)).toBe(false)

    sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })

    expect(await screen.findByText('Svar klar')).toBeInTheDocument()
  })

  // ── Toasten maa ikke filtrere den aktive samtale fra (målt 8/10-2026) ────
  //
  // Ro-loftet var kun den ENE aarsag til at toasten udeblød. Den anden laa i
  // SERVEREN: `feed()` skjuler `run_done` naar posten hoerer til den AKTIVE
  // samtale (`?aktiv=`), og desk sendte altid sit eget sessions-id. Maalt mod
  // den koerende server: 1705 aabne uden filter, 1160 med — 545 skjulte, og
  // `run_done` er den mest almindelige toast.
  //
  // Filtreringen hoerer i FEEDET og i KLOKKEN: de viser «hvad venter paa dig
  // lige nu». En toast er et engangs-varsel om at noget SKETE — den skal ikke
  // skjules fordi man tilfaeldigvis sidder i den samtale svaret kom fra.
  it('henter UDEN aktiv-filter — et svar i den aktive samtale skal ogsaa give toast', async () => {
    hent.mockResolvedValueOnce({ poster: [post()], antal: 1 })
       .mockResolvedValue({ poster: [post(), post({ id: 'p2', titel: 'Svar klar', slags: 'run_done' })], antal: 2 })
    render(<NotifikationsToast config={cfg} />)
    await waitFor(() => expect(hent).toHaveBeenCalledTimes(1))

    // Andet argument er `aktivSession`. Det skal vaere udefineret — ellers
    // bygger serveren `?aktiv=` og fjerner netop de poster toasten skal vise.
    expect(hent.mock.calls[0]![1]).toBeUndefined()

    sockets[sockets.length - 1]!.onmessage?.({ data: JSON.stringify({ kind: 'notifikation.ny' }) })
    expect(await screen.findByText('Svar klar')).toBeInTheDocument()
  })

  // ── Agent-approvals: den anden halvdel af klagen (14/10-2026) ───────────
  //
  // Bjørns klage havde to halvdele. Den første — kortet over composeren — blev
  // loest om formiddagen. Den anden er denne: kom posten mens man var et andet
  // sted, fik man en toast UDEN knapper.
  //
  // Aarsagen var ikke at knapperne manglede i toasten. Det var at
  // agent-approvals slet ikke NAAR toasten: de har ingen krog ind i
  // notifikations-lageret (`afstem_godkendelser` foeder kun TOOL-approvals), saa
  // de findes kun i kontrakt-feedet — som toasten aldrig spurgte om.
  describe('agent-godkendelser', () => {
    it('viser en NY agent-approval — med Godkend OG Afvis', async () => {
      expect(await medNyAgentApproval(agentKort())).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Godkend' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Afvis' })).toBeInTheDocument()
    })

    // Digest'en binder afgoerelsen til netop dette kald, og sessionen binder den
    // til den samtale posten blev foedt i. Mangler en af dem, afviser lageret
    // svaret — derfor maa de ikke falde ud undervejs til toasten.
    it('«Godkend» gaar til AGENT-ruten med digest OG origin_session_id', async () => {
      await medNyAgentApproval(agentKort())
      fireEvent.click(screen.getByRole('button', { name: 'Godkend' }))
      await waitFor(() => expect(afgoerAgent).toHaveBeenCalledWith(
        cfg, 'appr-c3d3dc5d507040e2', 'approve',
        '0000000000000000000000000000000000000000000000000000000000000000', 'sess-1'))
      // IKKE notifikations-ruten: den kender ikke posten.
      expect(afgoer).not.toHaveBeenCalled()
    })

    it('«Afvis» sender deny ad samme vej', async () => {
      await medNyAgentApproval(agentKort())
      fireEvent.click(screen.getByRole('button', { name: 'Afvis' }))
      await waitFor(() => expect(afgoerAgent).toHaveBeenCalledWith(
        cfg, 'appr-c3d3dc5d507040e2', 'deny', expect.any(String), 'sess-1'))
    })

    it('viser INGEN toast for approvals der laa der i forvejen', async () => {
      kontraktFeed.mockResolvedValue(kontraktFeedMed([agentKort()]))
      render(<NotifikationsToast config={cfg} />)
      await waitFor(() => expect(kontraktFeed).toHaveBeenCalled())
      expect(screen.queryByText('Godkend: bash')).toBeNull()
    })

    // En notifikation er et engangs-varsel; en godkendelse er en opgave der
    // staar aaben. Faldt den efter syv sekunder, var man lige vidne til praecis
    // det problem knapperne skal loese: at man ikke kan naa at svare.
    it('har INGEN nedtaelling — den venter paa et svar', async () => {
      await medNyAgentApproval(agentKort())
      expect(document.querySelector('.notif-toast-agent')).not.toBeNull()
      expect(document.querySelector('.notif-toast-agent .notif-toast-nedtaelling')).toBeNull()
    })

    // Kun VENTENDE kort MED en approval. Et fejlet assignment kraever ogsaa et
    // svar, men det gaar gennem feedets kvittering — ikke her.
    it('et ventende kort UDEN approval giver ingen toast', async () => {
      const udenApproval = agentKort({ ref_kind: 'agent', approval: undefined, bucket: 'failed' })
      kontraktFeed.mockResolvedValueOnce(TOMT_KONTRAKT_FEED)
                  .mockResolvedValue(kontraktFeedMed([udenApproval]))
      render(<NotifikationsToast config={cfg} />)
      await waitFor(() => expect(kontraktFeed).toHaveBeenCalledTimes(1))
      fireEvent(document, new Event('visibilitychange'))
      await new Promise((r) => setTimeout(r, 30))
      expect(screen.queryByText(udenApproval.title)).toBeNull()
    })

    it('er posten afgjort, forsvinder feltet', async () => {
      await medNyAgentApproval(agentKort())
      fireEvent.click(screen.getByRole('button', { name: 'Godkend' }))
      await waitFor(() => expect(screen.queryByText('Godkend: bash')).toBeNull())
    })

    // En afgoerelse der ikke gik igennem maa ikke se ud som om den gjorde.
    it('fejler afgoerelsen, VISES fejlen — feltet forsvinder ikke tavst', async () => {
      afgoerAgent.mockRejectedValue(new Error('Godkendelsen er allerede afgjort.'))
      await medNyAgentApproval(agentKort())
      fireEvent.click(screen.getByRole('button', { name: 'Godkend' }))
      expect(await screen.findByText('Godkendelsen er allerede afgjort.')).toBeInTheDocument()
    })
  })
})
