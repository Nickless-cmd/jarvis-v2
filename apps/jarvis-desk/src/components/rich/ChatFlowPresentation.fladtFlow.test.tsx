/**
 * DEN STABILE DOKUMENTSTRUKTUR — besvarelsen er ét dokument, hale-runderne
 * er deres egne containere under den.
 *
 * Bjørn 27/11-2026: «Stop med at kompensere for strukturskiftet gennem
 * animationer. Turhovedet, besvarelsen og runderne uden for hovedet skal have
 * hver deres uafhængige visuelle livscyklus i én stabil dokumentstruktur.»
 *
 * ## Hvad der blev afløst
 *
 * Filen hed før `ChatFlowPresentation.fladtFlow.test.tsx` og beviste den
 * FLADE gren: at `[data-segmenter="flat"]` overtog når et runde-segment lå
 * efter besvarelsen, og at rækkefølgen «besvarelse → runde → besvarelse» blev
 * tegnet som tre containere.
 *
 * Den gren var selve fejlen. Den skiftede besvarelsens INDRE struktur (fra
 * `BlocksRenderer`s rod til `.chat-flow-segmenter`), og dermed remountede hele
 * besvarelsen i det øjeblik runden ankom. Animationerne dækkede over det.
 *
 * Nu er der ingen gren: `.chat-flow-answer` er ALTID `BlocksRenderer`, og
 * hale-runderne er ALTID deres egne containere i `[data-runder-efter]`.
 * `plassering` — ikke en boolean — bærer hvor længe hver container lever.
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

describe('stabil dokumentstruktur', () => {
  it('KERNEN: en runde EFTER slutsvaret får sin EGEN container under besvarelsen', () => {
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

    // Besvarelsen er ét dokument — uanset hvor mange runder der ligger efter.
    // Indholdet tjekkes IKKE her: uden frames står paceren på nul tegn i
    // jsdom, så teksten er tom af en pacing-grund og ikke af en strukturgrund.
    // Det er `accept.test.tsx` der måler teksten, hvor uret styres manuelt.
    const svar = container.querySelector('.chat-flow-answer')
    expect(svar).not.toBeNull()

    // Runden har sin egen container UNDER den — ikke inde i den.
    const hale = container.querySelector('[data-runder-efter]')
    expect(hale).not.toBeNull()
    expect(svar!.contains(hale)).toBe(false)

    const runde = hale!.querySelector('[data-segment="runde"]')
    expect(runde).not.toBeNull()
    expect(runde!.getAttribute('data-plassering')).toBe('efter')
  })

  it('besvarelsen skifter ALDRIG indre struktur — der findes ingen flad gren', () => {
    // Den gamle gren efterlod `[data-segmenter="flat"]` som besvarelsens
    // forælder. Den findes ikke længere: besvarelsen har præcis én ejer.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('Svaret.', 'final_answer'), kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    expect(container.querySelector('[data-segmenter="flat"]')).toBeNull()
    expect(container.querySelector('.chat-flow-answer')).not.toBeNull()
  })

  it('en tur UDEN hale-runde har ingen hale-container', () => {
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[kald('k1'), tekst('Svaret.', 'final_answer')]}
        streaming={false}
        status="done"
        finalAnswerStarted
      />,
    )
    expect(container.querySelector('[data-runder-efter]')).toBeNull()
    expect(container.querySelector('.chat-flow-answer')).not.toBeNull()
  })

  it('en godkendelse i HALEN er ikke en runde — den hører til et kald', () => {
    // MÅLT 26/11-2026: `indsaetVedKald` lægger en godkendelse SIDST når dens
    // `action` ikke matcher noget kalds `input`. Blokken havnede dermed efter
    // slutsvaret og blev læst som en ny runde. `HALEBLOKKE_UDEN_RUNDE` holder
    // den ude af hale-containeren, så en persisteret tur med en umatchet
    // godkendelse ikke får en container der ligner arbejde.
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

    expect(container.querySelector('[data-runder-efter]')).toBeNull()
    expect(container.querySelector('.chat-flow-answer')).not.toBeNull()
  })

  it('MODPRØVE: et RIGTIGT kald i halen får sin container', () => {
    // Gaten må ikke være blevet blind af udelukkelsen ovenfor. Et værktøjskald
    // efter slutsvaret ER en ny runde.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[tekst('Svaret.', 'final_answer'), kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
      />,
    )
    expect(container.querySelector('[data-runder-efter]')).not.toBeNull()
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
})

describe('levetiden — en hale-runde bliver stående til turen slutter', () => {
  const blokke = [
    tekst('Svaret.', 'final_answer'),
    kald('k-efter'),
  ]

  it('en runde EFTER slutsvaret er LIVE mens turen kører', () => {
    // GPT's tredje krav: «en runde uden for hovedet er stadig arbejde, men dens
    // container skal forblive synlig indtil turafslutningen». Levetiden er
    // data (`data-levetid`), ikke en CSS-tilstand gættet ud fra status.
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

  it('FOLDEN: hovedet åbner sig IKKE når den ekstra runde ankommer', () => {
    // Bjørn 27/11-2026: «du skal folde hoved før du køre den extra runde».
    //
    // MÅLT FØR RETTELSEN: `aaben` fulgte `arbejdeKoerer`, og den er også sand
    // i follow-up-vinduet. Så i det øjeblik runden ankom, blev `aaben` sand og
    // hovedet foldede UD igen — og foldede først sammen da HELE turen
    // sluttede. Brugeren måtte folde hovedet manuelt sammen for at se den
    // ekstra runde og slutbeskeden.
    //
    // Kontrakten: folden hører til den FØRSTE del af turen. Arbejde der
    // ankommer EFTER svaret genåbner ikke hovedet — det har sin egen container.
    const efter = render(
      <ChatFlowPresentation
        {...common}
        blocks={[kald('k1'), tekst('Svaret.', 'final_answer'), kald('k-efter')]}
        streaming
        status="working"
        finalAnswerStarted
        arbejdeEfterSvar
      />,
    )
    const gruppe = efter.container.querySelector('.chat-flow-gruppe-ydre')
    expect(gruppe).not.toBeNull()
    expect(gruppe!.getAttribute('data-aaben')).toBe('false')
    // Og runden ER synlig — den ligger bare i sin egen container.
    expect(efter.container.querySelector('[data-runder-efter]')).not.toBeNull()
  })

  it('MODPRØVE: under selve arbejdet ER hovedet åbent', () => {
    // Gaten må ikke være blevet blind: uden `arbejdeEfterSvar` er turen i sin
    // arbejdsfase, og så skal folden følge den.
    const { container } = render(
      <ChatFlowPresentation
        {...common}
        blocks={[kald('k1'), tekst('Arbejder…', 'commentary')]}
        streaming
        status="working"
        finalAnswerStarted={false}
      />,
    )
    const gruppe = container.querySelector('.chat-flow-gruppe-ydre')
    expect(gruppe).not.toBeNull()
    expect(gruppe!.getAttribute('data-aaben')).toBe('true')
  })

  it('besvarelsen har ingen kollaps-fase — den er leverancen', () => {
    const { container } = render(
      <ChatFlowPresentation {...common} blocks={blokke}
        streaming={false} status="done" finalAnswerStarted />,
    )
    // Besvarelsen er nu en almindelig `.chat-flow-answer` uden `data-levetid`:
    // den kollapser aldrig, fordi den ikke er arbejde. Det ER kontrakten —
    // før blev den båret af et `data-levetid="svar"` på et segment.
    const svar = container.querySelector('.chat-flow-answer')
    expect(svar).not.toBeNull()
    expect(svar!.getAttribute('data-levetid')).toBeNull()
  })
})
