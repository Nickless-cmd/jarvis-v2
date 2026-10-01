import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState } from './streamReducer'
import type { StreamEvent } from './sseProtocol'

const start = (id: string) => ({
  type: 'message_start',
  message: { id, model: 'm', provider: 'deepseek', lane: 'primary', session_id: 's',
             usage: { input_tokens: 0, output_tokens: 0 } },
} as unknown as StreamEvent)
const tekst = (t: string) => ([
  { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: t } },
] as unknown as StreamEvent[])
const runEvent = (id: string) => ({
  type: 'system_event', kind: 'run', payload: { run_id: id },
} as unknown as StreamEvent)

describe('blinket: et tomt message_start-id maa ikke rydde blokke', () => {
  it('bevarer teksten naar replayets message_start har tomt id', () => {
    // Saadan ser turen ud i produktion: message_start kommer FOER et legacy-event
    // har baaret run_id (sse_v2:705), saa id'et er tomt. Run-eventet saetter
    // derefter det rigtige. Ved replay kommer message_start igen — stadig tomt.
    const s = [start(''), runEvent('visible-abc'), ...tekst('Her er hele svaret.'),
               start('')].reduce(streamReducer, initialStreamState())
    const synlig = s.blocks.filter(Boolean).map((b) => (b?.type === 'text' ? b.text : '')).join('')
    expect(synlig).toContain('Her er hele svaret.')
  })

  it('et AEGTE nyt run rydder stadig', () => {
    const s = [start('visible-et'), ...tekst('gammelt'), start('visible-to')]
      .reduce(streamReducer, initialStreamState())
    expect(s.blocks.filter(Boolean)).toHaveLength(0)
    expect(s.activeRunId).toBe('visible-to')
  })

  it('run-eventets id overlever et tomt message_start', () => {
    const s = [start(''), runEvent('visible-abc'), start('')]
      .reduce(streamReducer, initialStreamState())
    expect(s.activeRunId).toBe('visible-abc')
  })
})
