/**
 * Hovedets fire tilstande — og vagten mod at de divergerer fra ordet.
 *
 * ## Hvorfor denne test findes (18/11-2026)
 *
 * Fejlen den værner mod blev målt, ikke gættet: `hovedTekst` blev udledt af
 * `status === 'working' && !finalAnswerStarted`, mens visningens gate brugte
 * `streaming || arbejdeEfterSvar`. To svar på samme spørgsmål — så hovedet
 * kunne sige «Tænkte» mens turen kørte, og gaten kunne afmontere elementet i
 * det samme frame som ordet skiftede. Det blev læst som et blink.
 *
 * Rettelsen er ikke en ny animation: det er at tilstanden blev eksplicit, og
 * at BÅDE ordet og gaten læser den. Testen her måler netop den kobling — en
 * test der kun gentog `hovedTekst`-implementeringen ville være grøn uanset.
 */
import { describe, it, expect } from 'vitest'
import { deriveChatFlow } from './chatFlowModel'
import type { ChatFlowInput } from './chatFlowModel'
import type { StreamStatus } from './streamReducer'

const arbejde = {
  type: 'tool_use' as const,
  id: 't1',
  name: 'read_file',
  input: {},
  status: 'done' as const,
}

const svar = { type: 'text' as const, text: 'Færdig.' }

function model(over: Partial<ChatFlowInput>) {
  return deriveChatFlow({
    blocks: [],
    finalAnswerStarted: false,
    status: 'working' as StreamStatus,
    ...over,
  })
}

describe('hovedTilstand — de fire, og kun de fire', () => {
  it('aktiv: turen kører og slutsvaret er ikke begyndt', () => {
    const m = model({ status: 'working', blocks: [arbejde] })
    expect(m.hovedTilstand).toBe('aktiv')
    expect(m.hovedTekst).toBe('Arbejder')
  })

  it('aktiv uden værktøjskald siger «Tænker», ikke «Arbejder»', () => {
    const m = model({ status: 'working', blocks: [] })
    expect(m.hovedTilstand).toBe('aktiv')
    expect(m.hovedTekst).toBe('Tænker')
  })

  it('formidlet: svaret er begyndt — arbejdet er overstået, turen kører endnu', () => {
    const m = model({
      status: 'working',
      blocks: [arbejde, svar],
      finalAnswerStarted: true,
    })
    expect(m.hovedTilstand).toBe('formidlet')
    expect(m.hovedTekst).toBe('Arbejdet')
  })

  it('formidlet: turen er færdig', () => {
    const m = model({ status: 'done', blocks: [arbejde, svar] })
    expect(m.hovedTilstand).toBe('formidlet')
    expect(m.hovedTekst).toBe('Arbejdet')
  })

  it('afbrudt: brugeren stoppede turen', () => {
    const m = model({ status: 'interrupted', blocks: [arbejde] })
    expect(m.hovedTilstand).toBe('afbrudt')
    expect(m.hovedTekst).toBe('Arbejdet afbrudt')
  })

  it('fejlet: turen faldt', () => {
    const m = model({ status: 'error', blocks: [arbejde] })
    expect(m.hovedTilstand).toBe('fejlet')
    expect(m.hovedTekst).toBe('Arbejdet fejlede')
  })

  it('alle fire tilstande kan nås — ingen af dem er død kode', () => {
    const nået = new Set(
      [
        model({ status: 'working', blocks: [arbejde] }),
        model({ status: 'done', blocks: [arbejde, svar] }),
        model({ status: 'interrupted', blocks: [arbejde] }),
        model({ status: 'error', blocks: [arbejde] }),
      ].map((m) => m.hovedTilstand),
    )
    expect(nået).toEqual(new Set(['aktiv', 'formidlet', 'afbrudt', 'fejlet']))
  })
})

describe('vagten: ordet kan ikke sige noget tilstanden ikke er', () => {
  // Nutid er forbeholdt `aktiv`. Siger ordet «Arbejder»/«Tænker» mens
  // tilstanden er en anden, er de to udledninger igen løbet fra hinanden.
  const NUTID = ['Arbejder', 'Tænker']

  it('nutid optræder KUN i aktiv — målt over alle fire udfald', () => {
    const kombinationer = [
      model({ status: 'working', blocks: [arbejde] }),
      model({ status: 'working', blocks: [] }),
      model({ status: 'working', blocks: [arbejde, svar], finalAnswerStarted: true }),
      model({ status: 'done', blocks: [arbejde, svar] }),
      model({ status: 'interrupted', blocks: [arbejde] }),
      model({ status: 'error', blocks: [arbejde] }),
      model({ status: 'working', blocks: [arbejde], arbejdeEfterSvar: true, finalAnswerStarted: true }),
    ]
    const brud = kombinationer.filter(
      (m) => NUTID.includes(m.hovedTekst) !== (m.hovedTilstand === 'aktiv'),
    )
    expect(brud.map((m) => `${m.hovedTilstand}/${m.hovedTekst}`)).toEqual([])
  })

  it('arbejdeEfterSvar slår finalAnswerStarted — ellers stod hovedet i datid mens der arbejdes', () => {
    // Præcis den divergens der blev målt: svaret er låst, men et nyt run
    // arbejder. Uden denne gren ville tilstanden være `formidlet` og ordet
    // «Arbejdet», mens værktøjer faktisk kørte.
    const m = model({
      status: 'done',
      blocks: [arbejde, svar],
      finalAnswerStarted: true,
      arbejdeEfterSvar: true,
    })
    expect(m.hovedTilstand).toBe('aktiv')
    expect(m.hovedTekst).toBe('Arbejder')
  })

  it('et terminalt udfald vinder over «kører» — en fejlet tur er ikke aktiv', () => {
    const m = model({ status: 'error', blocks: [arbejde] })
    expect(m.hovedTilstand).not.toBe('aktiv')
  })
})
