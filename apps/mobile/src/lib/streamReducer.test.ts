import { initialStreamState, streamReducer } from './streamReducer'

it('accumulates streamed text', () => {
  let state = streamReducer(initialStreamState(), {
    type: 'message_start',
    message: {
      id: 'm1',
      model: 'deepseek',
      provider: 'ollama',
      lane: 'primary',
      session_id: 's1',
      usage: { input_tokens: 3, output_tokens: 0 }
    }
  })

  state = streamReducer(state, {
    type: 'content_block_start',
    index: 0,
    content_block: { type: 'text', text: '' }
  })

  state = streamReducer(state, {
    type: 'content_block_delta',
    index: 0,
    delta: { type: 'text_delta', text: 'Hej' }
  })

  expect(state.blocks).toEqual([{ type: 'text', text: 'Hej' }])
  expect(state.status).toBe('working')
})

it('captures run id from system event', () => {
  const state = streamReducer(initialStreamState(), {
    type: 'system_event',
    kind: 'run',
    payload: { run_id: 'visible-1' }
  })

  expect(state.activeRunId).toBe('visible-1')
})
