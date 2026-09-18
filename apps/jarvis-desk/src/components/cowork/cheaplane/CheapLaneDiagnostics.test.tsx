/**
 * Diagnostik og opbevaring.
 *
 * Fundene er deterministiske — samme tilstand giver samme fund — så fladen må
 * ikke omskrive dem til noget blødere. Et fund har en kode, en alvorlighed og
 * sit bevis, og beviset er dét der gør at man kan handle på det.
 *
 * Opbevaringen har én regel der ikke kan forhandles: redigerede payloads må
 * ikke ligge længere end metadata. En prompt er det mest private i systemet,
 * og en indstilling der lod den overleve sin egen metadata ville betyde at
 * ingen længere kunne se hvor den kom fra.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLaneDiagnostics } from './CheapLaneDiagnostics'
import { CheapLaneSettings } from './CheapLaneSettings'
import type { Diagnose } from '../../../lib/cheapLaneApi'

const diagnose: Diagnose = {
  generated_at: '2026-09-18T09:00:00Z',
  status: 'findings',
  findings: [
    { code: 'auth-profile-starvation', severity: 'high',
      evidence: { auth_profile: 'mistral', slots: 1 },
      first_observed_at: '2026-09-18T08:00:00Z', last_observed_at: '2026-09-18T09:00:00Z' },
    { code: 'quota-unknown', severity: 'low', evidence: { provider: 'groq' } },
  ],
}

beforeEach(() => { vi.restoreAllMocks() })

describe('CheapLaneDiagnostics', () => {
  it('viser fundets kode, alvorlighed OG bevis', () => {
    render(<CheapLaneDiagnostics diagnose={diagnose} revisioner={[]} />)
    expect(screen.getByText('auth-profile-starvation')).toBeTruthy()
    expect(screen.getByText('high')).toBeTruthy()
    // Beviset er det der goer fundet handlingsbart.
    expect(screen.getByText(/mistral/)).toBeTruthy()
  })

  it('de alvorligste står øverst', () => {
    render(<CheapLaneDiagnostics diagnose={diagnose} revisioner={[]} />)
    const koder = [...document.querySelectorAll('.cl-fund-kode')].map((n) => n.textContent)
    expect(koder[0]).toBe('auth-profile-starvation')
  })

  it('ingen fund er et SVAR, ikke en tom liste', () => {
    render(<CheapLaneDiagnostics diagnose={{ status: 'ok', findings: [] }} revisioner={[]} />)
    expect(screen.getByText(/ingen fund/i)).toBeTruthy()
  })

  it('revisionssporet viser hvem der gjorde hvad', () => {
    render(<CheapLaneDiagnostics diagnose={diagnose} revisioner={[
      { at: '2026-09-18T08:30:00Z', actor: 'owner', action: 'slot.pause',
        target: 'groq::llama', reason: 'for dyr', outcome: 'ok', revision: 'rev-3' },
    ]} />)
    expect(screen.getByText('slot.pause')).toBeTruthy()
    expect(screen.getByText(/for dyr/)).toBeTruthy()
  })
})

describe('CheapLaneSettings', () => {
  it('viser de gældende opbevaringstider', () => {
    render(<CheapLaneSettings metadataDage={60} payloadDage={7} udfoer={vi.fn()} />)
    expect((screen.getByLabelText(/metadata/i) as HTMLInputElement).value).toBe('60')
    expect((screen.getByLabelText(/payload/i) as HTMLInputElement).value).toBe('7')
  })

  it('afviser payload der lever længere end sin metadata', async () => {
    const udfoer = vi.fn()
    const bruger = userEvent.setup()
    render(<CheapLaneSettings metadataDage={60} payloadDage={7} udfoer={udfoer} />)
    await bruger.clear(screen.getByLabelText(/payload/i))
    await bruger.type(screen.getByLabelText(/payload/i), '90')
    await bruger.click(screen.getByRole('button', { name: /gem/i }))
    expect(screen.getByText(/ikke ligge længere end metadata/i)).toBeTruthy()
    expect(udfoer).not.toHaveBeenCalled()
  })

  it('gemmer kun når man selv trykker gem', async () => {
    const udfoer = vi.fn().mockResolvedValue({ status: 'ok' })
    const bruger = userEvent.setup()
    render(<CheapLaneSettings metadataDage={60} payloadDage={7} udfoer={udfoer} />)
    await bruger.clear(screen.getByLabelText(/payload/i))
    await bruger.type(screen.getByLabelText(/payload/i), '3')
    expect(udfoer).not.toHaveBeenCalled()
    await bruger.click(screen.getByRole('button', { name: /gem/i }))
    expect(udfoer).toHaveBeenCalledWith(expect.objectContaining({
      action: 'retention.set',
      parameters: expect.objectContaining({ payload_days: 3, metadata_days: 60 }),
    }))
  })
})
