import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { parseNativeRichSpec } from './NativeRichBlock'

type KontraktCase = {
  name: string
  input: Record<string, unknown>
  guard: { level: 'ok' | 'delvis' | 'død'; errors: string[] }
  parser: { values: number[]; labelCount: number } | null
}

// Den samme fixture køres mod Python-guarden i
// tests/test_flade_maaling_over_tid_contract.py. Dermed kan ingen af siderne
// ændre kontrakten alene uden at mindst den ene test fejler.
const cases = JSON.parse(readFileSync(
  resolve(process.cwd(), '../../tests/fixtures/flade_maaling_over_tid_contract.json'),
  'utf8',
)) as KontraktCase[]

describe('maaling-over-tid guard/parser-kontrakt', () => {
  it.each(cases)('matcher guardens brugbarhedsdom for $name', ({ input, guard, parser: forventet }) => {
    const parsed = parseNativeRichSpec(JSON.stringify(input))

    if (guard.level === 'ok') expect(parsed).not.toBeNull()
    if (guard.level === 'død') expect(parsed).toBeNull()

    expect(parsed?.type).toBe(forventet === null ? undefined : 'chart')
    if (parsed?.type === 'chart' && forventet !== null) {
      expect(parsed.series[0]?.values).toEqual(forventet.values)
      expect(parsed.labels).toHaveLength(forventet.labelCount)
    }
  })
})
