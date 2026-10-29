import { GenoptagelsesVarselHost } from '../components/feedback/GenoptagelsesVarselHost'
import { useEffect } from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatView } from './ChatView'
import { SessionProvider } from '../contexts/SessionContext'
import { useSessions } from '../hooks/useSessions'
import { PIN_INTERVAL_MS } from '../lib/useChatScroll'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { PanelProvider } from '../contexts/PanelContext'
import { PermissionProvider } from '../contexts/PermissionContext'
import * as api from '../lib/api'
import { writeRaekkevisning } from '../lib/visningsPref'
import type { ContentBlock } from '../lib/sseProtocol'

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
  listSessions: vi.fn().mockResolvedValue([{ id: 's1', title: 'T', updated_at: 'x' }]),
  getSession: vi.fn().mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [] }),
  createSession: vi.fn(),
  cancelRun: vi.fn(),
  whoami: vi.fn().mockResolvedValue({ user_id: 'u', display_name: 'Bjørn', role: 'owner' }),
  pingServer: vi.fn().mockResolvedValue(20),
  getVisibleProviders: vi.fn().mockResolvedValue([]),
  getContextInfo: vi.fn().mockResolvedValue({ compact_at: 200000, run_compact_at: 240000 }),
  getModelContext: vi.fn().mockResolvedValue({ window: 1000000, compact_at: 200000, effective: 200000 }),
  getContextUsage: vi.fn().mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, compacting: false, compacted: false }),
  getSessionMilestones: vi.fn().mockResolvedValue({ milestones: [] }),
  getActiveRuns: vi.fn().mockResolvedValue([]),
  getActiveRunSessions: vi.fn().mockResolvedValue([]),
  // warmSession kom til i api.ts uden at mocken fulgte med — testen har
  // vaeret roed siden. Ikke en aegte fejl, men en roed suite skjuler den
  // naeste der ER aegte.
  warmSession: vi.fn().mockResolvedValue(undefined),
  followRun: vi.fn(() => ({ abort: vi.fn(), getOffset: () => 0, getRunId: () => null })),
  uploadAttachment: vi.fn(async () => ({ id: 'att-1' })),
  // Opsamlingen af et ventende godkendelses-kort (20/9-2026): uden den
  // i mocken falder hele viewet, fordi StreamContext kalder den.
  hentVentendeGodkendelse: vi.fn(async () => null),
  hentVentendeGodkendelseOveralt: vi.fn(async () => null),
  // Uden den i mocken falder hele viewet: effekten ved session-aabning kalder
  // den. Samme faelde som `warmSession` ovenfor.
  hentGenoptagelsesVarsel: vi.fn(async () => null),
  presencePing: vi.fn().mockResolvedValue(undefined),
  fetchPendingNotifications: vi.fn().mockResolvedValue([]),
  ackNotification: vi.fn().mockResolvedValue(undefined),
}))

// Sideopgaverne (spec desk-sideopgaver): tom liste som standard, saa de
// oevrige tests ser den chat de altid har set.
const sideopgaver = vi.hoisted(() => ({ liste: [] as unknown[] }))
vi.mock('../lib/sideTasksApi', () => ({
  getSideTasks: vi.fn(async () => sideopgaver.liste),
  setSideTaskStatus: vi.fn(),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

// Kladden og panel-tilstanden persisteres nu i localStorage (4/10-2026), så uden
// denne lækker én tests åbne panel ind i den næste — og «de to ruder kan stå
// SAMMEN» fejler, fordi panelet allerede ER åbent fra testen før.
beforeEach(() => localStorage.clear())

describe('ChatView integration', () => {
  it('holder historisk Chat Flow adskilt fra Code-rækkevisning ved et tomt blokindeks', async () => {
    writeRaekkevisning(true)
    const sparseContent = new Array<ContentBlock>(2)
    sparseContent[1] = { type: 'tool_use', id: 't1', name: 'read_file', input: {} }
    function InjectMessages() {
      const { reconcile } = useSessions()
      useEffect(() => {
        reconcile({ id: 'a1', role: 'assistant', created_at: '2026-09-27T10:00:00Z',
          content: sparseContent })
        reconcile({ id: 'a2', role: 'assistant', created_at: '2026-09-27T10:01:00Z',
          content: [{ type: 'text', text: 'Sikkert svar' }] })
      }, [reconcile])
      return null
    }
    try {
      const { container } = render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" /><InjectMessages />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      expect(await screen.findByText('Sikkert svar')).toBeInTheDocument()
      expect(container.querySelector('[data-chat-flow-mode="living"]')).toBeInTheDocument()
      expect(container.querySelector('.raekkevisning')).not.toBeInTheDocument()
    } finally {
      writeRaekkevisning(false)
    }
  })

  it('viser komprimering i composeren uden at genindføre liveness-linjen', async () => {
    vi.mocked(api.getSession).mockResolvedValue({
      etag: null, session: { id: 's1', title: 'T', updated_at: 'x' },
      messages: [{ id: 'u1', role: 'user', created_at: '2026-09-23T19:00:00Z', content: [{ type: 'text', text: 'Hej' }] }],
    })
    vi.mocked(api.getContextUsage).mockResolvedValue({
      tokens: 11000, compact_at: 35000, effective: 35000, model_window: 0,
      overhead_tokens: 0, compacting: true, compacted: false, last_compact_at: '',
      compactions: [],
    })
    try {
      const { container } = render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      expect(await screen.findByPlaceholderText(/Komprimerer kontekst/)).toBeInTheDocument()
      expect(container.querySelector('.composer-area .liveness')).not.toBeInTheDocument()
    } finally {
      vi.mocked(api.getSession).mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [], etag: null })
      vi.mocked(api.getContextUsage).mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, model_window: 0, overhead_tokens: 0, compacting: false, compacted: false })
    }
  })

  it('viser en gemt komprimeringsmarkør og hvor meget kontekst der blev frigjort', async () => {
    vi.mocked(api.getSession).mockResolvedValue({
      etag: null, session: { id: 's1', title: 'T', updated_at: 'x' },
      messages: [
        { id: 'u1', role: 'user', created_at: '2026-09-23T19:00:00Z', content: [{ type: 'text', text: 'Hej' }] },
        { id: 'compact-1', role: 'compact_marker', created_at: '2026-09-23T19:01:00Z', content: [] },
      ],
    })
    vi.mocked(api.getContextUsage).mockResolvedValue({
      tokens: 9000, compact_at: 35000, effective: 35000, model_window: 0,
      overhead_tokens: 0, compacting: false, compacted: true,
      last_compact_at: '2026-09-23T19:01:00Z',
      compactions: [{ marker_id: 'compact-1', tokens_before: 24000, tokens_after: 9000, freed_tokens: 15000 }],
    })
    try {
      render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      expect(await screen.findByText(/15\.000 konteksttokens frigjort/)).toBeInTheDocument()
    } finally {
      vi.mocked(api.getSession).mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [], etag: null })
      vi.mocked(api.getContextUsage).mockResolvedValue({ tokens: 0, compact_at: 130000, effective: 130000, model_window: 0, overhead_tokens: 0, compacting: false, compacted: false })
    }
  })

  it('shows optimistic user msg + streamed assistant text', async () => {
    const { container } = render(
      <SettingsProvider initialConfig={cfg}>
        <SessionProvider config={cfg}>
          <StreamProvider config={cfg}>
            <PermissionProvider>
              <PanelProvider defaultWidth={400}>
                <ChatView sessionId="s1" />
              </PanelProvider>
            </PermissionProvider>
          </StreamProvider>
        </SessionProvider>
      </SettingsProvider>,
    )
    await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
    // 17/10-2026: `getByText` er SYNKRON — den venter ikke på at den optimistiske
    // besked er flushet. Under CI-load fejlede den derfor tilfældigt
    // («Unable to find an element with the text: hej», run 39026252819).
    // `findByText` venter og gentager; påstanden er den samme, kun ventetiden er ny.
    expect(await screen.findByText('hej')).toBeInTheDocument()
    act(() => {
      handlersRef.current?.onRunId('r1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current?.onEvent({ type: 'system_event', kind: 'final_answer_start', payload: { run_id: 'r1' } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
      handlersRef.current?.onEvent({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'svar' } })
    })
    expect(await screen.findByText('svar')).toBeInTheDocument()
    act(() => { handlersRef.current?.onEvent({ type: 'message_stop' }) })
    await act(() => new Promise<void>((r) => setTimeout(r, 120)))
    expect(container.querySelector('.msg-block[data-just-completed]')).toHaveTextContent('svar')
  })

  it('fortsætter den samme rolige pacing efter message_stop uden final_answer_start', async () => {
    // Svar uden tools får ingen final_answer_start fra relæet. DeepSeek kan
    // levere dem i store bidder; wakeup/follow-modellen leverer typisk små og
    // skjulte derfor fejlen. Den lokale Chat-række skal pace fra første delta
    // og blive monteret, mens resten ruller færdig efter message_stop.
    const text = 'Et længere normalt chatsvar uden værktøj. '.repeat(40)
    const view = render(
      <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
        <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
          <ChatView sessionId="s1" />
        </PanelProvider></PermissionProvider></StreamProvider>
      </SessionProvider></SettingsProvider>,
    )
    await userEvent.type(screen.getByRole('textbox'), 'svar uden tool{Enter}')
    act(() => {
      handlersRef.current?.onRunId('r-no-boundary')
      handlersRef.current?.onEvent({ type: 'message_start', message: {
        id: 'r-no-boundary', model: 'm', provider: 'p', lane: 'l', session_id: 's1',
        usage: { input_tokens: 0, output_tokens: 0 },
      } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0,
        content_block: { type: 'text', text: '' } })
      handlersRef.current?.onEvent({ type: 'content_block_delta', index: 0,
        delta: { type: 'text_delta', text } })
    })
    const synligTekst = () => view.container
      .querySelector('.chat-flow-answer, .chat-flow-live-synthesis')?.textContent?.length ?? 0
    await waitFor(() => expect(synligTekst()).toBeGreaterThan(0))
    const førStop = synligTekst()
    act(() => { handlersRef.current?.onEvent({ type: 'message_stop' }) })

    const answer = view.container.querySelector('.chat-flow-answer')
    expect(answer).toBeInTheDocument()
    expect(answer?.textContent?.length ?? 0).toBeGreaterThanOrEqual(førStop)
    expect(answer?.textContent?.length ?? 0).toBeLessThan(text.length)
    expect(view.container.textContent).not.toContain(text)
    view.unmount()
  })

  it('viser eget uploadet billede straks og skjuler kørselstal i chat', async () => {
    URL.createObjectURL = vi.fn(() => 'blob:chat-preview')
    const { container } = render(
      <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
        <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
          <ChatView sessionId="s1" />
        </PanelProvider></PermissionProvider></StreamProvider>
      </SessionProvider></SettingsProvider>,
    )
    const input = container.querySelector<HTMLInputElement>('input[type="file"]')!
    fireEvent.change(input, { target: { files: [new File(['image'], 'foto.png', { type: 'image/png' })] } })
    await waitFor(() => expect(api.uploadAttachment).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('foto.png')).toBeInTheDocument())
    await userEvent.type(screen.getByRole('textbox'), 'se her{Enter}')
    await waitFor(() => expect(container.querySelector('.msg-user-images img')).toHaveAttribute('src', 'blob:chat-preview'))
    expect(container.querySelector('.composer-tal')).toBeNull()
  })

  it('bruger uploadens nye session til beskeden, selv før parent-proppen er opdateret', async () => {
    vi.mocked(api.createSession).mockClear()
    vi.mocked(api.createSession).mockResolvedValueOnce({ id: 's-upload', title: 'Ny samtale', updated_at: 'now' })
    URL.createObjectURL = vi.fn(() => 'blob:new-chat-preview')
    function BoundChatView() {
      const { activeId } = useSessions()
      return <ChatView sessionId={activeId} />
    }
    const { container } = render(
      <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
        <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
          <BoundChatView />
        </PanelProvider></PermissionProvider></StreamProvider>
      </SessionProvider></SettingsProvider>,
    )
    fireEvent.change(container.querySelector<HTMLInputElement>('input[type="file"]')!, {
      target: { files: [new File(['image'], 'nyt.png', { type: 'image/png' })] },
    })
    await waitFor(() => expect(api.uploadAttachment).toHaveBeenCalled())
    await userEvent.type(screen.getByRole('textbox'), 'billede{Enter}')
    await waitFor(() => expect(container.querySelector('.msg-user-images img')).toHaveAttribute('src', 'blob:new-chat-preview'))
    expect(api.createSession).toHaveBeenCalledTimes(1)
  })

  it('starter ikke en follow-stream for sit eget svar efter message_stop', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    vi.mocked(api.followRun).mockClear()
    try {
      render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'r1', status: 'working' }])
      vi.mocked(api.followRun).mockClear()
      const pollsBeforeStop = vi.mocked(api.getActiveRunSessions).mock.calls.length
      act(() => {
        handlersRef.current?.onRunId('r1')
        handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
        handlersRef.current?.onEvent({ type: 'message_stop' })
      })
      await waitFor(() => expect(vi.mocked(api.getActiveRunSessions).mock.calls.length).toBeGreaterThan(pollsBeforeStop))
      await act(() => new Promise<void>((r) => setTimeout(r, 100)))
      expect(api.followRun).not.toHaveBeenCalled()
    } finally {
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    }
  })

  it('følger stadig et andet aktivt run i den åbne session', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'other-run', status: 'working' }])
    vi.mocked(api.followRun).mockClear()
    try {
      render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      await waitFor(() => expect(api.followRun).toHaveBeenCalledOnce())
    } finally {
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    }
  })

  it('følger fortsættelses-run selv om sessionen forbliver aktiv', async () => {
    let runId = 'run-1'
    vi.mocked(api.getActiveRunSessions).mockImplementation(async () => [{ session_id: 's1', run_id: runId, status: 'working' }])
    vi.mocked(api.followRun).mockClear()
    try {
      render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      await waitFor(() => expect(api.followRun).toHaveBeenCalledTimes(1))
      expect(api.followRun).toHaveBeenLastCalledWith(
        expect.anything(), 's1', expect.any(Function), expect.any(Function), 'run-1')
      runId = 'run-2'
      await waitFor(() => expect(api.followRun).toHaveBeenCalledTimes(2), { timeout: 10000 })
      expect(api.followRun).toHaveBeenLastCalledWith(
        expect.anything(), 's1', expect.any(Function), expect.any(Function), 'run-2')
    } finally {
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    }
  }, 12000)

  it('kobler passiv desk-stream på igen efter et netværksbrud', async () => {
    let onDone: Parameters<typeof api.followRun>[3] | undefined
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([{ session_id: 's1', run_id: 'run-1', status: 'working' }])
    vi.mocked(api.followRun).mockClear()
    vi.mocked(api.followRun).mockImplementation((_cfg, _sid, _onEvent, done) => {
      onDone = done
      return { abort: vi.fn(), getOffset: () => 0, getRunId: () => 'run-1' }
    })
    try {
      render(
        <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
          <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
            <ChatView sessionId="s1" />
          </PanelProvider></PermissionProvider></StreamProvider>
        </SessionProvider></SettingsProvider>,
      )
      await waitFor(() => expect(api.followRun).toHaveBeenCalledTimes(1))
      act(() => onDone?.('error'))
      await waitFor(() => expect(api.followRun).toHaveBeenCalledTimes(2), { timeout: 4000 })
    } finally {
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
      vi.mocked(api.followRun).mockImplementation(() => ({ abort: vi.fn(), getOffset: () => 0, getRunId: () => null }))
    }
  }, 6000)

  it('viser pause_and_ask over chatten i stedet for inde i den scrollbare transcript', async () => {
    const { container } = render(
      <SettingsProvider initialConfig={cfg}>
        <SessionProvider config={cfg}>
          <StreamProvider config={cfg}>
            <PermissionProvider>
              <PanelProvider defaultWidth={400}>
                <ChatView sessionId="s1" />
              </PanelProvider>
            </PermissionProvider>
          </StreamProvider>
        </SessionProvider>
      </SettingsProvider>,
    )
    await userEvent.type(screen.getByRole('textbox'), 'fortsæt{Enter}')
    const result = JSON.stringify({
      kind: 'pause_and_ask',
      question: 'Hvilken vej skal jeg tage?',
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
    expect(pauseCard).toBeInTheDocument()
    expect(container.querySelector('.transcript .pauseask')).not.toBeInTheDocument()
    expect(container.querySelector('.composer-area .liveness')).not.toBeInTheDocument()
    expect(screen.getByText('Hvilken vej skal jeg tage?')).toBeInTheDocument()
  })

  // ── Varslet om arbejde der aldrig blev faerdigt (24/9-2026) ──────────────
  //
  // `run_recovery` fandtes KUN som live SSE-event. Et run der blev opgivet i
  // gaar — eller mens processen var doed — fortalte derfor aldrig nogen om
  // det: indikatoren slukkede bare. Endpointet havde eksisteret i en uge med
  // nul kaldere, og banneret var tegnet og klar.
  const medEnBesked = () => vi.mocked(api.getSession).mockResolvedValue({
    etag: null, session: { id: 's1', title: 'T', updated_at: 'x' },
    messages: [{ id: 'u1', role: 'user', created_at: '2026-09-23T19:00:00Z', content: [{ type: 'text', text: 'Hej' }] }],
  })
  const nulstil = () => {
    vi.mocked(api.getSession).mockResolvedValue({ session: { id: 's1', title: 'T', updated_at: 'x' }, messages: [], etag: null })
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(null)
  }
  const visChat = () => render(
    <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
      <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
        <GenoptagelsesVarselHost sessionId="s1" />
        <ChatView sessionId="s1" />
      </PanelProvider></PermissionProvider></StreamProvider>
    </SessionProvider></SettingsProvider>,
  )

  it('henter varslet naar sessionen aabnes og viser det over composeren', async () => {
    medEnBesked()
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue({
      task_id: 't1', run_id: 'r1', state: 'recovering',
      reason: 'pending-tool-intent', recovery_attempt: 1, recovery_limit: 3,
      checkpoint_summary: '',
      notice: {
        state: 'recovering', reason: 'pending-tool-intent',
        message: 'Jarvis havde stadig et vaerktoejskald klar. Jarvis fortsaetter automatisk fra sit checkpoint.',
        continuing: true,
      },
    })
    try {
      const { container } = visChat()
      expect(await screen.findByText(/vaerktoejskald klar/)).toBeInTheDocument()
      expect(container.querySelector('.composer-area .recovery-notice')).toBeTruthy()
    } finally { nulstil() }
  })

  it('et OPGIVET run pulserer ikke — det ville ligne et levende', async () => {
    // `banner-reconnecting` har en pulserende prik der siger «der sker noget
    // lige nu». Paa et run der ER opgivet er det ikke bare grimt, det er
    // usandt.
    medEnBesked()
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue({
      task_id: 't2', run_id: 'r2', state: 'failed_terminal',
      reason: 'genoptagelses-vinduet udloeb', recovery_attempt: 3, recovery_limit: 3,
      checkpoint_summary: '',
      notice: {
        state: 'failed_terminal', reason: 'genoptagelses-vinduet udloeb',
        message: 'Opgaven naaede aldrig at blive genoptaget inden for et doegn. Skriv den igen hvis den stadig skal laves.',
        continuing: false,
      },
    })
    try {
      const { container } = visChat()
      expect(await screen.findByText(/aldrig at blive genoptaget/)).toBeInTheDocument()
      const b = container.querySelector('.recovery-notice .banner')
      expect(b).not.toHaveClass('banner-reconnecting')
      expect(b).toHaveClass('banner-warn')
    } finally { nulstil() }
  })

  it('henter IGEN naar en tur slutter — varslet kan vaere opstaaet imens', async () => {
    // DEN VIRKELIGE FEJL, maalt paa «hey..» 24/9-2026.
    //
    // Der blev spurgt én gang pr. session pr. komponent-levetid. Bjoerns desk
    // havde samtalen aaben i timer; varslerne opstod kl. 20:29. Foerste (og
    // eneste) forespoergsel skete laenge foer og fandt ingenting — saa syv
    // ulaeste varsler blev aldrig vist.
    //
    // Min foerste test af dette var VACUOUS: den lod komponenten hente mens
    // status stadig var `idle`, saa den bestod ogsaa med den gamle betingelse.
    // Denne starter med INTET varsel, koerer en tur, og lader varslet opstaa
    // derefter.
    medEnBesked()
    vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue(null)
    vi.mocked(api.hentGenoptagelsesVarsel).mockClear()
    try {
      visChat()
      expect(await screen.findByText('Hej')).toBeInTheDocument()
      const foerste = vi.mocked(api.hentGenoptagelsesVarsel).mock.calls.length

      // NU opstaar varslet — som da oprydningen skabte dem kl. 20:29.
      vi.mocked(api.hentGenoptagelsesVarsel).mockResolvedValue({
        task_id: 't4', run_id: 'r4', state: 'failed_terminal',
        reason: 'opgivet efter aftale', recovery_attempt: 3, recovery_limit: 3,
        checkpoint_summary: '',
        notice: {
          state: 'failed_terminal', reason: 'opgivet efter aftale',
          message: 'Opgaven blev opgivet efter aftale. Skriv den igen hvis den stadig skal laves.',
          continuing: false,
        },
      })

      // En tur koerer og slutter. `handlersRef` saettes foerst naar `send()`
      // kalder `startStream` — derfor skal der SENDES, ikke bare fyres events.
      // (Min foerste udgave fyrede events uden at sende, saa handleren var null
      // og intet skete. Testen maalte sin egen attrap.)
      await userEvent.type(screen.getByRole('textbox'), 'koer{Enter}')
      await act(async () => {
        handlersRef.current?.onRunId('r9')
        handlersRef.current?.onEvent({
          type: 'message_start',
          message: { id: 'r9', model: 'm', provider: 'p', lane: 'l',
                     session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } },
        })
        await new Promise((r) => setTimeout(r, 150))
        handlersRef.current?.onEvent({ type: 'message_stop' })
        await new Promise((r) => setTimeout(r, 250))
      })

      expect(vi.mocked(api.hentGenoptagelsesVarsel).mock.calls.length).toBeGreaterThan(foerste)
      expect(await screen.findByText(/opgivet efter aftale/)).toBeInTheDocument()
    } finally { nulstil() }
  })

  it('spoerger kun EN gang pr. session — serveren kvitterer varslet', async () => {
    // Varslet FORBRUGES naar det hentes, saa et gentaget kald ville tabe det
    // i stedet for at gentage det.
    medEnBesked()
    vi.mocked(api.hentGenoptagelsesVarsel).mockClear()
    try {
      const { rerender } = visChat()
      expect(await screen.findByText('Hej')).toBeInTheDocument()
      await act(async () => {
        rerender(
          <SettingsProvider initialConfig={cfg}><SessionProvider config={cfg}>
            <StreamProvider config={cfg}><PermissionProvider><PanelProvider defaultWidth={400}>
              <GenoptagelsesVarselHost sessionId="s1" />
              <ChatView sessionId="s1" />
            </PanelProvider></PermissionProvider></StreamProvider>
          </SessionProvider></SettingsProvider>,
        )
      })
      expect(vi.mocked(api.hentGenoptagelsesVarsel).mock.calls.filter((c) => c[1] === 's1').length).toBe(1)
    } finally { nulstil() }
  })

})
/**
 * Baggrundsjob i CHATTEN.
 *
 * Panelet fandtes kun i Code-visningen. Bjørn arbejder mest i chat, og der var
 * ingen vej til det overhovedet — derfor «hvorfor de ikk bliver vist
 * overhovede». En knap der ikke findes, kan ingen finde.
 */
describe('ChatView — baggrundsjob', () => {
  const vis = () => render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>
              <ChatView sessionId="s1" />
            </PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )

  it('har INGEN baggrundsjob-knap i chat-headeren', () => {
    // Bjørn 17/10-2026: «i header i chat mode bør ændrings panel og baggrunds
    // panel ikke vises». Indgangene hører i code mode; panelerne selv består.
    vis()
    expect(screen.queryByRole('button', { name: 'Vis/skjul baggrundsjob' })).not.toBeInTheDocument()
  })
})

describe('ChatView — ændringer og jobs i samme skinne', () => {
  const vis = () => render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>
              <ChatView sessionId="s1" />
            </PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )

  it('har hverken ændringer- eller baggrundsjob-ikon i chat-headeren', () => {
    vis()
    expect(screen.queryByRole('button', { name: 'Vis/skjul ændringer' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Vis/skjul baggrundsjob' })).not.toBeInTheDocument()
  })

  it('et gemt åbent ændringer-panel vises stadig — kun indgangen er væk', async () => {
    // Indgangen er fjernet fra chat-headeren, men tilstanden består: et panel
    // der var åbent før skiftet må ikke blive usynligt og ulukkeligt.
    localStorage.setItem('jarvis-desk:panel:changes', 'true')
    try {
      vis()
      expect(screen.getByRole('complementary', { name: 'Ændringer' })).toBeInTheDocument()
    } finally {
      localStorage.removeItem('jarvis-desk:panel:changes')
    }
  })
})

/**
 * Bund-fade'en i transcripten (Bjørn 17/9-2026).
 *
 * MÅLT: `padding-bottom` var 8px mod en 44px fade-zone, så den sidste linje
 * stod i 18–70% opacitet. Den så ud som om den gled bag liveness-linjen — men
 * den linje ligger UDEN FOR scroll-containeren. Det var masken selv.
 *
 * Fade'ens opgave er at sige «der er mere nedenfor». Står man i bunden, er der
 * ikke — og så skal den ikke æde den sidste linje.
 */
describe('ChatView — bund-fade', () => {
  // Transcripten findes kun i en AKTIV samtale — den tomme visning har sin
  // egen (GreetingHero, ChatView.tsx:653). Én sendt besked gør den aktiv.
  const vis = async () => {
    const r = render(
      <SettingsProvider initialConfig={cfg}>
        <SessionProvider config={cfg}>
          <StreamProvider config={cfg}>
            <PermissionProvider>
              <PanelProvider defaultWidth={400}>
                <ChatView sessionId="s1" />
              </PanelProvider>
            </PermissionProvider>
          </StreamProvider>
        </SessionProvider>
      </SettingsProvider>,
    )
    await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
    return r
  }

  const maal = (t: HTMLElement, scrollHeight: number, clientHeight: number, scrollTop: number) => {
    Object.defineProperty(t, 'scrollHeight', { value: scrollHeight, configurable: true })
    Object.defineProperty(t, 'clientHeight', { value: clientHeight, configurable: true })
    t.scrollTop = scrollTop
    act(() => { t.dispatchEvent(new Event('scroll')) })
  }

  // Follow-ejerskabet afgøres ikke straks længere (29/9-2026): et læser-input
  // afregnes ved `scrollend` — eller efter 500 ms. Testene skal derfor LUKKE
  // gesten, ellers måler de en tilstand der endnu ikke er afgjort.
  const slut = (t: HTMLElement) => {
    act(() => { t.dispatchEvent(new Event('scrollend')) })
  }

  it('slukker bund-fade naar man staar i bunden', async () => {
    const { container } = await vis()
    const t = container.querySelector('.transcript') as HTMLElement
    expect(t).toBeInTheDocument()
    // atBottom starter true: der er ikke noget nedenfor at tone ud
    expect(t.className).toContain('is-at-bottom')
  })

  it('taender den igen naar man scroller op — der ER mere nedenfor', async () => {
    const { container } = await vis()
    const t = container.querySelector('.transcript') as HTMLElement
    maal(t, 1000, 300, 700) // staar i bunden
    slut(t)
    expect(t.className).toContain('is-at-bottom')
    // 1000 indhold, 300 synligt, til toppen → 700px ned til bunden
    maal(t, 1000, 300, 0)
    slut(t)
    expect(t.className).not.toContain('is-at-bottom')
  })

  it('regner 25 px fra gulvet som bund — DSH-taersklen, ikke den gamle paa 120', async () => {
    const { container } = await vis()
    const t = container.querySelector('.transcript') as HTMLElement
    maal(t, 1000, 300, 700) // staar i bunden
    slut(t)
    expect(t.className).toContain('is-at-bottom')
    // 20px fra bunden → inden for DSH's 25px → stadig bund
    maal(t, 1000, 300, 680)
    slut(t)
    expect(t.className).toContain('is-at-bottom')
    // 50px fra bunden → over graensen → ikke bund
    maal(t, 1000, 300, 650)
    slut(t)
    expect(t.className).not.toContain('is-at-bottom')
  })

  // 17/9-nettet (spec'ens punkt 1a/1c, 29/9-2026): et svar kan lande ad en vej
  // hvor hverken stream-blokke, follow-blokke eller besked-antallet ændrer sig —
  // fx serverens gemte besked der ERSTATTER en linje, eller et autonomt run
  // hentet ind ved refresh. Kun interval-nettet ser det.
  it('holder bunden naar indholdet vokser uden en React-opdatering (17/9-nettet)', async () => {
    vi.mocked(api.getActiveRunSessions).mockResolvedValue([
      { session_id: 's1', run_id: 'remote-run', status: 'working' },
    ])
    try {
      const { container } = await vis()
      const t = container.querySelector('.transcript') as HTMLElement
      maal(t, 1000, 300, 700) // staar i bunden
      expect(t.className).toContain('is-at-bottom')

      Object.defineProperty(t, 'scrollHeight', { value: 1800, configurable: true })
      await act(async () => { await new Promise((r) => setTimeout(r, PIN_INTERVAL_MS + 80)) })

      expect(t.scrollTop).toBe(1800)
    } finally {
      // Uden oprydningen ser næste test et aktivt run og får «anden enhed»-badgen
      // — samme mønster som de to follow-stream-tests ovenfor.
      vi.mocked(api.getActiveRunSessions).mockResolvedValue([])
    }
  })
})

describe('ChatView — flaggede sideopgaver', () => {
  const skal = (sessionId: string | null) => (
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>
              <ChatView sessionId={sessionId} />
            </PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>
  )
  const opgave = { side_task_id: 'side-1', title: 'Ryd op i docs', prompt: 'p', tldr: 'kort', status: 'pending', session_id: 's', created_at: 'x' }

  it('vises IKKE i chat-mode — kun i code (Bjørn 8/10-2026)', async () => {
    // «side-opgaver bør kun vises i code mode i desk.. ikk i chat mode».
    // Kortet hører til hvor der er et arbejdsområde at løse opgaven i.
    sideopgaver.liste = [opgave]
    const { container } = render(skal(null))
    await waitFor(() => expect(container.querySelector('.chatview')).not.toBeNull())
    expect(screen.queryByText('Ryd op i docs')).toBeNull()
    expect(container.querySelector('.sok-top-anker')).toBeNull()
    sideopgaver.liste = []
  })

  it('og heller ikke i en AKTIV chat', async () => {
    sideopgaver.liste = [opgave]
    render(skal('s1'))
    await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
    expect(document.querySelector('.chatview:not(.empty)')).not.toBeNull()
    expect(screen.queryByText('Ryd op i docs')).toBeNull()
    sideopgaver.liste = []
  })
})

/**
 * Jarvis' browser i chat-headeren.
 *
 * Knappen kom 21/9-2026 og havde ingen test — og netop derfor opdagede ingen
 * at code-fladen slet ikke fik den. Denne og dens tvilling i CodeView.test
 * holder de to flader sammen: glider den ene, falder den anden.
 */
describe('ChatView — Jarvis\' browser', () => {
  const vis = () => render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>
              <ChatView sessionId="s1" />
            </PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )

  it('har knappen i headeren, og den åbner ruden', async () => {
    vis()
    const knap = screen.getByRole('button', { name: "Vis/skjul Jarvis' browser" })
    expect(document.querySelector('.jbrowser')).not.toBeInTheDocument()
    await userEvent.click(knap)
    expect(document.querySelector('.jbrowser')).toBeInTheDocument()
  })
})

/**
 * Permission-vælgeren i CHAT-composeren (side-3e6e7612c0, 29/10-2026).
 *
 * MÅLT: `ChatView.tsx:775` sendte `showPermissions={false}` hårdkodet, mens
 * `CodeView.tsx:951` sender `true`. Vælgeren var fuldt implementeret i
 * Composer (default `true`, tegnet bag `{showPermissions && ...}`) og
 * PermissionContext var allerede serverkoblet til `chat_sessions.approval_mode`.
 * Den eneste grund til at den ikke fandtes i chat var den hårdkodede false —
 * så hvert eneste tool-kald i chat mode krævede et godkendelses-kort.
 *
 * Gatingen er `auth?.role === 'owner'`: et medlem må ikke kunne give sig selv
 * fuld adgang. `isOwner` blev ALLEREDE sendt syv linjer nedenunder, så der
 * kræves intet nyt data — kun at det samme svar bruges på begge felter.
 */
describe('ChatView — permission-vælger (owner-only)', () => {
  const vis = () => render(
    <SettingsProvider initialConfig={cfg}>
      <SessionProvider config={cfg}>
        <StreamProvider config={cfg}>
          <PermissionProvider>
            <PanelProvider defaultWidth={400}>
              <ChatView sessionId="s1" />
            </PanelProvider>
          </PermissionProvider>
        </StreamProvider>
      </SessionProvider>
    </SettingsProvider>,
  )

  const somRolle = (role: 'owner' | 'member') => {
    vi.mocked(api.whoami).mockResolvedValue({
      user_id: 'u', display_name: 'Test', role,
    } as never)
  }

  afterEach(() => {
    // Gendan ejer-rollen: de øvrige tests i filen forudsætter den.
    somRolle('owner')
  })

  it('owner ser permission-vælgeren i chat-composeren', async () => {
    somRolle('owner')
    const { container } = vis()
    // Auth kommer asynkront fra whoami — vælgeren kan først tegnes derefter.
    await waitFor(() => {
      expect(container.querySelector('.composer-perm')).toBeInTheDocument()
    })
  })

  it('et medlem ser den IKKE — fuld adgang må ikke kunne vælges af ikke-ejer', async () => {
    somRolle('member')
    const { container } = vis()
    // Vent til auth faktisk er landet, ellers er fraværet tomt og beviser intet.
    await waitFor(() => {
      expect(container.querySelector('.composer-shell')).toBeInTheDocument()
    })
    await act(() => new Promise<void>((r) => setTimeout(r, 150)))
    expect(container.querySelector('.composer-perm')).not.toBeInTheDocument()
  })
})
