import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../lib/api', () => ({
  getMindIndex: vi.fn().mockResolvedValue({
    index: [
      { section: 'overview', label: 'Oversigt', ready: true },
      { section: 'mind', label: 'Sind', ready: true },
      { section: 'decisions', label: 'Beslutninger', ready: true },
      { section: 'observability', label: 'Observabilitet', ready: true },
      { section: 'agency', label: 'Agentur', ready: true },
      { section: 'skills', label: 'Skills', ready: true },
      { section: 'council', label: 'Council', ready: true },
      { section: 'memory', label: 'Hukommelse', ready: true },
      { section: 'reflection', label: 'Refleksion', ready: true },
      { section: 'lab', label: 'Lab', ready: true },
      { section: 'hardening', label: 'Hærdning', ready: true },
      { section: 'fremtidig', label: 'Fremtidig', ready: false },
    ],
  }),
  getMindSection: vi.fn().mockImplementation((_c, section: string) => {
    if (section === 'mind') {
      return Promise.resolve({ summary: '2/3 systemer aktive', systems: [
        { system: 'inner_voice', active: true, summary: 'taler' },
        { system: 'dreams', active: false },
      ] })
    }
    if (section === 'decisions') {
      // Formen er taget fra det levende endpoint 2026-09-05, ikke gættet.
      return Promise.resolve({
        queue: { pending: 1, expired_unanswered: 31, answered: 0 },
        items: [
          { kind: 'initiative', id: 'init-1', text: 'Slå det seneste bash-run op',
            why: 'Jeg vil vide om det holdt.', actions: ['approve', 'reject'] },
          { kind: 'life_project', id: 'life-1', text: 'Build a steadier inner architecture',
            why: 'I want a longer thread of coherence.', actions: ['abandon'] },
        ],
      })
    }
    if (section === 'observability') {
      return Promise.resolve({
        feed: [], incidents: [],
        hollow_promises: {
          available: true, window_hours: 24, hollow_total: 31,
          guard_detected: 12, escaped: 19,
          models: [
            { model: 'deepseek-v4-flash-vision-exp', turns: 42, hollow: 24, hollow_pct: 57.1 },
            { model: 'deepseek-v4-flash', turns: 97, hollow: 7, hollow_pct: 7.2 },
          ],
        },
      })
    }
    if (section === 'agency') {
      // Målt fra central_hub.mind_section('agency') 3/11-2026.
      return Promise.resolve({
        active: true,
        map: {
          summary: { nodes: 9, bridges: 13, connected: 9, partial: 0, missing: 0,
            experimental: 4, dark_edges: 4 },
          nodes: [
            { id: 'senses', label: 'Senses', kind: 'input', state: 'active',
              summary: 'Visual memory, sensory archive, perceptual event engine.' },
            { id: 'emotion', label: 'Emotion', kind: 'state', state: 'active' },
          ],
          bridges: [
            { source: 'senses', target: 'emotion', status: 'connected',
              summary: 'Perceptual records create emotional anchors.' },
          ],
        },
        agents: {
          windows: { today: { calls: 0, cost_usd: 0 } },
          dispatches: { total: 0, by_status: {} },
          roster: [
            { model_key: 'mistral/ministral-3b-latest', provider: 'mistral',
              model: 'ministral-3b-latest', status: 'inactive' },
          ],
        },
      })
    }
    if (section === 'skills') {
      // Målt fra central_hub.mind_section('skills') 3/11-2026.
      return Promise.resolve({
        active: true,
        skill_count: 70,
        all_tags: ['design', 'code-review', 'quality'],
        skills: [
          { name: 'banner-design', description: 'Design banners for social media.',
            tags: ['design', 'media'], has_scripts: false },
          { name: 'code-review', description: 'Struktureret gennemgang af kode/PRs.',
            tags: ['code-review', 'quality'], has_scripts: true },
        ],
      })
    }
    if (section === 'council') {
      // Målt fra central_hub.mind_section('council') 3/11-2026 — tom men empty-safe.
      return Promise.resolve({
        convocations: 0, deadlocks: 0, escalations: 0, roles: {},
        split: { event: 0, ondemand: 0 }, recent: [], window: 'today',
        note: 'council_convene kan være tom indtil WS-C; håndteret empty-safe.',
        active: true,
      })
    }
    if (section === 'memory') {
      // Målt fra de fire builders 3/11-2026: body har 200 snapshots, density er
      // tom men ærlig, experiential kræver bruger-scope.
      return Promise.resolve({
        active: true,
        body: {
          snapshot_count: 200,
          latest: { context: 'hjerteslag, steady krop', sensation: 'let',
            intensity: 0.54, state: 'steady', strain_level: 'low' },
          summary: 'Jeg mindes en let fornemmelse fra hjerteslag, steady krop',
        },
        density: { total_notes: 0, promotable_count: 0, promoted_count: 0,
          promotion_threshold: 3, summary: 'Ingen density-noter endnu' },
        recall: { summary: '0 recall-empty events in last 24h (across 0 tools)',
          stats: { total: 0, window_hours: 24, by_tool: {} } },
        experiential: { active: false, status: 'unscoped', total_count: 0,
          summary: 'Experiential memory requires an authenticated user scope' },
      })
    }
    if (section === 'reflection') {
      // Målt fra build_jarvis_brain_reflection_surface 3/11-2026.
      return Promise.resolve({
        active: true,
        mode: 'daily-visible-reflection-slot',
        summary: { active_today: true, current_state: 'ready_for_reflection',
          chronicle_summary_available: true },
        items: [{ kind: 'reflection_envelope_preview',
          chronicle_summary: '(chronicle summary unavailable — refleksionen kører på fri hånd)',
          nudge_after_count: 3 }],
        allowed_effects: ['prompt_attention', 'request_visible_reflection',
          'do_not_write_memory_without_remember_this'],
      })
    }
    if (section === 'lab') {
      // Målt fra build_cost_surface 3/11-2026.
      return Promise.resolve({
        windows: {
          today: { calls: 7149, input_tokens: 140534739, output_tokens: 2333001,
            cache_hit_pct: 95.3, cost_usd: 2.2549 },
          '7d': { calls: 70078, cost_usd: 24.1013 },
        },
        breakdown: [{ provider: 'deepseek', calls: 7000, cost_usd: 2.1 }],
        deepseek_balance_usd: 42.5,
      })
    }
    if (section === 'hardening') {
      // Målt fra list_flags() 3/11-2026: 10 flag, heraf ét dangerous.
      return Promise.resolve({
        active: true, count: 10, dangerous_count: 1,
        flags: [
          { key: 'injection:rule_conclusions', label: 'Injection: rule conclusions',
            kind: 'bool', dangerous: false, value: true },
          { key: 'lag4_live', label: 'Lag-4 adaptation live', kind: 'bool',
            dangerous: true, value: true },
        ],
      })
    }
    return Promise.resolve({ status: 'green', coverage: { nerves: 116, clusters: 20 } })
  }),
  actOnDecision: vi.fn().mockResolvedValue({ ok: true }),
  pingServer: vi.fn().mockResolvedValue(20),  // ConnectionPill › useConnection
}))
vi.mock('../../lib/centralStream', () => ({
  subscribeCentralStream: vi.fn(() => () => {}),
}))

import { JarvisMind } from './JarvisMind'
import { actOnDecision, getMindIndex, getMindSection } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'

const CFG = { apiBaseUrl: 'http://x', authToken: 't' }

describe('JarvisMind', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('bygger sub-navbar fra hub-index (ét ground truth)', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindIndex).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Sind' })).toBeTruthy())
    expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy()
  })

  it('åbner den DELTE Central-stream for den levende puls', () => {
    render(<JarvisMind config={CFG} />)
    expect(subscribeCentralStream).toHaveBeenCalled()
  })

  it('default-fanen Sind henter sektion fra hub og viser surfaces', async () => {
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(getMindSection).toHaveBeenCalledWith(CFG, 'mind'))
    await waitFor(() => expect(screen.getByText(/inner voice/i)).toBeTruthy())
  })

  // Beslutnings-fanen er den ENESTE der ikke bare informerer. Uden knapper var
  // den bare endnu en visning — og 31 initiativer udløb netop ubesvarede fordi
  // ruterne fandtes uden at nogen kunne trykke.
  it('beslutnings-fanen giver ægte knapper, ikke bare en visning', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByText(/Slå det seneste bash-run op/)).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Godkend' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Afvis' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Læg den fra dig' })).toBeTruthy()
  })

  it('godkend rammer initiativ-ruten med slags og id', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Godkend' })).toBeTruthy())
    await userEvent.click(screen.getByRole('button', { name: 'Godkend' }))
    await waitFor(() =>
      expect(actOnDecision).toHaveBeenCalledWith(CFG, 'initiative', 'init-1', 'approve'))
  })

  it('viser tallet der gør ondt: de ubesvarede', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Beslutninger' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Beslutninger' }))
    await waitFor(() => expect(screen.getByText(/31 tidligere forslag udløb uden svar/)).toBeTruthy())
  })

  // Backenden talte de tomme løfter fra dag ét, men fanen renderede kun feed +
  // flag-antal — så tallet var usynligt uden at folde rå-laget ud.
  it('observabilitet VISER de tomme løfter, ikke kun i rå-laget', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Observabilitet' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Observabilitet' }))
    await waitFor(() => expect(screen.getByText('slap forbi værnet')).toBeTruthy())
    expect(screen.getByText('19')).toBeTruthy()
    expect(screen.getByText('57.1%')).toBeTruthy()
  })

  it('placeholder for pending-faner', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Fremtidig' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Fremtidig' }))
    expect(screen.getByText(/ikke endnu flyttet|endnu ikke flyttet/i)).toBeTruthy()
  })

  // De fire sektioner der stod som `pending` er nu projiceret oven på builders
  // der ALLEREDE fandtes. Payload-formerne er målt fra builderne 3/11-2026.
  it('hukommelse VISER krop, density og recall-huller', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Hukommelse' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Hukommelse' }))
    await waitFor(() => expect(screen.getByText('krops-minder')).toBeTruthy())
    expect(screen.getByText('200')).toBeTruthy()
    expect(screen.getByText(/hjerteslag, steady krop/)).toBeTruthy()
    expect(screen.getByText(/Ingen density-noter endnu/)).toBeTruthy()
    expect(document.querySelector('.jm-raw')).toBeNull()
  })

  it('refleksion VISER hvad den må røre — ikke bare at den kørte', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Refleksion' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Refleksion' }))
    await waitFor(() => expect(screen.getByText('Må røre')).toBeTruthy())
    expect(screen.getByText(/do not write memory without remember this/i)).toBeTruthy()
  })

  it('lab VISER saldoen først — forbrug uden saldo siger ikke om der er råd', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Lab' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Lab' }))
    await waitFor(() => expect(screen.getByText('saldo (USD)')).toBeTruthy())
    expect(screen.getByText('$42.50')).toBeTruthy()
    expect(screen.getByText('7149')).toBeTruthy()
  })

  it('hærdning VISER de farlige flag frem', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Hærdning' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Hærdning' }))
    await waitFor(() => expect(screen.getByText('Lag-4 adaptation live')).toBeTruthy())
    expect(screen.getByText('⚠ farlig')).toBeTruthy()
  })

  // 3/11-2026: agentur, council og skills var fuldt projiceret hele tiden, men
  // SectionView havde ingen gren for dem — så de faldt til rå JSON. Det var
  // ikke manglende data, det var manglende visning. Payload-formerne nedenfor
  // er målt fra de ægte builders (central_hub.mind_section), ikke opdigtede.
  it('agentur VISER kortet og rosteret, ikke rå JSON', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Agentur' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Agentur' }))
    await waitFor(() => expect(screen.getByText('Senses')).toBeTruthy())
    expect(screen.getByText('mørke kanter')).toBeTruthy()
    expect(screen.getByText('senses')).toBeTruthy()
    expect(screen.getByText('ministral-3b-latest')).toBeTruthy()
    expect(document.querySelector('.jm-raw')).toBeNull()
  })

  it('skills VISER listen og kan filtrere de 70 ned', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Skills' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Skills' }))
    await waitFor(() => expect(screen.getByText('code-review')).toBeTruthy())
    expect(screen.getByText('banner-design')).toBeTruthy()
    await userEvent.type(screen.getByLabelText('Søg i skills'), 'code-review')
    await waitFor(() => expect(screen.queryByText('banner-design')).toBeNull())
    expect(screen.getByText('code-review')).toBeTruthy()
  })

  it('council er empty-safe: tom fane siger det højt i stedet for at se død ud', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<JarvisMind config={CFG} />)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Council' })).toBeTruthy())
    await userEvent.click(screen.getByRole('tab', { name: 'Council' }))
    await waitFor(() => expect(screen.getByText(/Ingen councils/i)).toBeTruthy())
    expect(document.querySelector('.jm-raw')).toBeNull()
  })
})
