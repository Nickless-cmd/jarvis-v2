import { describe, it, expect, vi } from 'vitest'
import { detectTools, REQUIRED_TOOLS } from './depDoctor'

describe('depDoctor', () => {
  it('markerer present=false når which fejler', async () => {
    const which = vi.fn(async (t: string) => t === 'git') // kun git findes
    const res = await detectTools(which)
    expect(res.find((r) => r.tool === 'git')!.present).toBe(true)
    expect(res.find((r) => r.tool === 'node')!.present).toBe(false)
    expect(res.map((r) => r.tool).sort()).toEqual([...REQUIRED_TOOLS].sort())
  })
})
