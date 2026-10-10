import { describe, expect, it } from 'vitest'

import { asyncSpawn } from './asyncSpawn.js'

describe('asyncSpawn', () => {
  it('preserves final stdout, stderr and status after extraction', async () => {
    const result = await asyncSpawn(process.execPath, [
      '-e',
      "process.stdout.write('out');process.stderr.write('err')",
    ])
    expect(result).toMatchObject({
      stdout: 'out',
      stderr: 'err',
      status: 0,
      signal: null,
      timed_out: false,
    })
  })

  it('emits decoded ordered chunks and preserves final buffers', async () => {
    const seen: Array<{ stream: string; seq: number; chunk: string }> = []
    const result = await asyncSpawn(process.execPath, [
      '-e',
      "process.stdout.write(Buffer.from([0xc3]));setTimeout(()=>process.stdout.write(Buffer.from([0xa6,10])),20)",
    ], {}, (delta) => seen.push(delta))
    expect(seen.map((delta) => delta.seq)).toEqual(
      [...seen.keys()].map((index) => index + 1),
    )
    expect(seen.map((delta) => delta.chunk).join('')).toBe('æ\n')
    expect(result.stdout).toBe('æ\n')
    expect(result.first_output_ms).not.toBeNull()
    expect(result.process_ms).toBeGreaterThanOrEqual(result.first_output_ms ?? 0)
  })

  it('batches an output flood while preserving the complete bounded final buffer', async () => {
    const seen: Array<{ stream: string; seq: number; chunk: string }> = []
    const result = await asyncSpawn(process.execPath, [
      '-e',
      "let n=0;const t=setInterval(()=>{process.stdout.write('x'.repeat(100));if(++n===100)clearInterval(t)},1)",
    ], { maxBuffer: 20_000 }, (delta) => seen.push(delta))
    expect(result.stdout).toHaveLength(10_000)
    expect(seen.map((delta) => delta.chunk).join('')).toBe(result.stdout)
    expect(seen.length).toBeLessThan(20)
  })
})
