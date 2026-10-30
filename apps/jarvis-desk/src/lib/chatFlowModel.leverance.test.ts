/**
 * Leverance-reglen skal være DEN SAMME i klienten som på serveren.
 *
 * Bjørn 29/10-2026: «når du tegner et widget, vises det over din slut besked
 * mens der paces og derefter hopper det til under din besked».
 *
 * Serveren lægger en leverance (`file`) efter den sidste blok der ikke er
 * værktøjsstøj — `_leverance_i_bunden` i `core/services/visible_runs_outcomes.py`.
 * Klientens levende tur havde ingen sådan regel, så widgetten blev tegnet på
 * sit oprindelige indeks. `vis_widget` kaldes typisk i en runde FØR teksten
 * skrives, så den stod ØVERST — og hoppede ned da den persisterede besked
 * (med serverens rækkefølge) afløste den levende.
 *
 * Hoppet forsvinder kun hvis de to visninger er ens. Derfor måler disse tests
 * rækkefølgen, ikke bare at blokken findes.
 */
import { describe, expect, it } from 'vitest'
import { deriveChatFlow, type ChatFlowInput } from './chatFlowModel'
import type { ContentBlock } from './sseProtocol'

const base: ChatFlowInput = {
  blocks: [],
  workingStep: null,
  rundeEtiketter: {},
  tankeResumeer: {},
  finalAnswerStarted: true,
  status: 'done',
}

/** Widget: `type: 'file'`, `text/html`, dannet af Jarvis selv. */
const widget: ContentBlock = {
  type: 'file',
  filename: 'flade.html',
  mime_type: 'text/html; charset=utf-8',
  kilde: 'generated',
  attachment_id: 'att-widget',
}

/** En udgivet HTML-fil er IKKE en widget — den skal ikke rammes. */
const udgivetHtml: ContentBlock = {
  type: 'file',
  filename: 'rapport.html',
  mime_type: 'text/html',
  kilde: 'published',
  attachment_id: 'att-pub',
}

const svar: ContentBlock = { type: 'text', text: 'Her er svaret.', phase: 'final_answer' }

function typer(blocks: ContentBlock[]): string[] {
  return blocks.map((block) => (block.type === 'file' ? `file:${block.filename}` : block.type))
}

describe('deriveChatFlow — leverancen hører i bunden', () => {
  it('flytter widgetten efter slutteksten naar den ankommer FOER teksten', () => {
    // Den levende rækkefølge: vis_widget kaldes i en runde før teksten skrives.
    const model = deriveChatFlow({ ...base, blocks: [widget, svar] })
    expect(typer(model.finalBlocks)).toEqual(['text', 'file:flade.html'])
  })

  it('giver IDENTISK raekkefoelge for levende og persisteret besked', () => {
    // Persisteret rækkefølge (serveren har allerede flyttet den ned).
    const persisteret = deriveChatFlow({ ...base, blocks: [svar, widget] })
    const levende = deriveChatFlow({ ...base, blocks: [widget, svar] })
    expect(typer(levende.finalBlocks)).toEqual(typer(persisteret.finalBlocks))
  })

  it('lader image og video blive ved deres vaerktoej', () => {
    const billede: ContentBlock = {
      type: 'image',
      src: 'https://x/y.png',
      alt: 'billede',
      attachment_id: 'att-img',
    }
    const model = deriveChatFlow({ ...base, blocks: [billede, svar] })
    // Billedet illustrerer det der tales om netop dér — det flyttes ikke.
    expect(typer(model.finalBlocks)).toEqual(['image', 'text'])
  })

  it('rammer IKKE en udgivet html-fil (kilde != generated)', () => {
    const model = deriveChatFlow({ ...base, blocks: [udgivetHtml, svar] })
    expect(typer(model.finalBlocks)).toEqual(['file:rapport.html', 'text'])
  })

  it('laegger en leverance bagerst naar der ikke er tekst efter den', () => {
    const model = deriveChatFlow({ ...base, blocks: [svar, widget] })
    expect(typer(model.finalBlocks)).toEqual(['text', 'file:flade.html'])
  })

  it('bevarer raekkefoelgen mellem flere leverancer', () => {
    const anden: ContentBlock = { ...widget, filename: 'flade2.html', attachment_id: 'att-2' }
    const model = deriveChatFlow({ ...base, blocks: [widget, anden, svar] })
    expect(typer(model.finalBlocks)).toEqual(['text', 'file:flade.html', 'file:flade2.html'])
  })
})
