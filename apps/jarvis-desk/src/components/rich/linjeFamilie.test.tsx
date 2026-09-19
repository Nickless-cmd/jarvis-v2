import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { ToolGroupCard } from './ToolGroupCard'
import { ThinkingLine } from './ThinkingLine'
import { SkillLine, SkillSurfaceLine } from './SkillLine'
import type { ToolGroupBlock } from '../../lib/toolRounds'

/**
 * Bjørn 19/9-2026: «tænker linje og skill linje bør have det samme
 * tema/design/udseende så de faktisk matcher nogenlunde alle 3 linjer».
 *
 * Før: tanke- og skill-linjen skiftede mellem ChevronRight og ChevronDown
 * med runde-linjens `.toolgroup-chevron`, som DREJER -90°. Foldet pegede
 * pilen op, åben pegede den til højre — og den var skjult uden hover, fordi
 * `er-aaben` aldrig blev sat. Ingen test holdt de tre linjer sammen.
 */
const runde: ToolGroupBlock = {
  type: 'tool_group', kind: 'round', count: 2,
  tools: [0, 1].map((i) => ({ type: 'tool_use' as const, id: `t${i}`, name: 'read_file', input: { path: `/f${i}` }, status: 'done' as const, result: 'x' })),
}

const linjer: [string, () => ReturnType<typeof render>][] = [
  ['runde', () => render(<ToolGroupCard block={runde} density="compact" />)],
  ['tanke', () => render(<ThinkingLine text="jeg overvejer" seconds={4} live={false} />)],
  ['skill', () => render(<SkillLine density="compact" block={{ type: 'tool_use', id: 's1', name: 'skill_gate', input: {}, status: 'done',
    result: JSON.stringify({ gate_result: 'invoked', skill_name: 'xlsx', score: 0.8, all_matches: [{ name: 'xlsx', score: 0.8 }] }) }} />)],
  ['skill-flade', () => render(<SkillSurfaceLine block={{ type: 'skill_surface', matches: [{ name: 'xlsx', score: 0.8, primary: true }] } as never} />)],
]

describe('de tre linjer er bygget ens', () => {
  it.each(linjer)('%s: ikon i fast celle, titel, én caret der drejes', (_navn, tegn) => {
    const { container } = tegn()
    const linje = container.querySelector('.toolgroup')!
    expect(linje.querySelector('.toolgroup-head > .toolgroup-spark > .toolgroup-icon')).not.toBeNull()
    expect(linje.querySelector('.toolgroup-label .linje-titel')).not.toBeNull()
    expect(linje.querySelectorAll('.toolgroup-celle .toolgroup-chevron')).toHaveLength(1)
    expect(linje.className).not.toMatch(/er-aaben/)
    fireEvent.click(linje.querySelector('.toolgroup-head')!)
    expect(linje.className).toMatch(/er-aaben/)
    expect(linje.querySelector('.toolgroup-body')).not.toBeNull()
  })

  it('tanke og skill glitrer mens de arbejder — som runden', () => {
    const t = render(<ThinkingLine text="" live startet={Date.now()} />)
    expect(t.container.querySelector('.linje-titel')!.className).toMatch(/shimmer/)
    const s = render(<SkillLine density="compact" block={{ type: 'tool_use', id: 's1', name: 'skill_gate', input: { query: 'x' }, status: 'running' }} />)
    expect(s.container.querySelector('.linje-titel')!.className).toMatch(/shimmer/)
  })
})
