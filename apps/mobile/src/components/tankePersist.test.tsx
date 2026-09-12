import { render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import { streamReducer, initialStreamState } from '../lib/streamReducer'
import { blocksToPersisted } from '../lib/blocksToPersisted'
import type { StreamEvent } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'

/**
 * Hele vejen: SSE-rammer → reducer → gemt besked → tråd.
 *
 * Bjørn: «tænker/tænkte i chatview forsvinder stadig efter end stream i stedet
 * for at persiste som tool results». Enhedstests af hvert led var grønne, så
 * fejlen må ligge i overgangen mellem dem — og dén kan kun en test der går
 * HELE vejen se.
 */
const E = (e: unknown) => e as StreamEvent

it('tænkningen overlever vejen fra stream til gemt besked', async () => {
  let s = initialStreamState()
  for (const e of [
    E({ type: 'message_start', message: { id: 'run1', usage: { input_tokens: 0 } } }),
    E({ type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } }),
    E({ type: 'content_block_delta', index: 0, delta: { type: 'thinking_delta', thinking: 'jeg overvejer' } }),
    E({ type: 'content_block_stop', index: 0 }),
    E({ type: 'content_block_start', index: 1, content_block: { type: 'tool_use', id: 't1', name: 'bash', input: {} } }),
    E({ type: 'content_block_start', index: 2, content_block: { type: 'tool_result', tool_use_id: 't1', content: 'ok' } }),
    E({ type: 'content_block_start', index: 3, content_block: { type: 'thinking', thinking: '' } }),
    E({ type: 'content_block_delta', index: 3, delta: { type: 'thinking_delta', thinking: 'nu ser jeg på det' } }),
    E({ type: 'content_block_start', index: 4, content_block: { type: 'text', text: '' } }),
    E({ type: 'content_block_delta', index: 4, delta: { type: 'text_delta', text: 'Færdig.' } }),
  ]) s = streamReducer(s, e)

  const gemt = blocksToPersisted(s.blocks)
  const tanker = gemt.filter((b) => b.type === 'thinking')
  expect(tanker.length).toBe(2)

  const msg: ChatMessage = {
    id: 'a1', role: 'assistant', content: 'Færdig.',
    created_at: '2026-09-13T00:00:00Z', content_json: gemt
  } as ChatMessage
  const v = await render(<MessageList messages={[msg]} blocks={[]} />)
  expect(v.queryAllByText(/Tænkte/).length).toBe(2)
})
