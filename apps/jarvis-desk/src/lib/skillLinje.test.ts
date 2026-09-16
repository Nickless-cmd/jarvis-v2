import { describe, expect, it } from 'vitest'
import { skillOversigt } from './skillLinje'
import { groupToolRounds } from './toolRounds'
import type { ContentBlock } from './sseProtocol'

type ToolUse = Extract<ContentBlock, { type: 'tool_use' }>
const kald = (name: string, input: Record<string, unknown>, status?: ToolUse['status'], result?: unknown): ToolUse => ({
  type: 'tool_use', id: `${name}-1`, name, input, status,
  result: result === undefined ? undefined : typeof result === 'string' ? result : JSON.stringify(result, null, 2),
})

describe('skillOversigt — skill_gate', () => {
  it('kører: nutid med forespørgslen', () => {
    const o = skillOversigt(kald('skill_gate', { query: 'lav et regneark over udgifter' }, 'running'))
    expect(o.titel).toBe('Tjekker skills for «lav et regneark over udgifter»')
    expect(o.koerer).toBe(true)
  })

  it('invoked + auto_use: navn, score, indlæst og størrelse', () => {
    const o = skillOversigt(kald('skill_gate', { query: 'x' }, 'done', {
      status: 'ok', gate_result: 'invoked', skill_name: 'xlsx', score: 0.823, mode: 'auto_use',
      instructions_full_length: 4213, skill_description: 'Regneark',
      all_matches: [{ name: 'xlsx', score: 0.823 }, { name: 'csv', score: 0.41 }],
    }))
    expect(o.titel).toBe('Skill-gate: xlsx')
    expect(o.meta).toEqual(['0,82', 'indlæst', '4,2k tegn'])
    expect(o.matches.map((m) => m.name)).toEqual(['xlsx', 'csv'])
    expect(o.beskrivelse).toBe('Regneark')
  })

  it('suggested: siger at den KUN er foreslået', () => {
    const o = skillOversigt(kald('skill_gate', {}, 'done', { gate_result: 'invoked', skill_name: 'pdf', score: 0.6, mode: 'suggested' }))
    expect(o.meta).toEqual(['0,60', 'kun foreslået'])
  })

  it('low_match: bedste bud fra suggestions', () => {
    const o = skillOversigt(kald('skill_gate', {}, 'done', { gate_result: 'low_match', suggestions: [{ name: 'pdf', score: 0.31 }] }))
    expect(o.titel).toBe('Skill-gate: intet sikkert match')
    expect(o.meta).toEqual(['bedst pdf 0,31'])
  })

  it('no_match', () => {
    expect(skillOversigt(kald('skill_gate', {}, 'done', { gate_result: 'no_match', suggestions: [] })).titel)
      .toBe('Skill-gate: ingen skill matchede')
  })

  it('status error i resultatet er en fejl, selv om kaldet sluttede', () => {
    const o = skillOversigt(kald('skill_gate', {}, 'done', { status: 'error', error: 'failed to load' }))
    expect(o.fejl).toBe(true)
    expect(o.titel).toBe('Skill-gaten fejlede')
  })

  it('klippet live-resultat (ugyldig JSON): felterne fiskes ud, størrelse udelades ikke-målbar', () => {
    const helt = JSON.stringify({ status: 'ok', gate_result: 'invoked', skill_name: 'xlsx', score: 0.9, mode: 'auto_use', instructions: 'y'.repeat(9000) }, null, 2)
    const o = skillOversigt(kald('skill_gate', {}, 'done', helt.slice(0, 4000)))
    expect(o.titel).toBe('Skill-gate: xlsx')
    expect(o.meta).toEqual(['0,90', 'indlæst'])
  })
})

describe('skillOversigt — skill_invoke', () => {
  const svar = { skill: { status: 'ok', skill_name: 'git-advanced', description: 'Git beyond commit', instructions: 'x'.repeat(6120) } }

  it('kører: navnet fra input', () => {
    expect(skillOversigt(kald('skill_invoke', { name: 'xlsx' }, 'running')).titel).toBe('Indlæser skill xlsx')
  })

  it('færdig: navn, størrelse og beskrivelse — produktionens form', () => {
    const o = skillOversigt(kald('skill_invoke', { name: 'git-advanced' }, 'done', svar))
    expect(o.titel).toBe('Indlæste skill git-advanced')
    expect(o.meta).toEqual(['6,1k tegn'])
    expect(o.beskrivelse).toBe('Git beyond commit')
  })

  it('sikkerhedsadvarsel står i linjen', () => {
    const o = skillOversigt(kald('skill_invoke', { name: 'x' }, 'done', { skill: { ...svar.skill, security_warning: 'YELLOW' } }))
    expect(o.meta).toContain('sikkerhedsadvarsel')
    expect(o.advarsel).toBe(true)
  })

  it('fejl', () => {
    expect(skillOversigt(kald('skill_invoke', { name: 'x' }, 'error', 'nope')).titel).toBe('Kunne ikke indlæse skill x')
  })
})

describe('runder', () => {
  it('skill-kald bryder runden og står alene', () => {
    const r = groupToolRounds([
      kald('read_file', { path: 'a' }, 'done'),
      kald('skill_invoke', { name: 'xlsx' }, 'done'),
      kald('read_file', { path: 'b' }, 'done'),
    ])
    expect(r.map((b) => (b.type === 'tool_use' ? b.name : b.type))).toEqual(['tool_group', 'skill_invoke', 'tool_group'])
  })
})
