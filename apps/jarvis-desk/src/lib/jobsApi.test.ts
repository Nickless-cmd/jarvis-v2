import { describe, it, expect } from 'vitest'
import { kildeNavn, varighed } from './jobsApi'

/**
 * Linje 2 i panelet svarer på HVOR rækken kører — og det var netop den ene af
 * de to man ikke kunne se, da listen kun kendte serverens supervisor.
 *
 * `shell_operator` blev fanget 26/9-2026: uden den faldt en shell på hans
 * maskine igennem til «Server». `tool_operator` er samme fælde ét lag nede
 * (3/10-2026) — et `operator_bash`-kald ER et værktøjskald, men det kører
 * derovre. Fælden er ikke at strengen er ny; den er at standardgrenen er
 * «Server», så enhver ny operator-kilde fejler TAVST.
 */
describe('kildeNavn', () => {
  it('et værktøjskald på hans maskine falder ikke igennem til «Server»', () => {
    expect(kildeNavn('tool_operator')).toBe('Din maskine')
  })

  it('et værktøjskald på serveren er Server', () => {
    expect(kildeNavn('tool')).toBe('Server')
  })

  it('de hidtidige kilder er uændrede', () => {
    expect(kildeNavn('supervisor')).toBe('Server')
    expect(kildeNavn('shell')).toBe('Server')
    expect(kildeNavn('operator')).toBe('Din maskine')
    expect(kildeNavn('shell_operator')).toBe('Din maskine')
    expect(kildeNavn('agent')).toBe('Agent')
  })
})

describe('varighed', () => {
  it('viser den form CC bruger, og tom naar der intet tal er', () => {
    expect(varighed(137)).toBe('2m 17s')
    expect(varighed(1160)).toBe('19m 20s')
    expect(varighed(45)).toBe('45s')
    expect(varighed(null)).toBe('')
    expect(varighed(undefined)).toBe('')
  })
})
