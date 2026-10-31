import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BlocksRenderer } from './BlocksRenderer'
import { fletGodkendelser } from '../../lib/godkendelseIFolden'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ChatMessage } from '../../lib/api'

/**
 * Kæden ende-til-ende: persisterede rækker → fletning → foldens arbejde →
 * ÉN synlig linje med den endelige status.
 *
 * MAALT 31/10-2026 (Bjørn, skærmbillede): to linjer stod som selvstændige
 * blokke midt i samtalen. `godkendelseIFolden.test.ts` beviser at de bliver
 * ÉN blok i `workBlocks`; her bevises at den blok faktisk TEGNER én linje —
 * ellers er «flettet sammen» kun en påstand om en datastruktur.
 */

function godkendelsesRaekke(id: string, status: string): ChatMessage {
  return {
    id,
    role: 'approval_request',
    content: [],
    created_at: '2026-10-31T15:57:36+00:00',
    content_json: [{
      type: 'approval',
      approval_id: 'ap-1',
      tool: 'bash',
      action: 'rm -rf /tmp/approval-probes',
      status,
      risk: 'destructive',
    }],
  }
}

describe('godkendelsen tegnes som ÉN linje i turens arbejde', () => {
  it('to persisterede rækker giver præcis én synlig linje med den endelige status', () => {
    const ind: ChatMessage[] = [
      { id: 'u1', role: 'user', content: [{ type: 'text', text: 'Prøv nu' }], created_at: '2026-10-31T15:57:30+00:00' },
      godkendelsesRaekke('a1', 'pending'),
      godkendelsesRaekke('a2', 'approved'),
      {
        id: 's1',
        role: 'assistant',
        content: [{ type: 'text', text: 'Slettet.' }],
        created_at: '2026-10-31T15:57:45+00:00',
      },
    ]

    const tur = fletGodkendelser(ind).find((m) => m.id === 's1')!
    const model = deriveChatFlow({
      blocks: tur.content,
      finalAnswerStarted: true,
      status: 'done',
    })

    render(<BlocksRenderer blocks={model.workBlocks} density="compact" streaming={false} />)

    // Afgørelsen står — ikke anmodningen. Én linje, ikke to.
    expect(screen.getAllByText(/Godkendt/)).toHaveLength(1)
    expect(screen.queryByText(/Afventer/)).toBeNull()
    // Selve kommandoen er med, så man kan se HVAD der blev godkendt.
    expect(screen.getAllByText(/rm -rf \/tmp\/approval-probes/).length).toBeGreaterThan(0)
  })

  it('en AFVIST godkendelse vises som afvist — ikke som godkendt', () => {
    const ind: ChatMessage[] = [
      { id: 'u1', role: 'user', content: [], created_at: '2026-10-31T15:57:30+00:00' },
      godkendelsesRaekke('a1', 'pending'),
      godkendelsesRaekke('a2', 'denied'),
      { id: 's1', role: 'assistant', content: [{ type: 'text', text: 'Ok.' }], created_at: '2026-10-31T15:57:45+00:00' },
    ]
    const tur = fletGodkendelser(ind).find((m) => m.id === 's1')!
    const model = deriveChatFlow({ blocks: tur.content, finalAnswerStarted: true, status: 'done' })
    render(<BlocksRenderer blocks={model.workBlocks} density="compact" streaming={false} />)
    expect(screen.getAllByText(/Afvist/)).toHaveLength(1)
    expect(screen.queryByText(/Godkendt/)).toBeNull()
  })
})
