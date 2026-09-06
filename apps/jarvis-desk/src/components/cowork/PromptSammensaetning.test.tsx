import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

const getRunPrompt = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getRunPrompt: (...a: unknown[]) => getRunPrompt(...a) }))

import { PromptSammensaetning } from './PromptSammensaetning'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('PromptSammensaetning', () => {
  // Krøllede parenteser med vilje: mockReset() returnerer selve mocken, og
  // vitest opfatter en returneret FUNKTION som teardown — så mocken blev kaldt
  // efter hver test og kastede sin egen rejection ud i ingenting.
  beforeEach(() => { getRunPrompt.mockReset() })

  it('viser sektionerne med andel og gør labels læsbare', async () => {
    getRunPrompt.mockResolvedValue({
      run_id: 'r1', found: true, answer_chars: 765, total_chars: 10339, section_count: 2,
      sections: [
        { label: 'SOUL.md', chars: 7705, pct: 74.5 },
        { label: 'Visible_chat_guidance_rules', chars: 2634, pct: 25.5 },
      ],
    })
    render(<PromptSammensaetning config={cfg} runId="r1" />)
    // Understregerne er en server-artefakt; de må ikke stå i UI.
    expect(await screen.findByText('Visible chat guidance rules')).toBeTruthy()
    expect(screen.getByText(/2 sektioner · 10k tegn · svar 765 tegn/)).toBeTruthy()
    expect(screen.getByText('74.5%')).toBeTruthy()
  })

  it('siger at posten mangler — ikke at prompten var tom', async () => {
    getRunPrompt.mockResolvedValue({ run_id: 'r1', found: false, sections: [] })
    render(<PromptSammensaetning config={cfg} runId="r1" />)
    expect(await screen.findByText(/ikke gemt for denne tur/)).toBeTruthy()
    expect(screen.getByText(/ikke at prompten var tom/)).toBeTruthy()
  })

  it('skjuler halen bag et tal i stedet for at rulle uendeligt', async () => {
    getRunPrompt.mockResolvedValue({
      run_id: 'r1', found: true, total_chars: 1000, section_count: 20,
      sections: Array.from({ length: 20 }, (_, i) => ({ label: `s${i}`, chars: 50, pct: 5 })),
    })
    render(<PromptSammensaetning config={cfg} runId="r1" />)
    expect(await screen.findByText('+ 8 mindre sektioner')).toBeTruthy()
  })

  it('siger til når kaldet fejler', async () => {
    // mockRejectedValue skaber promisen straks → uhåndteret rejection før kaldet.
    getRunPrompt.mockImplementation(() => Promise.reject(new Error('nede')))
    render(<PromptSammensaetning config={cfg} runId="r1" />)
    expect(await screen.findByText(/Kunne ikke hente/)).toBeTruthy()
  })
})
