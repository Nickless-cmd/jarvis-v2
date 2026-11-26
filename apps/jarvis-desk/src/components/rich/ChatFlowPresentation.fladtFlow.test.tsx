/**
 * DET FLADE DOKUMENTFLOW — rækkefølgen som DOM, ikke som tre faste containere.
 *
 * Bjørn 26/11-2026: «en runde uden for hovedet er stadig arbejde, men dens
 * container skal forblive synlig indtil turafslutningen».
 *
 * GPT's tredje krav var at verificere segmentidentiteten FØR den bruges som
 * React-key: `liveChatBlokke()` kan komprimere huller gennem `udenHuller()` og
 * præpende `skillFlade` foran de eksisterende blokke, så indeks i den
 * projicerede liste ikke er SSE-indekset. Testene her sender blokkene gennem
 * begge forskydninger og kræver at containerens `data-segment-id` står stille.
 */
import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

const tekst = (text: string, phase?: 'commentary' | 'final_answer'): ContentBlock =>
  ({ type: 'text', text, ...(phase ? { phase } : {}) }) as ContentBlock

const kald = (id: string): ContentBlock =>
  ({ type: 'tool_use', id, name: 'bash', input: {}, status: 'done' }) as ContentBlock

const common = {
  mode: 'living' as const,
  density: 'compact' as const,
  workingStep: null,
  rundeEtiketter: {},
  tankeResumeer: {},
  tokens: 0,
  config: {} as never,
}

const segmentIds = (container: HTMLElement): string[] =>
  Array.from(container.querySelectorAll('[data-segment-id]'))
    .map((el) => el.getAttribute('data-segment-id') ?? '')

describe('fladt dokumentflow', () => {
  it('KERNEN: en runde EFTER slutsvaret får sin egen container', () => {
    // Den gamle struktur kunne ikke udtrykke dette: besvarelsen og runden lå
    // i hver sin faste container, og rækkefølgen blev rekonstrueret.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[
          tekst('Første del af svaret.', 'final_answer'),
          kald('k-efter'),
          tekst('Anden del af svaret.', 'final_answer'),
        ]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )

    const flow = container.querySelector('[data-segmenter="flat"]')
    expect(flow).not.toBeNull()

    // Rækkefølgen i DOM følger turens rækkefølge — ikke rollen.
    const roller = Array.from(flow!.querySelectorAll('[data-segment]'))
      .map((el) => el.getAttribute('data-segment'))
    expect(roller).toEqual(['besvarelse', 'runde', 'besvarelse'])
  })

  it('runden efter slutsvaret er stadig ARBEJDE — men dens plassering er «efter»', () => {
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('Svaret.', 'final_answer'), kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )

    const runde = container.querySelector('[data-segment="runde"]')
    expect(runde).not.toBeNull()
    // Rollen og placeringen er TO egenskaber: den er arbejde, og den ligger
    // i halen. Levetiden læses af `plassering`, ikke af rollen.
    expect(runde!.getAttribute('data-plassering')).toBe('efter')
  })

  it('containerens id kommer fra kilden — en reconnect der udfylder et hul rører den ikke', () => {
    const blokke = [
      tekst('Svaret.', 'final_answer'),
      kald('k-efter'),
    ]
    const foer = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming status="working" finalAnswerStarted />,
    )
    const idsFoer = segmentIds(foer.container)
    foer.unmount()

    // Et run midt i turen kan efterlade et `undefined`-hul; `udenHuller()`
    // filtrerer det væk, og hvert efterfølgende indeks rykker ned.
    const medHul = [blokke[0]!, undefined as unknown as ContentBlock, blokke[1]!]
    const efter = render(
      <ChatFlowPresentation {...common} blocks={medHul}
        streaming status="working" finalAnswerStarted />,
    )

    expect(segmentIds(efter.container)).toEqual(idsFoer)
  })

  it('en præpendet skillFlade forskubber positionen men ikke de øvrige id’er', () => {
    const blokke = [tekst('Svaret.', 'final_answer'), kald('k-efter')]
    const foer = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming status="working" finalAnswerStarted />,
    )
    const idsFoer = segmentIds(foer.container)
    foer.unmount()

    const skilleflade = { type: 'skill_surface', matches: [], primary: false } as unknown as ContentBlock
    const efter = render(
      <ChatFlowPresentation {...common} blocks={[skilleflade, ...blokke]}
        streaming status="working" finalAnswerStarted />,
    )
    const idsEfter = segmentIds(efter.container)

    // Skillefladen tilføjer sit eget id; resten skal stå stille.
    expect(idsEfter.filter((id) => !id.startsWith('skill_surface:'))).toEqual(idsFoer)
  })

  it('en tur uden runde efter svaret beholder den GAMLE struktur', () => {
    // Den flade gren må ikke tage over for de ture hvor rækkefølgen er
    // identisk med den gamle — dér bærer den gamle vej fold, pacing og de
    // målte gates.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[kald('k1'), tekst('Svaret.', 'final_answer')]}
        streaming={false}
        status="done"
        finalAnswerStarted
      />,
    )

    expect(container.querySelector('[data-segmenter="flat"]')).toBeNull()
    expect(container.querySelector('.chat-flow-answer')).not.toBeNull()
  })

  it('en godkendelse i HALEN udløser ikke den flade gren — den hører til et kald', () => {
    // MÅLT 26/11-2026: `indsaetVedKald` lægger en godkendelse SIDST når dens
    // `action` ikke matcher noget kalds `input`. Blokken havnede dermed efter
    // slutsvaret og blev læst som en ny runde — men den er arbejde der hører
    // til et kald, præcis som `progress`. Uden denne udelukkelse tog hver
    // persisteret tur med en umatchet godkendelse den flade gren og rev de
    // målte gates ned.
    const godkendelse = {
      type: 'approval', approval_id: 'a1', tool: 'bash',
      action: 'rm -f /tmp/x', status: 'approved', risk: 'destructive',
    } as unknown as ContentBlock

    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[kald('k1'), tekst('Svaret.', 'final_answer'), godkendelse]}
        streaming={false}
        status="done"
        finalAnswerStarted
      />,
    )

    expect(container.querySelector('[data-segmenter="flat"]')).toBeNull()
    expect(container.querySelector('.chat-flow-answer')).not.toBeNull()
  })

  it('MODPRØVE: et RIGTIGT kald i halen udløser stadig den flade gren', () => {
    // Gaten må ikke være blevet blind af udelukkelsen ovenfor. Et værktøjskald
    // efter slutsvaret ER en ny runde, og så skal rækkefølgen bæres af data.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('Svaret.', 'final_answer'), kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )

    expect(container.querySelector('[data-segmenter="flat"]')).not.toBeNull()
  })
})

describe('levetiden — en runde bliver stående til turen slutter', () => {
  const blokke = [
    tekst('Svaret.', 'final_answer'),
    kald('k-efter'),
  ]

  it('en runde EFTER slutsvaret er LIVE mens turen kører', () => {
    // GPT's tredje krav: «en runde uden for hovedet er stadig arbejde, men dens
    // container skal forblive synlig indtil turafslutningen». Levetiden er
    // data (`data-levetid`), ikke en CSS-tilstand der gættes ud fra status.
    const { container } = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming status="working" finalAnswerStarted />,
    )
    const runde = container.querySelector('[data-segment="runde"]')
    expect(runde).not.toBeNull()
    expect(runde!.getAttribute('data-levetid')).toBe('live')
  })

  it('den kollapser FØRST når turen er terminal', () => {
    const { container } = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming={false} status="done" finalAnswerStarted />,
    )
    const runde = container.querySelector('[data-segment="runde"]')
    expect(runde).not.toBeNull()
    expect(runde!.getAttribute('data-levetid')).toBe('kollapset')
  })

  it('besvarelsen har ingen kollaps-fase — den er leverancen', () => {
    const { container } = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming={false} status="done" finalAnswerStarted />,
    )
    const svar = container.querySelector('[data-segment="besvarelse"]')
    expect(svar!.getAttribute('data-levetid')).toBe('svar')
  })
})
