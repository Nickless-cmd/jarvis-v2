import { gemteEtiketter } from './persistedBlocks'
import type { ChatMessage } from './types'

// Den GEMTE runde-sætning (19/9-2026). Før blev den kun streamet og var væk i
// det øjeblik turen var gemt. Nu gemmer serveren den som Claude Desktops egen
// blok, og den slås op på samme nøgle som den live: kaldets id.
const besked = (content_json: unknown): ChatMessage =>
  ({ id: 'm1', role: 'assistant', content: 'x', content_json } as unknown as ChatMessage)

it('slår sætningen op på hvert kald den dækker', () => {
  const m = besked([
    { type: 'tool_use', id: 'a', name: 'read_file', input: {} },
    { type: 'tool_use', id: 'b', name: 'read_file', input: {} },
    { type: 'tool_use_summary', summary: 'Fandt fejlen', preceding_tool_use_ids: ['a', 'b'] },
  ])
  expect(gemteEtiketter([m])).toEqual({ a: 'Fandt fejlen', b: 'Fandt fejlen' })
})

it('tager også content_json som streng — API\'et har sendt begge former', () => {
  const m = besked(JSON.stringify([{ type: 'tool_use_summary', summary: 'X Y', preceding_tool_use_ids: ['c'] }]))
  expect(gemteEtiketter([m])).toEqual({ c: 'X Y' })
})

it('ignorerer tomme sætninger og beskeder uden blokke', () => {
  const tom = besked([{ type: 'tool_use_summary', summary: '  ', preceding_tool_use_ids: ['a'] }])
  expect(gemteEtiketter([tom, besked(null)])).toEqual({})
})
