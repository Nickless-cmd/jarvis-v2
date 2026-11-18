import { describe, expect, it } from 'vitest'
import { fordelBilledRaekker } from './billedGrid'

describe('fordelBilledRaekker', () => {
  it('pakker så mange fliser som minimumsbredden tillader på hver række', () => {
    expect(fordelBilledRaekker(5, 220)).toEqual([3, 2])
  })

  it('holder en enkelt række når alle fliser kan være mellem minimum og maksimum', () => {
    expect(fordelBilledRaekker(3, 500)).toEqual([3])
  })

  it('bevarer mindst én flise på smalle flader', () => {
    expect(fordelBilledRaekker(2, 40)).toEqual([1, 1])
  })

  it('giver ingen rækker når der ikke er fliser', () => {
    expect(fordelBilledRaekker(0, 320)).toEqual([])
  })
})
