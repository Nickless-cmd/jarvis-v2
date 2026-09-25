import { beforeEach, describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, fireEvent, act } from '@testing-library/react'
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

interface FakeHandlers {
  onEvent: (e: unknown) => void
  onRunId: (id: string) => void
}
const handlersRef: { current: FakeHandlers | null } = { current: null }

vi.mock('../lib/streamClient', () => ({
  startStream: (_r: unknown, h: FakeHandlers) => { handlersRef.current = h; return { abort: vi.fn(), getRunId: () => 'r1' } },
  StreamError: class extends Error {},
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

describe('CodeView', () => {
  beforeEach(() => {
    localStorage.clear()
    handlersRef.current = null
    vi.mocked(api.getSession).mockResolvedValue({
      session: { id: 's1', title: 'T', updated_at: '2026-09-16T10:00:00Z' }, messages: [], etag: null,
    })
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
    wrap(<CodeView sessionId={null} userName="B" role="owner" />)
    fireEvent.click(screen.getByText('Min computer'))
    expect(screen.getByText('Vælg mappe…')).toBeInTheDocument()
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
})
