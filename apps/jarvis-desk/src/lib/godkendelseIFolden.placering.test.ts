import { describe, it, expect } from 'vitest'
import { fletGodkendelser } from './godkendelseIFolden'
import type { ChatMessage } from './api'
import type { ContentBlock } from './sseProtocol'

/**
 * PLACERINGEN — ikke bare «inde i folden» (2/11-2026).
 *
 * `fletGodkendelser` lagde blokken SIDST i turens indhold. Den havnede dermed
 * i folden, men ved den forkerte runde — og i code mode slet ikke i folden,
 * fordi `opdel` klassificerer alt efter sidste værktøjskald som svar.
 *
 * Bjørn, med skærmbillede af code mode: «Hvorfor vises de i bunden af din
 * besked? Du burde ligge inde i turhoved ved de runde linjer de høre til?»
 *
 * MÅLT mod `chat_messages` 2/11-2026: godkendelsens `action` er ORDRET lig
 * `input.command` på det `tool_use` den gjaldt (326 og 365 tegn, eksakt match
 * ved indeks [9] og [13] i den samme tur). Derfor kan placeringen udledes af
 * hvilket kald godkendelsen gjaldt — den skal ikke gættes.
 */

function raekke(id: string, role: ChatMessage['role'], ekstra: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id,
    role,
    content: [],
    created_at: '2026-11-02T15:51:23+00:00',
    ...ekstra,
  }
}

function godkendelse(id: string, approvalId: string, action: string, status = 'approved'): ChatMessage {
  return raekke(id, 'approval_request', {
    content_json: [{ type: 'approval', approval_id: approvalId, tool: 'bash', action, status }],
  })
}

function kald(id: string, kommando: string): ContentBlock {
  // Resultatet hænger på kaldet selv — `tool_result` er ikke en blok-type i
  // `ContentBlock`-unionen. Vitest kørte grønt med den, men `tsc -b` fangede
  // den; testen skal ikke kunne køre på en form produktionen ikke kan lave.
  return { type: 'tool_use', id, name: 'bash', input: { command: kommando }, status: 'done', result: '' }
}

function tur(blokke: ContentBlock[]): ChatMessage {
  return raekke('m1', 'assistant', { content: blokke })
}

describe('godkendelsen lægges ved det kald den gjaldt', () => {
  it('står umiddelbart FØR sit eget tool_use — ikke sidst i turen', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('g1', 'ap-forst', 'rm -rf /tmp/forst'),
      godkendelse('g2', 'ap-anden', 'rm -rf /tmp/anden'),
      tur([
        { type: 'text', text: 'Jeg rydder op.' },
        kald('call_1', 'rm -rf /tmp/forst'),
        kald('call_2', 'rm -rf /tmp/anden'),
        { type: 'text', text: 'Ryddet op.' },
      ]),
    ]

    const flettet = fletGodkendelser(ind)
    const content = flettet.find((m) => m.id === 'm1')!.content

    const forstKald = content.findIndex((b) => b.type === 'tool_use' && b.id === 'call_1')
    const andetKald = content.findIndex((b) => b.type === 'tool_use' && b.id === 'call_2')

    expect(content[forstKald - 1]).toMatchObject({ type: 'approval', approval_id: 'ap-forst' })
    expect(content[andetKald - 1]).toMatchObject({ type: 'approval', approval_id: 'ap-anden' })

    // Slutteksten skal stadig være den sidste — godkendelsen må ikke skubbe
    // svaret op eller lægge sig efter det.
    expect(content[content.length - 1]).toMatchObject({ type: 'text', text: 'Ryddet op.' })
  })

  it('to godkendelser for SAMME kommando rammer hvert sit kald', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('g1', 'ap-1', 'rm -rf /tmp/x'),
      godkendelse('g2', 'ap-2', 'rm -rf /tmp/x'),
      tur([
        kald('call_1', 'rm -rf /tmp/x'),
        kald('call_2', 'rm -rf /tmp/x'),
        { type: 'text', text: 'Færdig.' },
      ]),
    ]

    const content = fletGodkendelser(ind).find((m) => m.id === 'm1')!.content
    const kaldIndeks = content
      .map((b, i) => (b.type === 'tool_use' ? i : -1))
      .filter((i) => i >= 0)

    expect(content[kaldIndeks[0]! - 1]).toMatchObject({ approval_id: 'ap-1' })
    expect(content[kaldIndeks[1]! - 1]).toMatchObject({ approval_id: 'ap-2' })
  })

  it('uden et matchende kald lægges den sidst — men aldrig som svar', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('g1', 'ap-ukendt', 'noget-helt-andet'),
      tur([
        kald('call_1', 'rm -rf /tmp/x'),
        { type: 'text', text: 'Færdig.' },
      ]),
    ]

    const content = fletGodkendelser(ind).find((m) => m.id === 'm1')!.content
    const sidsteKald = content.map((b) => b.type).lastIndexOf('tool_use')
    const approvalIndeks = content.findIndex((b) => b.type === 'approval')

    // Den må ikke snige sig ind FORAN et kald den ikke hører til.
    expect(approvalIndeks).toBeGreaterThan(sidsteKald)
    expect(content.filter((b) => b.type === 'approval')).toHaveLength(1)
  })
})
