import { describe, it, expect } from 'vitest'
import { describeTool, summarizeRound, countFromResult, subjectFromInput } from './toolRound'
import type { ContentBlock } from './sseProtocol'

type ToolUse = Extract<ContentBlock, { type: 'tool_use' }>
const t = (name: string, input: Record<string, unknown>, status: 'done' | 'running' = 'done', result?: string): ToolUse =>
  ({ type: 'tool_use', id: name + JSON.stringify(input), name, input, status, result })

/**
 * Porteret 1:1 fra mobilens toolSummary.ts + toolGroup.ts (Bjørn 8/9-2026:
 * «det skal lige 1:1 — det er i den mobil app du byggede på tidligere»).
 */

describe('linjen siger hvad der laves, ikke hvilket værktøj', () => {
  it('bruger emnet frem for værktøjsnavnet', () => {
    expect(describeTool('read_file', { path: '/a/b/agent.ts' }, false)).toBe('Læste agent.ts')
  })

  it('bøjer verbet mens det kører', () => {
    expect(describeTool('read_file', { path: 'x.ts' }, true)).toBe('Læser x.ts…')
  })

  it('falder tilbage på værktøjsnavnet frem for at finde på noget', () => {
    expect(describeTool('mystisk_ting', {}, false)).toBe('Kørte mystisk_ting')
  })

  it('operator-varianten er samme handling for læseren', () => {
    // `operator_read_file` og `read_file` gør det samme; kun navnet er andet.
    expect(describeTool('operator_read_file', { path: 'x.ts' }, false)).toBe('Læste x.ts')
  })

  it('en lang kommando klippes, en sti bliver til filnavnet', () => {
    expect(subjectFromInput({ path: '/meget/lang/sti/til/fil.py' })).toBe('fil.py')
    expect(subjectFromInput({ command: 'x'.repeat(80) }).endsWith('…')).toBe(true)
  })
})

describe('én linje for hele runden', () => {
  it('ét kald → dets egen beskrivelse', () => {
    expect(summarizeRound([t('read_file', { path: 'a.ts' })])).toBe('Læste a.ts')
  })

  it('flere ens → tælles op', () => {
    expect(summarizeRound([
      t('read_file', { path: 'a.ts' }), t('read_file', { path: 'b.ts' }),
    ])).toBe('Læste 2 filer')
  })

  it('blandede → «værktøjer»', () => {
    expect(summarizeRound([
      t('read_file', { path: 'a.ts' }), t('bash', { command: 'ls' }),
    ])).toBe('Kørte 2 værktøjer')
  })

  it('resultatets EGEN optælling slår antallet af kald', () => {
    // «Ændrede 16 filer» siger mere end «Kørte 3 værktøjer».
    expect(summarizeRound([
      t('edit_file', { path: 'a' }, 'done', 'modified 9 filer'),
      t('edit_file', { path: 'b' }, 'done', 'modified 7 filer'),
    ])).toBe('Redigerede 16 filer')
  })

  it('kører den, står linjen i nutid med prikker', () => {
    expect(summarizeRound([
      t('read_file', { path: 'a' }, 'running'), t('read_file', { path: 'b' }, 'running'),
    ])).toBe('Læser 2 filer…')
  })

  it('vi gætter ikke et tal der ikke står der', () => {
    expect(countFromResult('alt gik fint')).toBeUndefined()
    expect(countFromResult('fandt 12 træffere')).toBe(12)
  })

  it('tom runde giver tom linje — ikke en tom ramme', () => {
    expect(summarizeRound([])).toBe('')
  })
})
