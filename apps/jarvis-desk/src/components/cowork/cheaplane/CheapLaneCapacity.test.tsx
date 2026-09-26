import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CheapLaneCapacity } from './CheapLaneCapacity'
import type { Kapacitet, KvoteVindue } from '../../../lib/cheapLaneApi'

const ukendt: KvoteVindue = {
  period: 'month', unit: 'tokens', provider: 'groq', auth_profile: 'primary',
  limit: null, used: 120, remaining: null, source: 'unknown', confidence: null, reset_at: null,
}
const kendt: KvoteVindue = {
  period: 'day', unit: 'requests', provider: 'kilo', auth_profile: 'primary',
  limit: 1000, used: 250, remaining: 750, source: 'provider', confidence: 0.9,
  reset_at: '2026-09-19T00:00:00Z',
}

describe('CheapLaneCapacity', () => {
  it('viser ukendt kapacitet som ukendt og bevarer målt forbrug', () => {
    render(<CheapLaneCapacity kapacitet={{ windows: [ukendt] }} />)
    expect(screen.getByText('Ukendt kapacitet')).toBeInTheDocument()
    expect(screen.getByText(/120 brugt/)).toBeInTheDocument()
    expect(screen.queryByText('0 %')).toBeNull()
  })

  it('viser brugt, grænse, rest og kilde når tallene findes', () => {
    render(<CheapLaneCapacity kapacitet={{ windows: [kendt] }} />)
    expect(screen.getByText(/250/)).toBeInTheDocument()
    expect(screen.getByText(/1\.000/)).toBeInTheDocument()
    expect(screen.getByText(/750 tilbage/)).toBeInTheDocument()
    expect(screen.getByText('provider')).toBeInTheDocument()
    expect(screen.getByText('25 %')).toBeInTheDocument()
  })

  it('holder tokens og kald i hver sit kvotevindue', () => {
    render(<CheapLaneCapacity kapacitet={{ windows: [ukendt, kendt] }} />)
    expect(screen.getByText('tokens denne måned')).toBeInTheDocument()
    expect(screen.getByText('kald i dag')).toBeInTheDocument()
  })

  it('forklarer manglende kvoter uden at skjule forbrug', () => {
    render(<CheapLaneCapacity kapacitet={{ windows: [] }} />)
    expect(screen.getByText(/Ingen tokenkvoter er registreret endnu/)).toBeInTheDocument()
  })

  it('viser målt ind/ud og konti uden registrerede kvoter', () => {
    const capacity = {
      windows: [],
      usage: {
        day: {
          start_at: '2026-09-26T00:00:00Z', end_at: '2026-09-27T00:00:00Z',
          input_tokens: 170, output_tokens: 70, total_tokens: 240,
          calls: 2, unmetered_calls: 0,
          profiles: [
            { provider: 'groq', auth_profile: 'default', account: 'account1', input_tokens: 100, output_tokens: 40, total_tokens: 140, calls: 1, unmetered_calls: 0 },
            { provider: 'groq', auth_profile: 'account2', account: 'account2', input_tokens: 70, output_tokens: 30, total_tokens: 100, calls: 1, unmetered_calls: 0 },
          ],
          accounts: [
            { account: 'account1', input_tokens: 100, output_tokens: 40, total_tokens: 140, calls: 1, unmetered_calls: 0 },
            { account: 'account2', input_tokens: 70, output_tokens: 30, total_tokens: 100, calls: 1, unmetered_calls: 0 },
          ],
        },
      },
      estimated_capacity: {
        day: {
          known_estimate_tokens: 1350, complete: false,
          unknown_members: [{ provider: 'mistral', auth_profile: 'default' }],
          profiles: [
            { provider: 'groq', auth_profile: 'default', daily_call_limit: 10, sample_calls: 1, mean_tokens_per_call: 100, remaining_calls: 9, estimated_tokens: 900 },
            { provider: 'groq', auth_profile: 'account2', daily_call_limit: 10, sample_calls: 1, mean_tokens_per_call: 50, remaining_calls: 9, estimated_tokens: 450 },
          ],
          end_at: '2026-09-27T00:00:00Z',
        },
        month: {
          known_estimate_tokens: 10000, complete: false, end_at: '2026-10-01T00:00:00Z',
          observed_7d_tokens: 700, observed_30d_run_rate: 3000,
          unknown_members: [], profiles: [],
        },
      },
    } as Kapacitet
    render(<CheapLaneCapacity kapacitet={capacity} />)
    expect(screen.getAllByText('Ind').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ud').length).toBeGreaterThan(0)
    expect(screen.getByText('240')).toBeInTheDocument()
    expect(screen.getByText(/1.350/)).toBeInTheDocument()
    expect(screen.getAllByText(/scenarie/i).length).toBeGreaterThan(0)
    expect(screen.getByText('Konto 1')).toBeInTheDocument()
    expect(screen.getByText('Konto 2')).toBeInTheDocument()
    expect(screen.getByText(/7-dages tempo/)).toBeInTheDocument()
    expect(screen.getByText(/3\.000/)).toBeInTheDocument()
  })

  it('viser gatewayens Ollama Cloud som konto 2', () => {
    render(<CheapLaneCapacity kapacitet={{
      windows: [],
      usage: {
        day: {
          start_at: '2026-09-26T00:00:00Z', end_at: '2026-09-27T00:00:00Z',
          input_tokens: 70, output_tokens: 30, total_tokens: 100,
          calls: 1, unmetered_calls: 0,
          profiles: [{
            provider: 'ollama-a2', auth_profile: 'default', account: 'account2',
            input_tokens: 70, output_tokens: 30, total_tokens: 100,
            calls: 1, unmetered_calls: 0,
          }],
          accounts: [{
            account: 'account2', input_tokens: 70, output_tokens: 30, total_tokens: 100,
            calls: 1, unmetered_calls: 0,
          }],
        },
      },
    }} />)
    expect(screen.getByText(/Ollama Cloud via llm-gateway/)).toBeInTheDocument()
  })
})
