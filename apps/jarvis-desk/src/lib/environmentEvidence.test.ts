import { describe, expect, it } from 'vitest'
import type { ContentBlock } from './sseProtocol'
import {
  buildEnvironmentEvidence,
  mergeEnvironmentEvidence,
  sourcesForTool,
  type ToolEvidence,
} from './environmentEvidence'

const tool = (
  id: string,
  name: string,
  input: Record<string, unknown>,
  result?: string,
  status: 'running' | 'done' | 'error' = 'done',
): ContentBlock => ({ type: 'tool_use', id, name, input, result, status })

describe('environment evidence', () => {
  it('bevarer tool-id, input, status og resultat', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('t1', 'web_search', { query: 'wled' }, '{"url":"https://kno.wled.ge"}'),
    ]])
    expect(evidence.tools[0]).toEqual({
      id: 't1', name: 'web_search', input: { query: 'wled' }, status: 'done',
      result: '{"url":"https://kno.wled.ge"}',
    })
  })

  it('binder URL til input og resultat fra det tool der fandt den', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('t1', 'web_search', { query: 'wled', url: 'https://wled.me/start' },
        'Læs https://kno.wled.ge/basics/getting-started/'),
    ]])
    expect(evidence.sources).toEqual([
      expect.objectContaining({
        url: 'https://wled.me/start', toolUseId: 't1', toolName: 'web_search', origin: 'tool_input',
      }),
      expect.objectContaining({
        url: 'https://kno.wled.ge/basics/getting-started/', toolUseId: 't1',
        toolName: 'web_search', origin: 'tool_result', resultExcerpt: expect.stringContaining('kno.wled.ge'),
      }),
    ])
  })

  it('lægger kilder fra svartekst sidst og filtrerer interne adresser', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('t1', 'web_fetch', {}, 'https://fund.dk/a http://localhost:8000/x'),
      { type: 'text', text: 'Se også https://citeret.dk/b og http://10.0.0.2/x' },
    ]])
    expect(evidence.sources.map((source) => [source.domaene, source.origin])).toEqual([
      ['fund.dk', 'tool_result'],
      ['citeret.dk', 'assistant_text'],
    ])
  })

  it('udleder både top-level og spawned agent-id uden at gætte', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('a', 'explore', { query: 'find parser' },
        '{"agent_id":"agent-a","role":"researcher","agent_status":"completed"}'),
      tool('b', 'dispatch_code_mode_task', { task: 'review' },
        '{"spawned":[{"role":"reviewer","agent_id":"agent-b"},{"role":"tester","error":"nede"}]}'),
    ]])
    expect(evidence.agents).toEqual([
      { agentId: 'agent-a', role: 'researcher', goal: 'find parser', status: 'completed', dispatchToolUseId: 'a' },
      { agentId: 'agent-b', role: 'reviewer', goal: 'review', dispatchToolUseId: 'b' },
    ])
  })

  it('gør ikke task eller ugyldigt JSON til Agent Pool-agenter', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('t1', 'task', { prompt: 'se efter' }, 'færdig'),
      tool('t2', 'explore', { query: 'find' }, '{"agent_id":'),
    ]])
    expect(evidence.agents).toEqual([])
  })

  it('seneste blok med samme tool-id vinder uden at flytte rækkefølgen', () => {
    const evidence = buildEnvironmentEvidence([
      [tool('t1', 'web_search', { query: 'først' }, undefined, 'running'), tool('t2', 'read_file', { path: 'x' })],
      [tool('t1', 'web_search', { query: 'først' }, 'https://færdig.dk', 'done')],
    ])
    expect(evidence.tools.map((entry) => entry.id)).toEqual(['t1', 't2'])
    expect(evidence.tools[0]).toEqual(expect.objectContaining({ status: 'done', result: 'https://færdig.dk' }))
  })

  it('deduplikerer samme URL og agent-id på tværs af grupper', () => {
    const evidence = buildEnvironmentEvidence([[
      tool('a', 'explore', { query: 'x' }, '{"agent_id":"agent-a","findings":"https://dr.dk/a"}'),
      { type: 'text', text: 'https://dr.dk/a' },
      tool('b', 'send_message_to_agent', { agent_id: 'agent-a' }, '{"agent_id":"agent-a"}'),
    ]])
    expect(evidence.sources).toHaveLength(1)
    expect(evidence.agents).toHaveLength(1)
  })

  it('fletter historik og live, hvor liveversionen vinder', () => {
    const history = buildEnvironmentEvidence([[tool('t1', 'web_search', { query: 'x' }, undefined, 'running')]])
    const live = buildEnvironmentEvidence([[tool('t1', 'web_search', { query: 'x' }, 'https://dr.dk', 'done')]])
    const merged = mergeEnvironmentEvidence(history, live)
    expect(merged.tools).toEqual([expect.objectContaining({ id: 't1', status: 'done', result: 'https://dr.dk' })])
    expect(merged.sources.map((source) => source.url)).toEqual(['https://dr.dk'])
  })

  it('finder kun kilder fra det givne tool', () => {
    const entry: ToolEvidence = {
      id: 't1', name: 'web_search', input: { query: 'x' }, status: 'done',
      result: 'https://dr.dk/a https://tv2.dk/b',
    }
    expect(sourcesForTool(entry).map((source) => source.domaene)).toEqual(['dr.dk', 'tv2.dk'])
  })
})
