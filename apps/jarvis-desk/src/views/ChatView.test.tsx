import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatView } from './ChatView'
import { SessionProvider } from '../contexts/SessionContext'
import { StreamProvider } from '../contexts/StreamContext'
import { SettingsProvider } from '../contexts/SettingsContext'
import { PanelProvider } from '../contexts/PanelContext'
import { PermissionProvider } from '../contexts/PermissionContext'
import * as api from '../lib/api'

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
  // warmSession kom til i api.ts uden at mocken fulgte med — testen har
  // vaeret roed siden. Ikke en aegte fejl, men en roed suite skjuler den
  // naeste der ER aegte.
  warmSession: vi.fn().mockResolvedValue(undefined),
  followRun: vi.fn(() => ({ abort: vi.fn() })),
  // Opsamlingen af et ventende godkendelses-kort (20/9-2026): uden den
  // i mocken falder hele viewet, fordi StreamContext kalder den.
  hentVentendeGodkendelse: vi.fn(async () => null),
  hentVentendeGodkendelseOveralt: vi.fn(async () => null),
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

describe('ChatView integration', () => {
  it('viser komprimering over composer selv når samtalen er i hvile', async () => {
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
      expect(await screen.findByText(/Komprimerer kontekst/)).toBeInTheDocument()
      expect(container.querySelector('.composer-area .liveness')).toHaveClass('is-compacting')
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
    render(
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
    expect(screen.getByText('hej')).toBeInTheDocument()
    act(() => {
      handlersRef.current?.onRunId('r1')
      handlersRef.current?.onEvent({ type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'l', session_id: 's1', usage: { input_tokens: 0, output_tokens: 0 } } })
      handlersRef.current?.onEvent({ type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
      handlersRef.current?.onEvent({ type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'svar' } })
    })
    expect(await screen.findByText('svar')).toBeInTheDocument()
  })

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
    const liveness = container.querySelector('.liveness')
    expect(pauseCard).toBeInTheDocument()
    expect(container.querySelector('.transcript .pauseask')).not.toBeInTheDocument()
    expect(pauseCard!.compareDocumentPosition(liveness!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByText('Hvilken vej skal jeg tage?')).toBeInTheDocument()
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

  it('har en knap til baggrundsjob i headeren', () => {
    vis()
    expect(screen.getByRole('button', { name: 'Vis/skjul baggrundsjob' })).toBeInTheDocument()
  })

  it('knappen åbner ruden', async () => {
    vis()
    expect(screen.queryByRole('complementary', { name: 'Baggrundsjob' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul baggrundsjob' }))
    expect(screen.getByRole('complementary', { name: 'Baggrundsjob' })).toBeInTheDocument()
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

  it('har et ændringer-ikon ved siden af baggrundsjob', () => {
    vis()
    expect(screen.getByRole('button', { name: 'Vis/skjul ændringer' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Vis/skjul baggrundsjob' })).toBeInTheDocument()
  })

  it('de to ruder kan stå SAMMEN i skinnen', async () => {
    vis()
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul ændringer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul baggrundsjob' }))
    expect(screen.getByRole('complementary', { name: 'Ændringer' })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: 'Baggrundsjob' })).toBeInTheDocument()
  })

  it('og hver for sig', async () => {
    vis()
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul ændringer' }))
    expect(screen.getByRole('complementary', { name: 'Ændringer' })).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: 'Baggrundsjob' })).not.toBeInTheDocument()
  })

  it('headeren gør plads KUN når skinnen er åben', async () => {
    const { container } = vis()
    expect(container.querySelector('.chatview.har-skinne')).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul ændringer' }))
    expect(container.querySelector('.chatview.har-skinne')).not.toBeNull()
    // Lukkes den igen, skal pladsen gives tilbage — ellers står headeren
    // permanent skubbet ind med et tomt felt til højre.
    await userEvent.click(screen.getByRole('button', { name: 'Vis/skjul ændringer' }))
    expect(container.querySelector('.chatview.har-skinne')).toBeNull()
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
    // 1000 indhold, 300 synligt, staar i toppen → 700px ned til bunden
    maal(t, 1000, 300, 0)
    expect(t.className).not.toContain('is-at-bottom')
  })

  it('regner naer-bunden som bund (NEAR_BOTTOM_PX = 120)', async () => {
    const { container } = await vis()
    const t = container.querySelector('.transcript') as HTMLElement
    maal(t, 1000, 300, 0)
    expect(t.className).not.toContain('is-at-bottom')
    // 50px fra bunden → inden for graensen
    maal(t, 1000, 300, 650)
    expect(t.className).toContain('is-at-bottom')
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

  it('staar oeverst lige under headeren i en TOM chat', async () => {
    sideopgaver.liste = [opgave]
    const { container } = render(skal(null))
    expect(await screen.findByText('Ryd op i docs')).toBeInTheDocument()
    // Bjørn 19/9: «i toppen af chatview» — ankeret er headerens nabo.
    const head = container.querySelector('.chatview-head')!
    expect(head.nextElementSibling?.classList.contains('sok-top-anker')).toBe(true)
    sideopgaver.liste = []
  })

  it('og i en AKTIV chat', async () => {
    sideopgaver.liste = [opgave]
    render(skal('s1'))
    await userEvent.type(screen.getByRole('textbox'), 'hej{Enter}')
    expect(await screen.findByText('Ryd op i docs')).toBeInTheDocument()
    expect(document.querySelector('.chatview:not(.empty)')).not.toBeNull()
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
