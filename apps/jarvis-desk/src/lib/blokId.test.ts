/**
 * BLOKKENS IDENTITET ER UFORANDERLIG — stemplet ved fødslen, aldrig udledt.
 *
 * Bjørn 26/11-2026 (GPT's første brud): «kildeNoegle() hasher det mutable
 * tekstindhold, samtidig med at model.segmenter bygges fra pacedBlocks.
 * Dermed ændres React-key under selve pacing.»
 *
 * Målingen af `tool_use:k1` beviste kun at ET KALD stod stille — den sagde
 * intet om den tekst der voksede. Testene her måler præcis det.
 */
import { describe, expect, it } from 'vitest'
import { initialStreamState, streamReducer, type StreamState } from './streamReducer'
import { deriveChatFlow } from './chatFlowModel'
import type { StreamEvent } from './sseProtocol'

const msgStart = (runId: string): StreamEvent => ({
  type: 'message_start',
  message: {
    id: runId, model: 'test', provider: 'p', lane: 'l', session_id: null,
    usage: { input_tokens: 1, output_tokens: 0 },
  },
} as StreamEvent)

const blokStart = (index: number, phase?: 'commentary' | 'final_answer'): StreamEvent => ({
  type: 'content_block_start', index,
  content_block: { type: 'text', text: '', ...(phase ? { phase } : {}) },
} as StreamEvent)

const delta = (index: number, text: string): StreamEvent => ({
  type: 'content_block_delta', index,
  delta: { type: 'text_delta', text },
} as StreamEvent)

/** Segment-id'erne som visningen faktisk bruger dem — React-keys. */
const segmentIds = (s: StreamState): string[] =>
  deriveChatFlow({
    blocks: s.blocks,
    finalAnswerStarted: s.finalAnswerStarted,
    status: s.status,
  }).segmenter.map((segment) => segment.id)

describe('blokidentiteten kommer fra fødslen, ikke fra indholdet', () => {
  it('KERNEN: nøglen står stille mens teksten vokser gennem hver delta', () => {
    let s = streamReducer(initialStreamState(), msgStart('r1'))
    s = streamReducer(s, blokStart(0, 'commentary'))

    const idVedFødsel = segmentIds(s)
    expect(idVedFødsel).toHaveLength(1)

    // Teksten vokser — det er præcis det pacing gør, frame for frame.
    for (const bid of ['Jeg ', 'læser ', 'koden ', 'først.']) {
      s = streamReducer(s, delta(0, bid))
      expect(segmentIds(s)).toEqual(idVedFødsel)
    }

    // Modprøve: teksten ER vokset. Ellers ville testen også bestå af at der
    // ikke skete noget, og så beviste den intet om identiteten.
    const tekst = s.blocks[0]
    expect(tekst && tekst.type === 'text' ? tekst.text : '').toBe('Jeg læser koden først.')
  })

  it('et replay af samme indeks i samme run beholder identiteten', () => {
    let s = streamReducer(initialStreamState(), msgStart('r1'))
    s = streamReducer(s, blokStart(0, 'commentary'))
    s = streamReducer(s, delta(0, 'halvt svar'))
    const foer = segmentIds(s)

    // Reconnect: serveren sender blokken forfra på samme indeks.
    s = streamReducer(s, blokStart(0, 'commentary'))
    s = streamReducer(s, delta(0, 'halvt svar'))

    expect(segmentIds(s)).toEqual(foer)
  })

  it('to blokke får to forskellige id’er — ellers ville React slå dem sammen', () => {
    let s = streamReducer(initialStreamState(), msgStart('r1'))
    s = streamReducer(s, blokStart(0, 'commentary'))
    s = streamReducer(s, delta(0, 'syntese'))
    s = streamReducer(s, blokStart(1, 'final_answer'))
    s = streamReducer(s, delta(1, 'svaret'))

    const ids = segmentIds(s)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('MODPRØVE: identiteten afhænger ikke af run-id — kun af fødslen', () => {
    // GPT's krav (26/11-2026): «Identiteten må aldrig afhænge af tekstindhold,
    // fase eller aktuel position.» Run-id'et hører til samme klasse: det kan
    // ankomme EFTER blokken og skifte under en replay. To ture med forskellige
    // run-ids giver derfor samme løbenummer — og det er pointen, ikke en fejl.
    // Unikheden der betyder noget er INDEN FOR turen (testen ovenover).
    let s = streamReducer(initialStreamState(), msgStart('r1'))
    s = streamReducer(s, blokStart(0, 'commentary'))
    const foersteTur = segmentIds(s)

    let n = streamReducer(initialStreamState(), msgStart('r2'))
    n = streamReducer(n, blokStart(0, 'commentary'))
    const andenTur = segmentIds(n)

    expect(andenTur).toHaveLength(1)
    expect(andenTur[0]).toBe(foersteTur[0])
  })

  it('blokken bærer sit id — det er ikke udledt i visningen', () => {
    let s = streamReducer(initialStreamState(), msgStart('r7'))
    s = streamReducer(s, blokStart(3, 'final_answer'))
    const blok = s.blocks[3]
    const id = blok && 'blokId' in blok ? blok.blokId : undefined
    // Et LØBENUMMER, ikke `${runId}:${indeks}`. Run-id'et kan ankomme efter
    // blokken, og indekset forskubbes af huller og skill-flader.
    expect(id).toMatch(/^b\d+$/)
  })
})

describe('identiteten overlever at listen forskubber sig', () => {
  it('KERNEN: et HUL der udfyldes foran forskubber forekomsten, ikke id’et', () => {
    // Et run midt i turen kan efterlade et hul. `liveChatBlokke` filtrerer
    // hullet væk, så alt bagefter rykker ÉT pladser ned i den projicerede
    // liste — og en nøgle bygget på forekomst ville skifte for hver af dem.
    // `blokId` er upåvirket: den er knyttet til blokken, ikke til rækken.
    let s = streamReducer(initialStreamState(), msgStart('r1'))
    s = streamReducer(s, blokStart(1, 'final_answer'))
    s = streamReducer(s, delta(1, 'svaret'))

    const foer = segmentIds(s)
    expect(foer).toHaveLength(1)

    // Nu udfyldes hullet på indeks 0 — et tidligere blokløb ankommer.
    s = streamReducer(s, blokStart(0, 'commentary'))
    s = streamReducer(s, delta(0, 'foerste blok'))

    const efter = segmentIds(s)
    // To segmenter, fordi rollerne er forskellige: runde, så besvarelse.
    expect(efter).toHaveLength(2)
    // Besvarelsen stod allerede på skærmen og beholder sit id.
    expect(efter[1]).toBe(foer[0])
  })
})
