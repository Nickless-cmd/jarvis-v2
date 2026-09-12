import { streamReducer, initialStreamState } from './streamReducer'
import { blocksToPersisted } from './blocksToPersisted'
import type { StreamEvent } from './sseProtocol'

/**
 * «Tænkte i xx min/sekunder» — Bjørn 12/9-2026.
 *
 * `ThinkingSummary` har kunnet vise varigheden hele tiden; feltet blev bare
 * aldrig fyldt af nogen. Serveren måler den ikke, så klienten gør det selv.
 */
function koer(events: StreamEvent[]) {
  return events.reduce((s, e) => streamReducer(s, e), initialStreamState())
}

const start = (i: number): StreamEvent =>
  ({ type: 'content_block_start', index: i, content_block: { type: 'thinking', thinking: '' } } as StreamEvent)
const delta = (i: number, t: string): StreamEvent =>
  ({ type: 'content_block_delta', index: i, delta: { type: 'thinking_delta', thinking: t } } as StreamEvent)

describe('tænketid', () => {
  afterEach(() => { jest.restoreAllMocks() })

  it('måler fra første tanke til den sidste', () => {
    const ur = jest.spyOn(Date, 'now')
    ur.mockReturnValue(1_000_000)
    let s = koer([start(0)])
    ur.mockReturnValue(1_014_000) // 14 sekunder senere
    s = streamReducer(s, delta(0, 'jeg overvejer noget'))

    const gemt = blocksToPersisted(s.blocks)
    const tanke = gemt.find((b) => b.type === 'thinking')
    expect(tanke?.seconds).toBe(14)
  })

  it('lange tanker måles i minutter uden at miste sekunderne', () => {
    const ur = jest.spyOn(Date, 'now')
    ur.mockReturnValue(0)
    let s = koer([start(0)])
    ur.mockReturnValue(134_000) // 2 min 14 s
    s = streamReducer(s, delta(0, 'en lang tanke'))
    expect(blocksToPersisted(s.blocks).find((b) => b.type === 'thinking')?.seconds).toBe(134)
  })

  it('en umålt tanke får INGEN tid — ikke nul', () => {
    // «Tænkte i 0 s» ville være en påstand vi ikke har dækning for. Uden tal
    // falder etiketten tilbage til «Tænkte», og det er ærligt.
    const gemt = blocksToPersisted([{ type: 'thinking', thinking: 'uden ur' }])
    expect(gemt[0]?.seconds).toBeUndefined()
  })

  it('en tanke der tog nul tid får heller INGEN tid', () => {
    // Samme skel som ovenfor, men med ur: 0 og «umålt» er to forskellige ting,
    // og kun det ene af dem er en påstand.
    const gemt = blocksToPersisted([
      { type: 'thinking', thinking: 'lynhurtig', startet: 500, sidst: 500 },
    ])
    expect(gemt[0]?.seconds).toBeUndefined()
  })

  it('starttidspunktet flytter sig ikke når tanken vokser', () => {
    const ur = jest.spyOn(Date, 'now')
    ur.mockReturnValue(5_000)
    let s = koer([start(0)])
    for (const t of [6_000, 7_000, 20_000]) {
      ur.mockReturnValue(t)
      s = streamReducer(s, delta(0, 'x'))
    }
    expect(blocksToPersisted(s.blocks).find((b) => b.type === 'thinking')?.seconds).toBe(15)
  })
})
