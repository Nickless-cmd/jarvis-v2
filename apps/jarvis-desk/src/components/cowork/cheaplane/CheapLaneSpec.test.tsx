/**
 * De krav i speccen der ikke var bygget endnu (fundet ved gennemgangen 18/9).
 *
 * Hver af dem er en sætning i «Acceptance Criteria» eller i afsnittet om den
 * enkelte fane — ikke en idé jeg fik undervejs.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLaneTilfoej } from './CheapLaneTilfoej'
import { CheapLaneBalancer } from './CheapLaneBalancer'
import { CheapLaneDiagnostics } from './CheapLaneDiagnostics'
import type { BalancerSlot } from '../../../lib/cheapLaneApi'

beforeEach(() => { vi.restoreAllMocks() })

describe('CheapLaneTilfoej — «adding a provider creates its model directly in the cheap lane»', () => {
  it('sender ALTID lane: cheap — der er ingen vælger', async () => {
    const udfoer = vi.fn().mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLaneTilfoej udfoer={udfoer} />)
    await bruger.click(screen.getByRole('button', { name: /tilføj udbyder/i }))
    await bruger.type(screen.getByLabelText('Udbyder'), 'groq')
    await bruger.type(screen.getByLabelText('Model'), 'llama-3.3-70b')
    await bruger.click(screen.getByRole('button', { name: 'Tilføj' }))
    expect(udfoer).toHaveBeenCalledWith(expect.objectContaining({
      action: 'provider.add',
      parameters: expect.objectContaining({ lane: 'cheap', provider: 'groq' }),
    }))
    // En lane-vælger ville vaere en vej til at oprette noget i den SYNLIGE
    // lane fra et panel der hedder «cheap».
    expect(screen.queryByLabelText(/lane/i)).toBeNull()
  })

  it('nøglen ryddes straks — også når serveren afviste', async () => {
    const udfoer = vi.fn().mockRejectedValue(new Error('afvist'))
    const bruger = userEvent.setup()
    render(<CheapLaneTilfoej udfoer={udfoer} />)
    await bruger.click(screen.getByRole('button', { name: /tilføj udbyder/i }))
    await bruger.type(screen.getByLabelText('Udbyder'), 'groq')
    await bruger.type(screen.getByLabelText('Model'), 'm')
    const felt = screen.getByLabelText(/api-nøgle/i) as HTMLInputElement
    await bruger.type(felt, 'hemmelig-noegle')
    expect(felt.type).toBe('password')
    await bruger.click(screen.getByRole('button', { name: 'Tilføj' }))
    expect(felt.value).toBe('')
  })
})

describe('CheapLaneBalancer — «provider, status, profile, egress, and health filters»', () => {
  const slots: BalancerSlot[] = [
    { slot_id: 'a', provider: 'groq', model: 'm1', auth_profile: 'primary', egress: 'direct',
      status: 'healthy', weight: 0.8, breaker_level: 0 },
    { slot_id: 'b', provider: 'kilo', model: 'm2', auth_profile: 'anden', egress: 'vpn',
      status: 'cooldown', weight: 0, breaker_level: 2, cooldown_reason: 'fejl' },
  ]
  const opsæt = () => {
    render(<CheapLaneBalancer slots={slots} udfoer={vi.fn()} simuler={vi.fn()} />)
    return userEvent.setup()
  }

  it.each([
    ['Udbyder', 'groq', 'm1'],
    ['Profil', 'anden', 'm2'],
    ['Egress', 'vpn', 'm2'],
  ])('filtrerer på %s', async (etiket, værdi, forventet) => {
    const bruger = opsæt()
    await bruger.selectOptions(screen.getByLabelText(etiket), værdi)
    expect(screen.getByText(new RegExp(forventet))).toBeTruthy()
  })

  it('«helbred» er ikke det samme som status', async () => {
    // Et slot kan staa som healthy og stadig vaere ude af spil. Filteret
    // svarer paa «hvad kan vaelges NU», ikke paa hvad etiketten siger.
    const bruger = opsæt()
    await bruger.selectOptions(screen.getByLabelText('Helbred'), 'blokeret')
    expect(screen.getByRole('button', { name: /kilo/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /groq/ })).toBeNull()
  })

  it('routing-vægten er bundet til trin man kan kalibrere', async () => {
    const udfoer = vi.fn().mockResolvedValue({ status: 'ok' })
    render(<CheapLaneBalancer slots={slots} udfoer={udfoer} simuler={vi.fn()} />)
    const bruger = userEvent.setup()
    await bruger.click(screen.getByRole('button', { name: /groq \/ m1/ }))
    await bruger.click(screen.getByRole('button', { name: 'Vælg sjældnere' }))
    expect(udfoer).toHaveBeenCalledWith(expect.objectContaining({
      action: 'routing-bias.set', parameters: { routing_bias: -0.5 },
    }))
  })
})

describe('CheapLaneDiagnostics — «Cheap Lane-related Central incidents … in a single timeline»', () => {
  it('viser Centrals hændelser sammen med fundene', () => {
    render(<CheapLaneDiagnostics
      diagnose={{ status: 'findings', findings: [
        { code: 'quota-unknown', severity: 'low', evidence: {} }] }}
      revisioner={[]}
      central={[{ id: '1', ts: '2026-09-18T09:00:00Z', severity: 'warning',
                  message: 'cheap lane breaker åbnede for groq' }]}
      pakkeUrl="http://x/mc/cheap-lane/diagnostics/export?hours=24" />)
    expect(screen.getByText('quota-unknown')).toBeTruthy()
    expect(screen.getByText(/breaker åbnede for groq/)).toBeTruthy()
    const link = screen.getByRole('link', { name: /diagnose-pakken/i }) as HTMLAnchorElement
    expect(link.href).toContain('/diagnostics/export')
    // Pakken hentes gennem serveren — den skal ikke baere en token i URL'en.
    expect(link.href).not.toMatch(/token|key|bearer/i)
  })
})

import { CheapLaneTabel, Status } from './CheapLaneTabel'
import { CheapLaneChart } from './CheapLaneChart'

describe('CheapLaneTabel — «sticky headers, stable column widths, sort controls»', () => {
  const raekker = [
    { id: 'a', navn: 'zulu', tal: 3 },
    { id: 'b', navn: 'alfa', tal: 10 },
    { id: 'c', navn: 'midt', tal: undefined as number | undefined },
  ]
  const kolonner = [
    { id: 'navn', navn: 'Navn', vaerdi: (r: typeof raekker[0]) => r.navn, celle: (r: typeof raekker[0]) => r.navn },
    { id: 'tal', navn: 'Tal', vaerdi: (r: typeof raekker[0]) => r.tal, celle: (r: typeof raekker[0]) => String(r.tal ?? '–') },
  ]
  const navne = () => [...document.querySelectorAll('tbody th')].map((n) => n.textContent)

  it('sorterer på klik og vender ved andet klik', async () => {
    const bruger = userEvent.setup()
    render(<CheapLaneTabel raekker={raekker} kolonner={kolonner} noegle={(r) => r.id} />)
    await bruger.click(screen.getByRole('button', { name: /Navn/ }))
    expect(navne()).toEqual(['alfa', 'midt', 'zulu'])
    await bruger.click(screen.getByRole('button', { name: /Navn/ }))
    expect(navne()).toEqual(['zulu', 'midt', 'alfa'])
  })

  it('«ved ikke» er ikke den højeste værdi — den står nederst begge veje', async () => {
    const bruger = userEvent.setup()
    render(<CheapLaneTabel raekker={raekker} kolonner={kolonner} noegle={(r) => r.id} />)
    await bruger.click(screen.getByRole('button', { name: /Tal/ }))
    expect(navne().at(-1)).toBe('midt')
    await bruger.click(screen.getByRole('button', { name: /Tal/ }))
    expect(navne().at(-1)).toBe('midt')
  })

  it('melder sin sorteringsretning til skærmlæseren', async () => {
    const bruger = userEvent.setup()
    render(<CheapLaneTabel raekker={raekker} kolonner={kolonner} noegle={(r) => r.id} />)
    await bruger.click(screen.getByRole('button', { name: /Navn/ }))
    expect(screen.getByRole('columnheader', { name: /Navn/ }).getAttribute('aria-sort')).toBe('ascending')
  })
})

describe('Status — «icon, label, and tone, never color alone»', () => {
  it('bærer både tegn og ord', () => {
    render(<Status status="cooldown" />)
    const el = document.querySelector('.cl-status')!
    expect(el.textContent).toContain('cooldown')
    expect(el.textContent!.replace('cooldown', '').trim().length).toBeGreaterThan(0)
  })
})

describe('CheapLaneChart — «empty/loading/error states»', () => {
  const serier = [{ key: 'Kald', navn: 'Kald', farve: '#0f0' }]

  it('skelner mellem «henter», «ingen målinger» og «kunne ikke læses»', () => {
    const { rerender } = render(<CheapLaneChart titel="Kald" punkter={[]} serier={serier} henter />)
    expect(screen.getByText(/henter/i)).toBeTruthy()

    rerender(<CheapLaneChart titel="Kald" punkter={[]} serier={serier} />)
    expect(screen.getByText(/ingen målinger/i)).toBeTruthy()

    // «Ingen maalinger» ville vaere en loegn her: vi VED ikke om der var nogen.
    rerender(<CheapLaneChart titel="Kald" punkter={[]} serier={serier} fejl="kilden svarede ikke" />)
    expect(screen.getByRole('alert').textContent).toContain('kilden svarede ikke')
    expect(screen.queryByText(/ingen målinger/i)).toBeNull()
  })
})
