import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { fletGodkendelser } from '../../lib/godkendelseIFolden'
import type { ChatMessage } from '../../lib/api'

/**
 * DEN RIGTIGE KOMPONENT, DE RIGTIGE RÆKKER (1/11-2026).
 *
 * `godkendelseIFolden.render.test.tsx` tegner `BlocksRenderer` direkte med
 * `model.workBlocks`. Det beviser at blokken kan tegnes — men ikke at den når
 * frem gennem `MessageRow` → `ChatFlowPresentation`, som er den vej appen
 * faktisk bruger. Bjørn så godkendelsen stå UDEN FOR folden mens den test var
 * grøn, så forskellen er ikke teoretisk.
 *
 * Rækkerne her er kopieret ordret fra `chat_messages` for session
 * chat-00f95aa5958342aabe0027fc6039befe kl. 11:44:08–11:44:19 den 1/11-2026:
 * pending-række, tool-række, approved-række, assistent-række.
 */

function raekke(over: Partial<ChatMessage> & { id: string; role: string }): ChatMessage {
  return {
    content: [],
    created_at: '2026-11-01T11:44:08+00:00',
    ...over,
  } as ChatMessage
}

const approvalBlok = (status: string) => [{
  type: 'approval',
  approval_id: 'approval-534e706621ac',
  tool: 'bash',
  action: 'rm -f /tmp/msg_weekday_times.txt',
  status,
  risk: 'destructive',
}]

const aegteRaekker: ChatMessage[] = [
  raekke({ id: 'u1', role: 'user', content: [{ type: 'text', text: 'slet lige noget fra tmp' }] }),
  raekke({ id: 'a1', role: 'approval_request', content_json: approvalBlok('pending') }),
  raekke({ id: 't1', role: 'tool' }),
  raekke({ id: 'a2', role: 'approval_request', content_json: approvalBlok('approved') }),
  raekke({
    id: 'm1',
    role: 'assistant',
    created_at: '2026-11-01T11:44:19+00:00',
    content: [
      { type: 'text', text: 'Jeg sletter en testfil i /tmp.', phase: 'commentary' },
      { type: 'tool_use', id: 'call_1', name: 'bash', input: { command: 'rm -f /tmp/x' } },
      { type: 'text', text: 'Slettet — men der kom intet godkendelseskort.' },
    ],
  }),
]

describe('godkendelsen når folden gennem MessageRow', () => {
  it('de to rækker bliver ÉN blok i turens arbejde — ikke to selvstændige', () => {
    const flettet = fletGodkendelser(aegteRaekker)
    expect(flettet.filter((m) => m.role === 'approval_request')).toHaveLength(0)
    const tur = flettet.find((m) => m.id === 'm1')!
    const approvalBlokke = tur.content.filter((b) => b.type === 'approval')
    expect(approvalBlokke).toHaveLength(1)
    expect((approvalBlokke[0] as { status: string }).status).toBe('approved')
  })

  it('MessageRow viser godkendelsen når arbejdet foldes ud', () => {
    const flettet = fletGodkendelser(aegteRaekker)
    const tur = flettet.find((m) => m.id === 'm1')!

    const { container } = render(
      <MessageRow
        presentation="chat"
        chatMode="calm"
        status="done"
        role="assistant"
        blocks={tur.content}
        density="compact"
        streaming={false}
      />,
    )

    // Folden er lukket som udgangspunkt — godkendelsen må ikke stå frit.
    expect(screen.queryByText(/Godkendt/)).toBeNull()

    // Åbn arbejdet: turhovedet ER knappen (`.rv-tur`), og den findes kun når
    // der er arbejde at folde ud. Den anden fold-knap (`.chat-flow-round-fold`)
    // hører til den LEVENDE runde og er ikke monteret på en afsluttet tur.
    const foldKnap = container.querySelector('button.rv-tur')
    expect(foldKnap).not.toBeNull()
    fireEvent.click(foldKnap as Element)

    // Nu skal linjen stå — inde i arbejdsdetaljerne, ikke som egen besked.
    const detaljer = container.querySelector('.chat-flow-work-details')
    expect(detaljer).not.toBeNull()
    expect(detaljer!.textContent).toMatch(/Godkendt/)
  })
})
