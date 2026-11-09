import { describe, it, expect } from 'vitest'
import { fletGodkendelser } from './godkendelseIFolden'
import type { ChatMessage } from './api'

/**
 * Én godkendelse må kun give ÉT kort.
 *
 * MÅLT 9/11-2026 (Bjørn: «Dem over composer bliver vist dobbelt»): serveren
 * skriver to rækker pr. godkendelse — `pending` og `approved`/`denied` — og
 * midt i en igangværende tur ligger de omgivet af `tool`-rækker uden en
 * assistant-række imellem. `fletGodkendelser` fjernede dengang kun rækkerne
 * når den fandt en efterfølgende assistant-tur, så begge rækker blev stående
 * og tegnet som to kort.
 *
 * Målt mod `chat_messages`: alle 17 godkendelser i den aktive session har
 * præcis 2 rækker, alle midt i en tur.
 */

function raekke(id: string, role: string, tekst = ''): ChatMessage {
  return {
    id,
    role,
    content: tekst ? [{ type: 'text', text: tekst }] : [],
    created_at: '2026-11-09T00:00:00Z',
  } as unknown as ChatMessage
}

function godkendelse(id: string, approvalId: string, status: string): ChatMessage {
  return {
    id,
    role: 'approval_request',
    content: `Godkendelse: bash — ${status}`,
    created_at: '2026-11-09T00:00:00Z',
    content_json: [
      {
        type: 'approval',
        approval_id: approvalId,
        tool: 'bash',
        action: 'rm -rf /tmp/x',
        status,
        risk: 'destructive',
      },
    ],
  } as unknown as ChatMessage
}

describe('dublet ved to rækker i en igangværende tur', () => {
  it('to rækker for samme approval_id midt i en tur giver ÉT kort', () => {
    const ind = [
      raekke('u1', 'user', 'kør det'),
      raekke('t1', 'tool', '[tool_result:abc]'),
      godkendelse('a1', 'ap-1', 'pending'),
      raekke('t2', 'tool', '[tool_result:def]'),
      godkendelse('a2', 'ap-1', 'approved'),
      raekke('t3', 'tool', '[tool_result:ghi]'),
    ]

    const ud = fletGodkendelser(ind)
    const tilbage = ud.filter((m) => (m as { role: string }).role === 'approval_request')

    expect(tilbage.length).toBe(1)
    expect(tilbage[0]?.id).toBe('a2')
  })

  it('to forskellige godkendelser giver to kort', () => {
    const ind = [
      raekke('u1', 'user', 'kør det'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'approved'),
      godkendelse('b1', 'ap-2', 'pending'),
      godkendelse('b2', 'ap-2', 'denied'),
    ]

    const ud = fletGodkendelser(ind)
    const tilbage = ud.filter((m) => (m as { role: string }).role === 'approval_request')

    expect(tilbage.length).toBe(2)
    expect(tilbage.map((m) => m.id).sort()).toEqual(['a2', 'b2'])
  })

  it('en afsluttet tur fjerner rækkerne helt og lægger blokken i turen', () => {
    const ind = [
      raekke('u1', 'user', 'kør det'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'approved'),
      raekke('s1', 'assistant', 'færdig'),
    ]

    const ud = fletGodkendelser(ind)
    const tilbage = ud.filter((m) => (m as { role: string }).role === 'approval_request')
    expect(tilbage.length).toBe(0)

    const blok = ud
      .flatMap((m) => (Array.isArray(m.content) ? m.content : []))
      .find((b) => (b as { type?: string }).type === 'approval')
    expect(blok).toMatchObject({ approval_id: 'ap-1', status: 'approved' })
  })
})
