import { denseBlocks } from './blockHelpers'
import type { ContentBlock } from './sseProtocol'

it('removes undefined holes without throwing', () => {
  const sparse = [
    { type: 'tool_use', id: 't', name: 'bash', input: {} },
    undefined,
    { type: 'text', text: 'hej' }
  ] as unknown as ContentBlock[]
  const dense = denseBlocks(sparse)
  expect(dense.map((b) => b.type)).toEqual(['tool_use', 'text'])
  // Iterating .type over the dense result never throws.
  expect(() => dense.map((b) => b.type)).not.toThrow()
})

it('tolerates empty / all-hole input', () => {
  expect(denseBlocks([])).toEqual([])
  expect(denseBlocks([undefined, null] as never)).toEqual([])
  expect(denseBlocks(undefined as never)).toEqual([])
})
