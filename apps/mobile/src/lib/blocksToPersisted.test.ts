import { blocksToPersisted } from './blocksToPersisted'
import type { ContentBlock } from './sseProtocol'

const t = (o: Partial<Extract<ContentBlock, { type: 'tool_use' }>> = {}) =>
  ({ type: 'tool_use' as const, id: 'b1', name: 'bash', input: { command: 'ls' }, ...o })

it('taenkningen foelger MED den faerdige besked', () => {
  // Foer forsvandt den i det sekund svaret var faerdigt og kom foerst igen
  // ved naeste app-start.
  const ud = blocksToPersisted([{ type: 'thinking', thinking: 'hmm' }])
  expect(ud).toEqual([{ type: 'thinking', text: 'hmm' }])
})

it('et faerdigt vaerktoej bliver til BAADE kald og resultat', () => {
  // Det er den form den gemte besked har, og MessageList laeser dem hver for
  // sig.
  const ud = blocksToPersisted([t({ status: 'done', result: 'a.py b.py' })])
  expect(ud).toEqual([
    { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 'b1' },
    { type: 'tool_result', tool_use_id: 'b1', content: 'a.py b.py', status: 'ok' },
  ])
})

it('en FEJLET kald baerer sin status', () => {
  const ud = blocksToPersisted([t({ status: 'error', result: 'boom' })])
  expect(ud[1]).toEqual({ type: 'tool_result', tool_use_id: 'b1', content: 'boom', status: 'error' })
})

it('et kald UDEN resultat faar ingen resultat-blok', () => {
  expect(blocksToPersisted([t({ status: 'running' })]))
    .toEqual([{ type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 'b1' }])
})

it('FORELOEBIGE raekker gemmes IKKE', () => {
  // De er annonceringer af noget der aldrig blev koert faerdigt; gemt ville de
  // snurre for evigt i historikken.
  expect(blocksToPersisted([t({ foreloebig: { startet: 1, skridt: 1, etiket: 'x' } })]))
    .toEqual([])
})

it('tom tekst og tom taenkning springes over', () => {
  expect(blocksToPersisted([
    { type: 'text', text: '   ' },
    { type: 'thinking', thinking: '' },
  ])).toEqual([])
})

it('huller i arrayet braekker ikke', () => {
  const med: ContentBlock[] = []
  med[2] = { type: 'text', text: 'hej' }
  expect(blocksToPersisted(med)).toEqual([{ type: 'text', text: 'hej' }])
})
