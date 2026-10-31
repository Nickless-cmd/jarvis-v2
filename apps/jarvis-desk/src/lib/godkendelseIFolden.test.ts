import { describe, it, expect } from 'vitest'
import { fletGodkendelser, forsteGodkendelse } from './godkendelseIFolden'
import { deriveChatFlow } from './chatFlowModel'
import type { ChatMessage } from './api'

/**
 * Godkendelsen hører til TUREN — ikke til samtalen.
 *
 * MAALT 31/10-2026 (Bjørn, med skærmbillede af 0.6.295): de to
 * godkendelses-rækker stod som to selvstændige blokke midt i samtalen, uden
 * for enhver fold. Hans ord: «Burde disse 2 ikk have ligget inde i det foldet
 * hovede ved de runder de hørte til?»
 *
 * Der var TO fejl i én: to rækker for én godkendelse (append-only i basen er
 * rigtigt, men på skærmen er det to gange), og placeret som samtale i stedet
 * for som arbejde.
 */

function raekke(id: string, role: ChatMessage['role'], ekstra: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id,
    role,
    content: role === 'assistant' ? [{ type: 'text', text: 'Svar.' }] : [],
    created_at: '2026-10-31T15:57:36+00:00',
    ...ekstra,
  }
}

function godkendelse(id: string, approvalId: string, status: string, action = 'rm -rf /tmp/x'): ChatMessage {
  return raekke(id, 'approval_request', {
    content_json: [{ type: 'approval', approval_id: approvalId, tool: 'bash', action, status, risk: 'destructive' }],
  })
}

describe('godkendelsen flettes ind i turen', () => {
  it('to rækker for ÉN godkendelse bliver til ÉN blok', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'approved'),
      raekke('s1', 'assistant'),
    ]
    const ud = fletGodkendelser(ind)
    const blokke = ud.flatMap((m) => m.content.filter((b) => b.type === 'approval'))
    expect(blokke).toHaveLength(1)
    expect(ud.filter((m) => m.role === 'approval_request')).toHaveLength(0)
  })

  it('den SIDSTE status vinder — afgørelsen, ikke anmodningen', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'denied'),
      raekke('s1', 'assistant'),
    ]
    const ud = fletGodkendelser(ind)
    const blok = ud.flatMap((m) => m.content).find((b) => b.type === 'approval')
    expect(blok).toMatchObject({ status: 'denied' })
  })

  it('blokken lægges i den assistent-tur der FØLGER efter', () => {
    const ind = [
      raekke('u1', 'user'),
      raekke('s0', 'assistant'),
      raekke('u2', 'user'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'approved'),
      raekke('s1', 'assistant'),
    ]
    const ud = fletGodkendelser(ind)
    const medBlok = ud.filter((m) => m.content.some((b) => b.type === 'approval'))
    expect(medBlok).toHaveLength(1)
    expect(medBlok[0]?.id).toBe('s1')
  })

  it('en raekke hvis tur IKKE er skrevet endnu bliver staaende — den skal kunne besvares nu', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('a1', 'ap-1', 'pending'),
    ]
    const ud = fletGodkendelser(ind)
    expect(ud.filter((m) => m.role === 'approval_request')).toHaveLength(1)
  })

  it('to FORSKELLIGE godkendelser bliver ikke smeltet sammen', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('a1', 'ap-1', 'approved', 'rm -rf /tmp/x'),
      godkendelse('a2', 'ap-2', 'denied', 'rm -rf /tmp/y'),
      raekke('s1', 'assistant'),
    ]
    const blokke = fletGodkendelser(ind).flatMap((m) => m.content).filter((b) => b.type === 'approval')
    expect(blokke).toHaveLength(2)
  })

  it('raekker UDEN approval_id smelter ikke sammen ved et tilfaelde', () => {
    const ind = [
      raekke('u1', 'user'),
      raekke('a1', 'approval_request', { content_json: [{ tool: 'bash', status: 'pending' }] }),
      raekke('a2', 'approval_request', { content_json: [{ tool: 'bash', status: 'pending' }] }),
      raekke('s1', 'assistant'),
    ]
    const blokke = fletGodkendelser(ind).flatMap((m) => m.content).filter((b) => b.type === 'approval')
    expect(blokke).toHaveLength(2)
  })
})

describe('blokken havner i FOLDEN, ikke i svaret', () => {
  it('deriveChatFlow lægger godkendelsen i arbejdet', () => {
    const ind = [
      raekke('u1', 'user'),
      godkendelse('a1', 'ap-1', 'pending'),
      godkendelse('a2', 'ap-1', 'approved'),
      raekke('s1', 'assistant'),
    ]
    const tur = fletGodkendelser(ind).find((m) => m.id === 's1')!
    const model = deriveChatFlow({
      blocks: tur.content,
      finalAnswerStarted: true,
      status: 'done',
    })
    expect(model.workBlocks.some((b) => b.type === 'approval')).toBe(true)
    expect(model.finalBlocks.some((b) => b.type === 'approval')).toBe(false)
    // Folden skal findes — ellers er der intet hoved at ligge i.
    expect(model.hasObservableWork).toBe(true)
  })
})

describe('forsteGodkendelse taaler en daarlig raekke', () => {
  it('tom eller ukendt form kaster ikke', () => {
    expect(forsteGodkendelse(undefined).status).toBe('pending')
    expect(forsteGodkendelse('skrald').tool).toBe('godkendelse')
    expect(forsteGodkendelse([{}]).approval_id).toBe('')
  })
})
