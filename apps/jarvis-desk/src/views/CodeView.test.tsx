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

  it('viser aktivitet fra en anden enhed som ikon ved Central i headeren', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValueOnce([
      { session_id: 's1', run_id: 'remote-run', status: 'working' },
    ])
    try {
      const { container } = wrap(<CodeView sessionId="s1" userName="B" role="owner" />)
      const badge = await screen.findByTestId('anden-enhed', {}, { timeout: 2500 })
      const headerRight = badge.closest('.chatview-head-right')
      expect(headerRight).toBeInTheDocument()
      // Ankeret var `central-badge`, men CentralBadge blev slået fra i headeren
      // 30/9-2026 (DESK_CHROME.centralBadge) og bor nu kun på Systemstatus-siden.
      // Testens ærinde er at mærket hører i header-right — så det er mærket selv
      // der er ankeret, ikke en nabo der kan slukkes uden at testen ved det.
      expect(headerRight?.contains(badge)).toBe(true)
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
      expect(await screen.findByText(/Komprimerer kontekst/)).toBeInTheDocument()
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

  it('viser pause_and_ask sammen med approvals over Code-transcriptet', async () => {
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

    const pauseCard = container.querySelector('.composer-notices .pauseask')
    const liveness = container.querySelector('.liveness')
    expect(pauseCard).toBeInTheDocument()
    expect(container.querySelector('.transcript .pauseask')).not.toBeInTheDocument()
    expect(pauseCard!.compareDocumentPosition(liveness!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
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
