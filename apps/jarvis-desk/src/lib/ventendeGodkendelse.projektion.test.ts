import { describe, it, expect } from 'vitest'
import type { ChatMessage } from './api'
import { fletGodkendelser } from './godkendelseIFolden'
import { medVentendeGodkendelse } from './ventendeGodkendelse'

/** Den hentede ventende godkendelse skal STÅ i transcriptet (16/11-2026).
 *
 *  Før lå den kun i `pendingApproval` og blev tegnet i `.composer-notices` —
 *  «oven på turen» — når den persisterede række manglede (fail-open
 *  persistering, refresh der halter). */
const ventende = { approvalId: 'a1', tool: 'exec_command', action: 'rm -rf /tmp/x', sessionId: 's1' }

const bruger: ChatMessage = { id: 'u1', role: 'user', content: [{ type: 'text', text: 'ryd op' }], created_at: '2026-11-16T10:00:00Z' }
const raekke = (status: string): ChatMessage => ({
  id: `r-${status}`, role: 'approval_request', content: [], created_at: '2026-11-16T10:00:01Z',
  content_json: [{ approval_id: 'a1', tool: 'exec_command', action: 'rm -rf /tmp/x', status }],
})
const godkendelser = (l: readonly ChatMessage[]) => l.filter((m) => m.role === 'approval_request')

describe('medVentendeGodkendelse', () => {
  it('(a) viser en hentet pending uden persisteret række — som række efter turen', () => {
    const ud = fletGodkendelser(medVentendeGodkendelse([bruger], ventende, 's1'))
    expect(godkendelser(ud)).toHaveLength(1)
    expect(ud[ud.length - 1]?.role).toBe('approval_request')
    expect((ud[ud.length - 1]?.content_json as Array<{ approval_id: string; status: string }>)[0])
      .toMatchObject({ approval_id: 'a1', status: 'pending' })
  })

  it('(b) viser ÉN når rækken også er persisteret', () => {
    const ud = fletGodkendelser(medVentendeGodkendelse([bruger, raekke('pending')], ventende, 's1'))
    expect(godkendelser(ud)).toHaveLength(1)
    expect(godkendelser(ud)[0]?.id).toBe('r-pending') // den persisterede vinder
  })

  it('(c) forsvinder når den godkendes (pending → null)', () => {
    expect(godkendelser(medVentendeGodkendelse([bruger], ventende, 's1'))).toHaveLength(1)
    expect(godkendelser(medVentendeGodkendelse([bruger], null, 's1'))).toHaveLength(0)
  })

  it('rører ikke listen når kortet hører til en anden session', () => {
    expect(godkendelser(medVentendeGodkendelse([bruger], ventende, 'andet'))).toHaveLength(0)
  })
})
