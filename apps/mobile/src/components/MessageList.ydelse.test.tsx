/**
 * Ydelse under streaming (19/9-2026) — samme måling som desk fik.
 *
 * Hver delta i et svar gav én render af hele listen. Det der tælles her er
 * det tunge: hvor mange gange markdown-it parser tekst pr. delta. Før
 * rettelsen parsede hver synlig gemt boble sin markdown forfra ved HVER delta,
 * og den levende boble parsede hele svaret forfra ved hvert token.
 */
import MarkdownIt from 'markdown-it'
import { act, render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ChatMessage } from '../lib/types'
import type { ContentBlock } from '../lib/sseProtocol'

const SVAR = [
  '## Overskrift',
  '',
  'Et afsnit med **fed** tekst og `kode`, og lidt mere tekst så det ligner et svar.',
  '',
  '- punkt et',
  '- punkt to',
  '- punkt tre',
  '',
  'Endnu et afsnit der afslutter svaret.'
].join('\n')

function samtale(n: number): ChatMessage[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `m${i}`,
    role: i % 2 === 0 ? 'user' : 'assistant',
    content: i % 2 === 0 ? `spørgsmål ${i}` : `${SVAR}\n\n(svar ${i})`,
    created_at: '2026-09-19T12:00:00Z'
  }) as ChatMessage)
}

// Et levende svar der vokser med ét ord ad gangen, over flere afsnit.
function levende(i: number): ContentBlock[] {
  const ord = Array.from({ length: i }, (_, k) => (k % 25 === 24 ? 'slut.\n\n' : `ord${k}`))
  return [{ type: 'text', text: ord.join(' ') }]
}

async function maal(deltaer = 120) {
  const parse = jest.spyOn(MarkdownIt.prototype, 'parse')
  const beskeder = samtale(30)
  const s = await render(<MessageList messages={beskeder} blocks={[]} />)
  parse.mockClear()
  const t0 = Date.now()
  for (let i = 1; i <= deltaer; i++) {
    await act(async () => {
      s.rerender(<MessageList messages={beskeder} blocks={levende(i)} />)
    })
  }
  const ms = Date.now() - t0
  const parses = parse.mock.calls.length
  const tegn = parse.mock.calls.reduce((sum, c) => sum + String(c[0] ?? '').length, 0)
  parse.mockRestore()
  return { parsesPrDelta: parses / deltaer, tegnPrDelta: tegn / deltaer, msPrDelta: ms / deltaer }
}

it('måler markdown-arbejdet pr. delta', async () => {
  const r = await maal()
  // eslint-disable-next-line no-console
  console.log('YDELSE ' + JSON.stringify({
    parsesPrDelta: +r.parsesPrDelta.toFixed(2),
    tegnPrDelta: Math.round(r.tegnPrDelta),
    msPrDelta: +r.msPrDelta.toFixed(1)
  }))
  // Målt 19/9-2026 — før: 6 parses og 1.258 tegn pr. delta (hver synlig gemt
  // boble parsede forfra, og det levende svar blev parset helt). Efter: kun
  // den blok der skrives på, ~360 tegn. Grænserne har luft, men fanger en
  // tilbagevenden til det gamle mønster.
  expect(r.parsesPrDelta).toBeLessThanOrEqual(1.5)
  expect(r.tegnPrDelta).toBeLessThan(700)
})
