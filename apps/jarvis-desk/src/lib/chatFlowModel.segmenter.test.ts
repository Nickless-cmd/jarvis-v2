/**
 * SEGMENTERNE — turens rækkefølge, ikke to bunker.
 *
 * Bjørn 26/11-2026: «En runde må ikke skifte forælder, når hovedet folder. En
 * besvarelse må ikke skifte semantisk rolle, når næste runde ankommer. Og
 * ingen af delene må forsvinde, før deres respektive livscyklus tillader det.»
 *
 * Tre invariants, én test hver:
 *
 *   1. IDENTITETEN ER STABIL     — en ny blok giver ikke eksisterende segmenter nye id'er
 *   2. PLACERINGEN ER STABIL     — en ny runde omklassificerer ikke et vist slutsvar
 *   3. LEVETIDEN ER UAFHÆNGIG    — intet segment forsvinder når et andet vokser
 *
 * Og den test de to bunker ikke kunne bestå: rækkefølgen
 * Besvarelse A → Runde 1 → Besvarelse B.
 */
import { describe, expect, it } from 'vitest'
import { deriveChatFlow, type ChatFlowInput } from './chatFlowModel'
import type { ContentBlock } from './sseProtocol'

const tekst = (text: string, phase?: 'commentary' | 'final_answer'): ContentBlock =>
  ({ type: 'text', text, ...(phase ? { phase } : {}) }) as ContentBlock

const kald = (id: string): ContentBlock =>
  ({ type: 'tool_use', id, name: 'bash', input: {} }) as ContentBlock

const fremdrift = (id: string): ContentBlock =>
  ({ type: 'progress', id, text: 'arbejder' }) as unknown as ContentBlock

const svar = (blocks: ContentBlock[], over: Partial<ChatFlowInput> = {}) =>
  deriveChatFlow({
    blocks,
    workingStep: null,
    rundeEtiketter: {},
    tankeResumeer: {},
    finalAnswerStarted: false,
    status: 'working',
    arbejdeEfterSvar: false,
    ...over,
  } as ChatFlowInput)

describe('segmenter bevarer turens rækkefølge', () => {
  it('KERNEN: Besvarelse A → Runde 1 → Besvarelse B kan udtrykkes', () => {
    // Det de to bunker ikke kunne: A og B lå i samme bunke, runden i den
    // anden, og visningen måtte gætte rækkefølgen.
    const model = svar([
      tekst('Første del af svaret.', 'final_answer'),
      kald('k1'),
      fremdrift('p1'),
      tekst('Anden del af svaret.', 'final_answer'),
    ])

    expect(model.segmenter.map((s) => s.slags)).toEqual([
      'besvarelse',
      'runde',
      'besvarelse',
    ])
    // Indholdet er i den rigtige rækkefølge, ikke blot i den rigtige bunke.
    expect(model.segmenter[0]!.blokke).toHaveLength(1)
    expect(model.segmenter[1]!.blokke).toHaveLength(2)
    expect(model.segmenter[2]!.blokke).toHaveLength(1)
  })

  it('de to bunker er AFledt — samme indhold som før', () => {
    // Syntesen bærer `commentary` — det er den form serveren sender den i.
    const blokke = [kald('k1'), tekst('syntese', 'commentary'), tekst('svaret', 'final_answer')]
    const model = svar(blokke, { finalAnswerStarted: true })
    // Kontrakten for de eksisterende læsere er uændret.
    expect(model.workBlocks.map((b) => b.type)).toEqual(['tool_use', 'text'])
    expect(model.finalBlocks.map((b) => b.type)).toEqual(['text'])
    // Og de er præcis segmenternes blokke, i samme orden.
    const fraSegmenter = model.segmenter.flatMap((s) => s.blokke)
    expect(fraSegmenter).toEqual([...model.workBlocks, ...model.finalBlocks])
  })
})

describe('INVARIANT 1 — identiteten er stabil', () => {
  it('en ny blok giver IKKE eksisterende segmenter nye id’er', () => {
    const foer = svar([kald('k1'), tekst('arbejde')])
    const foerIds = foer.segmenter.map((s) => s.id)

    // En ny blok ankommer bagefter — som i en levende strøm.
    const efter = svar([kald('k1'), tekst('arbejde'), kald('k2')])
    const efterIds = efter.segmenter.map((s) => s.id)

    // Hvert tidligere id findes stadig, uændret, på samme plads.
    foerIds.forEach((id, i) => expect(efterIds[i]).toBe(id))
  })

  it('MODPRØVE: to forskellige blokke får ikke samme id', () => {
    const model = svar([kald('k1'), kald('k2')])
    const ids = model.segmenter.map((s) => s.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})

describe('INVARIANT 2 — placeringen er stabil', () => {
  it('KERNEN: et slutsvar med phase bliver ALDRIG runde når en ny runde ankommer', () => {
    // Præcis den dynamiske omklassificering: før ville `lastWorkIndex` flytte
    // sig da k2 ankom, og teksten før den kunne skifte rolle.
    const foer = svar([tekst('Svaret.', 'final_answer')], { finalAnswerStarted: true })
    expect(foer.segmenter[0]!.slags).toBe('besvarelse')

    const efter = svar([tekst('Svaret.', 'final_answer'), kald('k2')], {
      finalAnswerStarted: true,
    })
    // Svaret er STADIG en besvarelse — det blev ikke arbejde af at en runde kom.
    expect(efter.segmenter[0]!.slags).toBe('besvarelse')
    expect(efter.segmenter[0]!.id).toBe(foer.segmenter[0]!.id)
  })

  it('commentary er runde uanset hvor den står', () => {
    const model = svar([kald('k1'), tekst('mellemregning', 'commentary')], {
      finalAnswerStarted: true,
    })
    expect(model.segmenter.map((s) => s.slags)).toEqual(['runde'])
  })

  it('DOCUMENTERET BEGRÆNSNING: en blok UDEN phase følger stadig placeringen', () => {
    // Det er den åbne grænse fra DEVLOG: umærkede persisterede blokke har
    // ingen autoritativ semantik, så `final_answer_start` flytter dem.
    const foer = svar([kald('k1'), tekst('umærket')], { finalAnswerStarted: false })
    expect(foer.segmenter.at(-1)!.slags).toBe('runde')

    const efter = svar([kald('k1'), tekst('umærket')], { finalAnswerStarted: true })
    expect(efter.segmenter.at(-1)!.slags).toBe('besvarelse')
  })
})

describe('INVARIANT 3 — levetiden er uafhængig', () => {
  it('intet segment forsvinder når et andet vokser', () => {
    const foer = svar([kald('k1'), tekst('syntese', 'commentary')])
    const foerAntal = foer.segmenter.length

    // Syntesen vokser (samme blok, mere tekst) og et svar begynder.
    const efter = svar([
      kald('k1'),
      tekst('syntese der er blevet længere', 'commentary'),
      tekst('svaret', 'final_answer'),
    ])

    expect(efter.segmenter.length).toBeGreaterThanOrEqual(foerAntal)
    foer.segmenter.forEach((s, i) => {
      expect(efter.segmenter[i]!.id).toBe(s.id)
      expect(efter.segmenter[i]!.slags).toBe(s.slags)
    })
  })

  it('et tomt input giver nul segmenter — ikke et tomt segment', () => {
    expect(svar([]).segmenter).toEqual([])
  })
})

/**
 * KILDEIDENTITETEN — ikke positionen i den liste vi fik.
 *
 * GPT 26/11-2026: `liveChatBlokke()` kan komprimere huller gennem
 * `udenHuller()` OG præpende `skillFlade` foran de eksisterende blokke. Så er
 * indeks i den projicerede liste ikke SSE-indekset, og et id bygget på indeks
 * ville skifte ved en reconnect der udfylder et hul — React ville rive
 * containeren ned midt i turen.
 *
 * Testene her sender listen GENNEM de to forskydninger og kræver at hvert
 * segments id står stille.
 */
describe('segmentidentiteten kommer fra kilden, ikke fra positionen', () => {
  it('skillFlade PRÆPENDET forskubber positionen men ikke id’erne', () => {
    const blokke = [
      kald('k1'),
      tekst('syntese', 'commentary'),
      tekst('svaret', 'final_answer'),
    ]
    const foer = svar(blokke, { finalAnswerStarted: true })
    // `liveChatBlokke` lægger skillFlade FORAN alt — indeks 0 bliver en
    // anden blok, og hvert efterfølgende indeks rykker én op.
    const skilleflade = { type: 'skill_surface', matches: [], primary: false } as unknown as ContentBlock
    const efter = svar([skilleflade, ...blokke], { finalAnswerStarted: true })

    // Det nye segment er skillefladen, som smelter sammen med det første
    // runde-segment. Vi fjerner skillefladen fra blokkene og kræver at
    // RESTEN har samme id som før — positionen er forskudt, kilden er ikke.
    const efterUdenSkilleflade = efter.segmenter
      .map((s) => ({ ...s, blokke: s.blokke.filter((b) => b !== skilleflade) }))
      .filter((s) => s.blokke.length > 0)
    expect(efterUdenSkilleflade.map((s) => s.id)).toEqual(foer.segmenter.map((s) => s.id))
  })

  it('et udfyldt HUL forskubber positionen men ikke id’erne', () => {
    const blokke = [
      kald('k1'),
      tekst('syntese', 'commentary'),
      tekst('svaret', 'final_answer'),
    ]
    const foer = svar(blokke, { finalAnswerStarted: true })
    // `udenHuller` fjerner `undefined` — her sætter vi et hul IND midt i
    // listen, præcis som et run midt i en tur kan efterlade det.
    const medHul = [blokke[0]!, undefined as unknown as ContentBlock, ...blokke.slice(1)]
    const efter = svar(medHul, { finalAnswerStarted: true })

    expect(efter.segmenter.map((s) => s.id)).toEqual(foer.segmenter.map((s) => s.id))
  })

  it('to identiske tekster i samme tur får FORSKELLIGE id’er', () => {
    // Forekomsttælleren er det der gør hash-nøglen brugbar: uden den ville
    // to ens synteser kollidere og React ville genbruge den forkerte node.
    const model = svar([
      tekst(' samme ', 'commentary'),
      kald('k1'),
      tekst(' samme ', 'commentary'),
    ])
    const idListe = model.segmenter.map((s) => s.id)
    expect(new Set(idListe).size).toBe(idListe.length)
  })

  it('PLACERINGEN er en separat egenskab fra rollen', () => {
    // En runde EFTER slutsvaret er stadig arbejde (`slags: 'runde'`), men dens
    // container skal leve til turen slutter — det bæres af `plassering`.
    const model = svar([
      tekst('svaret', 'final_answer'),
      kald('k-efter'),
    ], { finalAnswerStarted: true })

    const runde = model.segmenter.find((s) => s.slags === 'runde')
    expect(runde).toBeDefined()
    expect(runde!.plassering).toBe('efter')

    const besvarelse = model.segmenter.find((s) => s.slags === 'besvarelse')
    expect(besvarelse!.plassering).toBe('foerste')
  })
})
