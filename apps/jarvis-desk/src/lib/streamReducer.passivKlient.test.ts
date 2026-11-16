/**
 * MÅLING — problem 3: to klienter på samme session.
 *
 * Bjørn 16/11-2026: «Hvis jeg har feks. Code mode åben både i browseren og i
 * desk. Og trykker send i den ene så startes streamen pænt men i den anden
 * klient starter streamen op i forrige tur indtil turen er forbi.»
 *
 * Den PASSIVE klient (den der ikke selv sendte) ser den anden klients tur
 * komme ind over SSE. Den har ingen `client_turn_start` — den frame sendes kun
 * af den klient der selv trykkede send. Spørgsmålet er derfor:
 *
 *   Rydder et nyt runs `message_start` den forrige turs blokke i den passive
 *   klient, eller bliver de stående?
 *
 * Denne fil måler turgrænsen fra serverens `origin`-faktum.
 */
import { describe, expect, it } from 'vitest'
import { initialStreamState, streamReducer, type StreamState } from './streamReducer'

/** En klient der lige har LÆST et færdigt svar — låst, men ikke selv afsender. */
function passivKlientEfterLaestSvar(): StreamState {
  return {
    ...initialStreamState(),
    status: 'done',
    activeRunId: 'run-forrige',
    finalAnswerStarted: true,
    svarLaast: true,
    blocks: [{ type: 'text', text: 'Forrige turs svar.', phase: 'final_answer' }],
  }
}

describe('streamReducer — passiv klient ser en anden klients tur', () => {
  it('rydder den passive klient forrige turs blokke ved fremmed message_start', () => {
    const foer = passivKlientEfterLaestSvar()

    // Den anden klient trykker send. Serveren emitterer message_start for det
    // nye run. Den passive klient har ALDRIG set dette run-id som selvstændigt.
    const efter = streamReducer(foer, {
      type: 'message_start',
      message: {
        id: 'run-ny', model: 'm', provider: 'p', lane: 'l', origin: 'wakeup',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    } as never)

    // Målingen: er den forrige turs blokke væk?
    const forrigeSvarStaarTilbage = efter.blocks.some(
      (b) => b?.type === 'text' && b.text === 'Forrige turs svar.',
    )

    expect({
      forrigeSvarStaarTilbage,
      svarLaast: efter.svarLaast,
      aktivtRun: efter.activeRunId,
      antalBlokke: efter.blocks.length,
    }).toEqual({
      forrigeSvarStaarTilbage: false,
      svarLaast: false,
      aktivtRun: 'run-ny',
      antalBlokke: 0,
    })
  })

  it('lægger kun den fremmede turs tekst i den friske blok', () => {
    const foer = passivKlientEfterLaestSvar()
    const startet = streamReducer(foer, {
      type: 'message_start',
      message: {
        id: 'run-ny', model: 'm', provider: 'p', lane: 'l', origin: 'wakeup',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    } as never)

    // Turgrænsen skal være synlig allerede før den nye blok åbnes.
    expect(startet.blocks).toEqual([])

    const medBlok = streamReducer(startet, {
      type: 'content_block_start',
      index: 0,
      content_block: { type: 'text', text: '', phase: 'final_answer' },
    } as never)

    const medTekst = streamReducer(medBlok, {
      type: 'content_block_delta',
      index: 0,
      delta: { type: 'text_delta', text: 'Ny turs svar.' },
    } as never)

    // Ligger den nye tekst i den GAMLE blok, eller i en frisk?
    const tekst = medTekst.blocks
      .filter((b) => b?.type === 'text')
      .map((b) => (b as { text: string }).text)

    expect({ tekst, antalBlokke: medTekst.blocks.length }).toEqual({
      tekst: ['Ny turs svar.'],
      antalBlokke: 1,
    })
  })

  it('KONTROL: en klient der SELV sender rydder korrekt via client_turn_start', () => {
    const foer = passivKlientEfterLaestSvar()
    const efter = streamReducer(foer, {
      type: 'system_event', kind: 'client_turn_start', payload: {},
    } as never)

    expect(efter.blocks).toHaveLength(0)
    expect(efter.svarLaast).toBe(false)
    expect(efter.status).toBe('working')
  })
})
