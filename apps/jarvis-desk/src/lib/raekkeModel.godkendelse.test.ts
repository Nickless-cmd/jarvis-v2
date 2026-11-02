import { describe, it, expect } from 'vitest'
import { opdel, opdelArbejdsrunder } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

/**
 * GODKENDELSEN ER ARBEJDE — også i code mode (2/11-2026).
 *
 * `opdel` finder det SIDSTE værktøjskald og kalder alt derefter for svar.
 * `erArbejdsBlok` kendte ikke `approval`, så en godkendelse der lå efter
 * sidste kald faldt i `svar` og blev tegnet som en del af REPLIKKEN — nederst
 * i beskeden, under slutteksten.
 *
 * MÅLT 2/11-2026 på Bjørns skærmbillede af code mode: de to kort stod under
 * «Tilbage 144 MB…», altså i svaret. `chatFlowModel` (chat mode) havde reglen;
 * `raekkeModel` (code mode) havde den ikke. Fixet i `fletGodkendelser` blev
 * derfor kun synligt i chat mode.
 */

const kald = (id: string, kommando: string): ContentBlock => ({
  type: 'tool_use', id, name: 'bash', input: { command: kommando },
})

const godkendelse = (id: string): ContentBlock => ({
  type: 'approval',
  approval_id: id,
  tool: 'bash',
  action: 'rm -rf /tmp/x',
  status: 'approved',
})

describe('opdel: godkendelsen hører i arbejdet', () => {
  it('en godkendelse EFTER sidste kald er arbejde, ikke svar', () => {
    const blokke: ContentBlock[] = [
      { type: 'text', text: 'Jeg rydder op.' },
      kald('call_1', 'rm -rf /tmp/x'),
      { type: 'text', text: 'Ryddet op.' },
      godkendelse('ap-1'),
    ]

    const { arbejde, svar } = opdel(blokke)

    expect(svar.some((b) => b.type === 'approval')).toBe(false)
    expect(arbejde.some((e) => e.slags === 'blok' && e.blok.type === 'approval')).toBe(true)
  })

  it('en godkendelse der står ved sit kald bliver i samme runde', () => {
    const blokke: ContentBlock[] = [
      kald('call_1', 'rm -rf /tmp/a'),
      godkendelse('ap-1'),
      kald('call_2', 'rm -rf /tmp/b'),
      { type: 'text', text: 'Færdig.' },
    ]

    const { arbejde } = opdel(blokke)
    const sektioner = opdelArbejdsrunder(arbejde)
    const runder = sektioner.filter((s) => s.slags === 'runde')

    // Begge kald ligger i samme runde, fordi intet mellemsvar skiller dem.
    expect(runder).toHaveLength(1)
    const elementer = runder[0]!.slags === 'runde' ? runder[0]!.elementer : []
    const approvalIndeks = elementer.findIndex((e) => e.slags === 'blok' && e.blok.type === 'approval')
    const andetKald = elementer.findIndex(
      (e) => e.slags === 'blok' && e.blok.type === 'tool_use' && e.blok.id === 'call_2',
    )

    // Den skal stå MELLEM de to kald — ikke samlet til sidst i runden.
    expect(approvalIndeks).toBeGreaterThan(0)
    expect(approvalIndeks).toBeLessThan(andetKald)
  })
})
