import { beforeEach, describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeView } from './CodeView'
import { skaermFor } from '../lib/skaermRegister'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { SessionProvider } from '../contexts/SessionContext'
import { PanelProvider } from '../contexts/PanelContext'
import { PermissionProvider } from '../contexts/PermissionContext'
import * as api from '../lib/api'
import { usePanel } from '../hooks/usePanel'
import { PIN_INTERVAL_MS } from '../lib/useChatScroll'
import { writeRaekkevisning } from '../lib/visningsPref'

interface FakeHandlers {
  onEvent: (e: unknown) => void
  onRunId: (id: string) => void
}
const handlersRef: { current: FakeHandlers | null } = { current: null }

vi.mock('../lib/streamClient', () => ({
  startStream: (_r: unknown, h: FakeHandlers) => { handlersRef.current = h; return { abort: vi.fn(), getRunId: () => 'r1' } },
  StreamError: class extends Error {},
}))
// Job-tallet i headeren (8/10-2026). Uden denne mock gik kaldet til den
// rigtige klient og fejlede tavst — og så kunne ingen test se om viewet
// sendte SAMTALEN med. Det er hele pointen med testen nedenfor.
const listJobs = vi.fn().mockResolvedValue({ jobs: [], bridge_ok: true })
vi.mock('../lib/jobsApi', () => ({
  listJobs: (...a: unknown[]) => listJobs(...a),
}))
vi.mock('../lib/api', () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  getSessionMilestones: vi.fn().mockResolvedValue({ milestones: [] }),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' }, messages: [] }),
  createSession: vi.fn(),
  cancelRun: vi.fn(),
  cancelActiveRun: vi.fn(),
  whoami: vi.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  pingServer: vi.fn().mockResolvedValue(20),
  getVisibleProviders: vi.fn().mockResolvedValue([]),
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
  getWorkspaceTrust: vi.fn().mockResolvedValue(true),
  setWorkspaceTrust: vi.fn().mockResolvedValue(true),
  getContextInfo: vi.fn().mockResolvedValue({ compact_at: 200000, run_compact_at: 240000 }),
  getModelContext: vi.fn().mockResolvedValue({ window: 1000000, compact_at: 200000, effective: 200000 }),
  getContextUsage: vi.fn().mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, compacting: false, compacted: false }),
  getActiveRuns: vi.fn().mockResolvedValue([]),
  getActiveRunSessions: vi.fn().mockResolvedValue([]),
  followRun: vi.fn(() => ({ abort: vi.fn() })),
  // Opsamlingen af et ventende godkendelses-kort (20/9-2026): uden den
  // i mocken falder hele viewet, fordi StreamContext kalder den.
  hentVentendeGodkendelse: vi.fn(async () => null),
  hentVentendeGodkendelseOveralt: vi.fn(async () => null),
  warmSession: vi.fn().mockResolvedValue(undefined),
  getGitStatus: vi.fn().mockResolvedValue({ branch: 'main', dirty: 0, added: 0, removed: 0, is_git: true }),
  steerRun: vi.fn().mockResolvedValue(undefined),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

function PanelProbe() {
  const panel = usePanel()
  return <span data-testid="panel-target">{panel.target?.type ?? 'none'}</span>
}

function wrap(ui: ReactNode) {
  return render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>{ui}<PanelProbe /></PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )
}

/** jsdom har ingen layout: vi styrer selv målene, som browseren ville gøre. */
const maal = (t: HTMLElement, scrollHeight: number, clientHeight: number, scrollTop: number) => {
  Object.defineProperty(t, 'scrollHeight', { value: scrollHeight, configurable: true })
  Object.defineProperty(t, 'clientHeight', { value: clientHeight, configurable: true })
  t.scrollTop = scrollTop
  act(() => { t.dispatchEvent(new Event('scroll')) })
}

describe('CodeView', () => {
  beforeEach(() => {
    localStorage.clear()
    handlersRef.current = null
    vi.mocked(api.getSession).mockResolvedValue({
      session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' }, messages: [], etag: null,
    })
  })

  it('keeps historical Code messages on the existing row renderer', async () => {
    writeRaekkevisning(true)
    vi.mocked(api.getSession).mockResolvedValueOnce({
      session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' },
      messages: [{ id: 'a1', role: 'assistant', created_at: '2026-09-16T10:00:00Z', content: [
        { type: 'tool_use', id: 't1', name: 'read_file', input: {}, status: 'done' },
        { type: 'text', text: 'Kode-svar' },
      ] }],
      etag: null,
    })
    try {
      const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      await screen.findByText('Kode-svar')
      expect(container.querySelector('.raekkevisning')).toBeInTheDocument()
      expect(container.querySelector('[data-chat-flow-mode]')).not.toBeInTheDocument()
    } finally { writeRaekkevisning(false) }
  })

  it('viser INGEN kørselstal-linje — den er fjernet, og det er tredje gang', () => {
    // Bjørn 6/10-2026: «fjerne denne linje mellem compose og disclamer: 93
    // turns 1625 steps / TTFT 25335ms · 22 tok/s / 124K tokens».
    //
    // Det er TREDJE afvisning af usage-tal i chatfladen. De to foerste gjaldt
    // «1,284 tokens · Ran for 41.2s» under hvert svar. Linjen her var samme
    // slags tal et andet sted, og nu er den vaek — baade visningen, prop'en,
    // udregningen og CSS'en, saa der ikke staar doed kode der ser levende ud.
    //
    // Testen er vendt om frem for slettet: en slettet test siger ingenting til
    // den naeste der faar den gode idé at vise koerselstal i composeren.
    // Tallene bor i sessionslinjen.
    const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    expect(container.querySelector('.composer-tal')).toBeNull()
  })

  it('viser aktivitet fra en anden enhed i headeren uden at flytte composeren', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValueOnce([
      { session_id: 's1', run_id: 'remote-run', status: 'working' },
    ])
    try {
      const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      const badge = await screen.findByTestId('anden-enhed', {}, { timeout: 2500 })
      expect(badge.closest('.chatview-head-right')).toBeInTheDocument()
      expect(badge.closest('.composer-footer-slot')).toBeNull()
      expect(container.querySelector('.takeover-banner')).not.toBeInTheDocument()
    } finally {
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    }
  })

  it('viser baggrundskomprimering og den gemte tokenbesparelse', async () => {
    vi.mocked(api.getSession).mockResolvedValue({
      etag: null, session: { id: 's1', title: 'T', updated_at: 'x' },
      messages: [
        { id: 'u1', role: 'user', created_at: '2026-09-23T19:00:00Z', content: [{ type: 'text', text: 'Hej' }] },
        { id: 'compact-1', role: 'compact_marker', created_at: '2026-09-23T19:01:00Z', content: [] },
      ],
    })
    vi.mocked(api.getContextUsage).mockResolvedValue({
      tokens: 9000, compact_at: 35000, effective: 35000, model_window: 0,
      overhead_tokens: 0, compacting: true, compacted: true,
      last_compact_at: '2026-09-23T19:01:00Z',
      compactions: [{ marker_id: 'compact-1', tokens_before: 24000, tokens_after: 9000, freed_tokens: 15000 }],
    })
    try {
      wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      expect(await screen.findByPlaceholderText(/Komprimerer kontekst/)).toBeInTheDocument()
      expect(document.querySelector('.composer-area .liveness')).not.toBeInTheDocument()
      expect(await screen.findByText(/15\.000 konteksttokens frigjort/)).toBeInTheDocument()
    } finally {
      vi.mocked(api.getContextUsage).mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, model_window: 0, overhead_tokens: 0, compacting: false, compacted: false })
    }
  })

  it('tom samtale: greeting m. brugernavn + composer', () => {
    wrap(<CodeView sessionId={null} userName="Bjørn" />)
    // Greeting via GreetingHero (tids-bevidst hilsen) — navnet skal fremgå.
    expect(screen.getAllByText(/Bjørn/).length).toBeGreaterThan(0)
    // composer + workspace-vælger til stede
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('owner ser Server-valg; member ser Mit workspace', () => {
    const { unmount } = wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    expect(screen.getByText('Server')).toBeInTheDocument()
    unmount()
    wrap(<CodeView sessionId={null} userName="M" role="member" />)
    expect(screen.getByText('Mit workspace')).toBeInTheDocument()
  })

  it('workstation-knap viser mappe-vælger', () => {
    vi.stubGlobal('jarvisDesk', { pickFolder: vi.fn() })
    wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    fireEvent.click(screen.getByText('Min computer'))
    expect(screen.getByText('Vælg mappe…')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('hides local computer choice when running in a browser', () => {
    vi.stubGlobal('jarvisDesk', undefined)
    wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    expect(screen.queryByText('Min computer')).not.toBeInTheDocument()
  })

  it('viser pause_and_ask over composeren og styrer svaret ind i runet', async () => {
    // Ændret 9/11-2026 — samme grund som i ChatView: spørgsmålet skal stå fast
    // over composeren, ikke rulle med transcriptet.
    const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await userEvent.type(screen.getByRole('textbox'), 'fortsæt{Enter}')
    const result = JSON.stringify({
      kind: 'pause_and_ask',
      question: 'Hvilken fil skal jeg rette?',
      options: ['A', 'B'],
    })
    act(() => {
      handlersRef.current?.onRunId('r1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'ask-1', name: 'pause_and_ask', input: {} } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 1, content_block: { type: 'tool_result', tool_use_id: 'ask-1', status: 'done', content: result } })
    })
    // Stream-events anvendes én gang pr. frame (lib/useRammeReducer).
    await act(() => new Promise<void>((r) => setTimeout(r, 120)))

    expect(container.querySelector('.composer-notices .pauseask')).toBeInTheDocument()
    expect(container.querySelector('.transcript .pauseask')).not.toBeInTheDocument()
    expect(container.querySelector('.composer-area .liveness')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'A' }))
    await userEvent.click(screen.getByRole('button', { name: 'Send svar' }))
    await waitFor(() => expect(api.steerRun).toHaveBeenCalledWith(cfg, 'r1', 'A'))
  })

  it('fører historiske kilder fra transcriptet ind i den fælles inspector', async () => {
    vi.mocked(api.getSession).mockResolvedValue({
      etag: null,
      session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' },
      messages: [{
        id: 'a1', role: 'assistant', created_at: '2026-09-16T10:00:00Z',
        content: [{ type: 'text', text: 'Se https://docs.example.com/api for detaljerne.' }],
      }],
    })
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await screen.findByText(/docs\.example\.com\/api/)
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul miljø-felt' }))
    await userEvent.click(await screen.findByRole('button', { name: 'docs.example.com' }))
    expect(screen.getByTestId('panel-target')).toHaveTextContent('source')
  })

  // Browseren kom i chat-fladen 21/9 og blev glemt her. Ingen af de to flader
  // havde en test paa knappen — derfor saa ingen at de skiltes ad. Denne
  // pinner den i code; chat har faaet sin egen.
  it('har Jarvis\' browser i headeren, og knappen aabner ruden', async () => {
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    const knap = await screen.findByRole('button', { name: "Vis/skjul Jarvis' browser" })
    expect(document.querySelector('.jbrowser')).not.toBeInTheDocument()
    await userEvent.click(knap)
    expect(document.querySelector('.jbrowser')).toBeInTheDocument()
  })

  // Fejlen opstod i fletningen 21/9: Jarvis byggede view-request-kanalen og
  // jeg byggede den fulde visning, samme aften, hver for sig. Begge var
  // rigtige alene. Sammen kunne kanalen lukke en rude uden at slippe dens
  // fulde visning — og saa stod skinnen TOM, fordi de to andre ruder var
  // gemt bag en rude der ikke fandtes mere.
  it('slipper den fulde visning naar kanalen lukker ruden — ellers staar skinnen tom', async () => {
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    const knap = await screen.findByRole('button', { name: "Vis/skjul Jarvis' browser" })
    await userEvent.click(knap)
    await userEvent.click(await screen.findByRole('button', { name: 'Fuld visning' }))
    expect(document.querySelector('.code-right-stack.er-fuld')).toBeInTheDocument()

    // Jarvis lukker den gennem kanalen, ikke med krydset.
    const reg = skaermFor('s1')
    expect(reg).toBeDefined()
    act(() => { reg!.luk('browser') })

    expect(document.querySelector('.jbrowser')).not.toBeInTheDocument()
    // Aabner vi baggrundsjob nu, SKAL den kunne ses.
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul baggrundsjob' }))
    expect(await screen.findByRole('complementary', { name: 'Baggrundsjob' })).toBeInTheDocument()
  })

  /**
   * 17/9-nettet i code-mode (spec'ens punkt 1c, 29/9-2026).
   *
   * Før havde dette view KUN pin-ved-start. Interval-nettet og ResizeObserveren
   * fandtes ikke her, så et svar der landede ad en vej hvor hverken
   * stream-blokke, follow-blokke eller besked-antallet ændrede sig havde INTET
   * net i code-mode — samme bug Bjørn mærkede i chat 17/9-2026.
   *
   * Testen driver den ægte sti: et run fra en ANDEN enhed gør `aktiv` sand, og
   * indholdet vokser derefter UDEN en React-opdatering. Kun interval-nettet kan
   * redde den — ingen effekt i viewet ser højdeændringen.
   */
  it('holder bunden naar indholdet vokser uden en React-opdatering (17/9-nettet)', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([
      { session_id: 's1', run_id: 'remote-run', status: 'working' },
    ])
    const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await screen.findByTestId('anden-enhed', {}, { timeout: 2500 })

    const t = container.querySelector('.transcript') as HTMLElement
    expect(t).toBeInTheDocument()
    maal(t, 1000, 300, 700) // 1000 indhold, 300 synligt → staar i bunden
    expect(t.className).toContain('is-at-bottom')

    // Svaret lander ad en anden vej: indholdet vokser, intet re-render sker.
    Object.defineProperty(t, 'scrollHeight', { value: 1800, configurable: true })
    await act(async () => { await new Promise((r) => setTimeout(r, PIN_INTERVAL_MS + 80)) })

    expect(t.scrollTop).toBe(1800)
  })
  it('den levende tur bliver staaende til pacen er faerdig — done maa ikke dumpe resten', async () => {
    // Bjørn 20/10-2026: «hoved folder korrekt, og pacen køre roligt et par
    // linjer og bang så lander hele svaret».
    //
    // Aarsagen er IKKE paceren — den fortsaetter efter `message_stop` via
    // `harVaeretLive`. Det er CodeView der river den levende raekke ned i
    // samme frame som `done` (gaten var `status === 'working'`) og samtidig
    // reconciler den persisterede raekke med HELE teksten ind i transcriptet.
    // Chat-laget har `afslutterSvarPacing` + `udenAktivRun`; Code mode havde
    // ingen af dem — derfor gik det kun ud over code-fladen.
    const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await userEvent.type(screen.getByRole('textbox'), 'skriv et langt svar{Enter}')

    const svar = 'A'.repeat(600)
    act(() => {
      handlersRef.current?.onRunId('r1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
      handlersRef.current?.onEvent({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: svar } })
    })
    await act(() => new Promise<void>((r) => setTimeout(r, 150)))

    // Foer `done`: intet er dumpet.
    const foer = container.querySelector('.transcript')?.textContent ?? ''
    expect(foer.includes(svar)).toBe(false)

    act(() => {
      handlersRef.current?.onEvent({ type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { input_tokens: 0, output_tokens: 150 } })
      handlersRef.current?.onEvent({ type: 'message_stop' })
    })
    await act(() => new Promise<void>((r) => setTimeout(r, 80)))

    // Efter `done` maa resten stadig ikke lande i ét hug: pacen skal rulle
    // faerdig uanset at serveren allerede har leveret hele svaret. Maalt uden
    // rettelsen: `reconcile` lagde den persisterede raekke ind med alle 600
    // tegn i samme frame som den levende raekke forsvandt.
    const efter = container.querySelector('.transcript')?.textContent ?? ''
    expect(efter.includes(svar)).toBe(false)
    // ...og den persisterede kopi af SAMME run maa slet ikke tegnes endnu.
    expect(container.querySelector('[data-rail-id="a-r1"]')).toBeNull()
  })


})

/**
 * Job-tallet i headeren — samtale-scopet (8/10-2026).
 *
 * Tælleren hentede fra `/api/processes`, som kun kender serverens supervisor:
 * den kunne hverken filtrere på samtale eller se værktøjskald og agenter. Så
 * kunne headerens tal og panelet under den vise FORSKELLIGE tal for den samme
 * samtale. Bjørn: «baggrundsjobs panel i desk skal osse være sessions bestemt».
 *
 * Testen holder begge dele fast: at kilden er `listJobs`, og at samtalen
 * følger med i kaldet.
 */
describe('CodeView — job-tallet hører til samtalen', () => {
  beforeEach(() => {
    listJobs.mockReset()
    listJobs.mockResolvedValue({ jobs: [], bridge_ok: true })
  })

  it('henter gennem listJobs med samtalen — ikke gennem /api/processes', async () => {
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await waitFor(() => expect(listJobs).toHaveBeenCalled())
    expect(listJobs).toHaveBeenCalledWith(cfg, false, 's1')
  })
})

/**
 * Stop-knappen for ALT arbejde i samtalen (16/11-2026). CodeView var en glemt
 * kopi af ChatView før 12/11: `streaming` var kun mit eget svar, og stop kaldte
 * stream.abort() — et no-op for et run klienten ikke selv startede.
 */
describe('CodeView — stop for baggrunds-run', () => {
  const baggrund = (run_id: string) =>
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id, status: 'working' }])
  beforeEach(() => {
    vi.mocked(api.cancelRun).mockClear()
    vi.mocked(api.cancelActiveRun).mockClear()
  })
  const ryd = () => vi.mocked(api.getActiveRunSessions).mockResolvedValue([])

  it('viser stop-knappen naar et baggrunds-run kører uden at klienten streamer', async () => {
    baggrund('remote-run')
    try {
      wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      expect(await screen.findByRole('button', { name: 'Stop' }, { timeout: 2500 })).toBeInTheDocument()
    } finally { ryd() }
  })

  it('stop kalder cancel-active naar intet run-id findes', async () => {
    baggrund('') // serveren oplyser intet run-id
    try {
      wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      fireEvent.click(await screen.findByRole('button', { name: 'Stop' }, { timeout: 2500 }))
      expect(api.cancelActiveRun).toHaveBeenCalledWith(cfg, 's1')
      expect(api.cancelRun).not.toHaveBeenCalled()
    } finally { ryd() }
  })

  it('stop kalder cancelRun med run-id naar id\'et findes', async () => {
    baggrund('remote-run')
    try {
      wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      fireEvent.click(await screen.findByRole('button', { name: 'Stop' }, { timeout: 2500 }))
      expect(api.cancelRun).toHaveBeenCalledWith(cfg, 'remote-run')
      expect(api.cancelActiveRun).not.toHaveBeenCalled()
    } finally { ryd() }
  })
})

/**
 * Den ventende godkendelse står OVER COMPOSEREN (16/11-2026, anden vending).
 *
 * 31/10 flyttede kortet ind i transcriptet som primær flade. Målt 16/11:
 * Bjørn måtte scrolle til toppen af turen for at godkende. Rækken i
 * transcriptet er historik; det besvarbare kort hører til hvor han skriver.
 */
describe('CodeView — ventende godkendelse over composeren', () => {
  it('tegner kortet over composeren uden persisteret række, ikke i transcriptet', async () => {
    vi.mocked(api.hentVentendeGodkendelseOveralt).mockResolvedValue(
      { approvalId: 'ap1', tool: 'exec_command', action: 'rm -rf /tmp/x', sessionId: 's1', expiresAt: new Date(Date.now() + 3_600_000).toISOString() },
    )
    // En samtale med et spørgsmål — ellers er viewet i tom-tilstand uden transcript.
    vi.mocked(api.getSession).mockResolvedValue({
      session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' }, etag: null,
      messages: [{ id: 'u1', role: 'user', content: [{ type: 'text', text: 'ryd op' }], created_at: '2026-09-16T10:00:00Z' }],
    })
    try {
      const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      await waitFor(() => expect(container.querySelector('.composer-notices .approvalcard')).toBeInTheDocument(), { timeout: 3000 })
      expect(container.querySelectorAll('.approvalcard')).toHaveLength(1)
      expect(container.querySelector('.transcript .approvalcard')).toBeNull()
    } finally {
      vi.mocked(api.hentVentendeGodkendelseOveralt).mockResolvedValue(null)
    }
  })
})

/**
 * Cross-device i CODE MODE (Bjørn 16/11-2026): «to Code Mode-klienter på samme
 * session» — den passive klient mister run 2 eller blander dets tekst ind i
 * run 1's besked.
 *
 * Fixet i ChatView (5d3b987c7) blev ALDRIG portet hertil: CodeView kaldte
 * `followRun` uden run-id, dispatchede ikke `follow_start`, og havde ikke
 * `bgRunId` i effektens deps. Konsekvensen er målt nedenfor — ikke gættet:
 * med 6-sekunders-latchen på `bgActive` forbliver den sand mellem to runs, så
 * effekten kører ikke igen, og den passive klient abonnerer kun på det FØRSTE
 * run. Den arver derefter forrige turs `followState`.
 *
 * Testen driver den ægte sti: poll → bgActive → followRun, og måler både at
 * abonnementet bærer run-id'et, og at et nyt run genstarter det.
 */
describe('CodeView — cross-device: to runs på samme session', () => {
  type FollowKald = { onEvent: (e: unknown) => void; onDone: (r: string) => void; runId?: string | null }
  const kald: FollowKald[] = []
  /** Kaldet nr. `i` — kaster hvis det ikke findes, så en manglende genstart
   *  melder sig som en konkret fejl i stedet for `undefined` på en property. */
  const kaldet = (i: number): FollowKald => {
    const k = kald[i]
    if (!k) throw new Error(`followRun blev kun kaldt ${kald.length} gang(e) — forventede mindst ${i + 1}`)
    return k
  }

  beforeEach(() => {
    kald.length = 0
    vi.mocked(api.followRun).mockImplementation(((_c: unknown, _s: unknown, onEvent: FollowKald['onEvent'], onDone: FollowKald['onDone'], runId?: string | null) => {
      kald.push({ onEvent, onDone, runId })
      return { abort: vi.fn() }
    }) as never)
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
  })

  const tur = (runId: string, tekst: string) => [
    { type: 'message_start', message: { id: runId, model: 'm', provider: 'p', lane: 'l', origin: '', usage: { input_tokens: 0, output_tokens: 0 } } },
    { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '', phase: 'final_answer' } },
    { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: tekst } },
  ]

  it('binder abonnementet til run-id og genstarter det når et NYT run tager over', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-A', status: 'working' }])
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)

    await waitFor(() => expect(kald.length).toBe(1), { timeout: 3000 })
    // (2) run-id'et SKAL med — uden det kan reduceren ikke skelne nyt run fra reconnect.
    expect(kaldet(0).runId).toBe('run-A')

    // Tur A leverer sit svar ind i followState.
    act(() => { for (const e of tur('run-A', 'Svar fra tur A.')) kaldet(0).onEvent(e) })
    await act(() => new Promise<void>((r) => setTimeout(r, 50)))

    // Tur B starter MENS bgActive stadig er sand (6s-latchen) — præcis det
    // tilfælde hvor den gamle effekt aldrig kørte igen.
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-B', status: 'working' }])

    // (3) bgRunId skal stå i deps, ellers sker der intet her.
    await waitFor(() => expect(kald.length).toBe(2), { timeout: 4000 })
    expect(kaldet(1).runId).toBe('run-B')

    // (1) follow_start: tur A's blokke må ikke arves af tur B.
    act(() => { for (const e of tur('run-B', 'Svar fra tur B.')) kaldet(1).onEvent(e) })
    await act(() => new Promise<void>((r) => setTimeout(r, 50)))

    // `waitFor` ovenfor venter på at ABONNEMENTET er genstartet — ikke på at
    // React har committet B's tekst i DOM'en. Læste vi DOM'en synkront her,
    // kunne vi ramme vinduet mellem `onEvent` og commit: under CI-last fejlede
    // den derfor tilfældigt med «expected ... to contain 'Svar fra tur B.'».
    // Vi venter nu på præcis det vi påstår, i stedet for på et sidestykke.
    const laesSvar = () =>
      Array.from(document.querySelectorAll('.transcript, [data-live]')).map((n) => n.textContent ?? '').join(' ')
    await waitFor(() => expect(laesSvar()).toContain('Svar fra tur B.'), { timeout: 3000 })

    // Uden follow_start stod A's tekst tilbage under B — den fejl Bjørn ser.
    const svar = laesSvar()
    const bIndex = svar.indexOf('Svar fra tur B.')
    expect(svar.slice(bIndex + 'Svar fra tur B.'.length)).not.toContain('Svar fra tur A.')
  })

  it('reconnect midt i SAMME run genstarter ikke turen (samme run-id = no-op)', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-A', status: 'working' }])
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await waitFor(() => expect(kald.length).toBe(1), { timeout: 3000 })

    act(() => { for (const e of tur('run-A', 'Svar fra tur A.')) kaldet(0).onEvent(e) })
    await act(() => new Promise<void>((r) => setTimeout(r, 50)))

    // Et netværksbrud: follow-enden melder 'error' mens runnet LEVER. Samme
    // run-id skal derfor ikke give en frisk tur — kun en genoptaget strøm.
    act(() => { kaldet(0).onDone('error') })
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-A', status: 'working' }])
    await act(() => new Promise<void>((r) => setTimeout(r, 1500)))

    if (kald.length > 1) expect(kaldet(1).runId).toBe('run-A')
    expect(document.body.textContent).toContain('Svar fra tur A.')
  })

  /**
   * Reconciliation-hullet (punkt C i Bjørns opgave, 16/11-2026).
   *
   * `udenAktivRun` fik KUN den lokale stream: `stream.activeRunId` og
   * `liveBlokke(stream)`. For den passive klient er begge tomme — dens levende
   * tur ligger i `followState`. Så blev den persisterede række for run-A IKKE
   * skjult mens follow-strømmen tegnede det samme svar, og beskeden stod to
   * gange på skærmen. Kravet er eksplicit: samme assistentbesked må aldrig
   * eksistere som to synlige rækker.
   */
  it('tegner ikke den persisterede række samtidig med follow-strømmen', async () => {
    vi.mocked(api.getSession).mockResolvedValue({
      session: { id: 's1', title: 'T', updated_at: '2026-11-16T10:00:00Z' },
      messages: [{
        id: 'a1', role: 'assistant', created_at: '2026-11-16T10:00:00Z',
        run_id: 'run-A', content: [{ type: 'text', text: 'Svar fra tur A.' }],
      }],
      etag: null,
    })
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-A', status: 'working' }])
    wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
    await waitFor(() => expect(kald.length).toBe(1), { timeout: 3000 })

    act(() => { for (const e of tur('run-A', 'Svar fra tur A.')) kaldet(0).onEvent(e) })
    await act(() => new Promise<void>((r) => setTimeout(r, 120)))

    const antal = (document.body.textContent ?? '').split('Svar fra tur A.').length - 1
    expect(antal).toBe(1)
  })
})
