import { afterEach, describe, expect, it, vi } from 'vitest'
import { __resetSharedRead, setStreamActive, sharedRead } from './sharedRead'

afterEach(() => {
  __resetSharedRead()
  vi.useRealTimers()
})

describe('sharedRead — kollapser dublerede læsninger', () => {
  it('deduplikerer samtidige kald til samme nøgle til ÉN fetch', async () => {
    const fetcher = vi.fn().mockResolvedValue('svar')
    // 4 komponenter spørger samtidig (Sidebar/TakeoverHost/ChatView/CodeView)
    const results = await Promise.all([
      sharedRead('active-runs', fetcher, { ttlMs: 1000 }),
      sharedRead('active-runs', fetcher, { ttlMs: 1000 }),
      sharedRead('active-runs', fetcher, { ttlMs: 1000 }),
      sharedRead('active-runs', fetcher, { ttlMs: 1000 }),
    ])
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(results).toEqual(['svar', 'svar', 'svar', 'svar'])
  })

  it('genbruger et friskt svar indenfor TTL, og henter igen når TTL er udløbet', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockResolvedValue('v')
    await sharedRead('k', fetcher, { ttlMs: 1000 })
    await sharedRead('k', fetcher, { ttlMs: 1000 })
    expect(fetcher).toHaveBeenCalledTimes(1)      // cache-hit
    vi.advanceTimersByTime(1200)
    await sharedRead('k', fetcher, { ttlMs: 1000 })
    expect(fetcher).toHaveBeenCalledTimes(2)      // TTL udløbet → ny fetch
  })

  it('holder nøgler adskilt', async () => {
    const a = vi.fn().mockResolvedValue('a')
    const b = vi.fn().mockResolvedValue('b')
    expect(await sharedRead('a', a, { ttlMs: 1000 })).toBe('a')
    expect(await sharedRead('b', b, { ttlMs: 1000 })).toBe('b')
    expect(a).toHaveBeenCalledTimes(1)
    expect(b).toHaveBeenCalledTimes(1)
  })
})

describe('sharedRead — backoff mens Jarvis streamer', () => {
  it('forlænger TTL kraftigt når et run er aktivt (poll-storm må ikke kvæle SSE)', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockResolvedValue('v')
    setStreamActive(true)
    await sharedRead('k', fetcher, { ttlMs: 1000, streamingTtlMs: 10_000 })
    vi.advanceTimersByTime(5000)                  // ville normalt være udløbet
    await sharedRead('k', fetcher, { ttlMs: 1000, streamingTtlMs: 10_000 })
    expect(fetcher).toHaveBeenCalledTimes(1)      // stadig cache-hit under streaming
    setStreamActive(false)
    vi.advanceTimersByTime(1200)
    await sharedRead('k', fetcher, { ttlMs: 1000, streamingTtlMs: 10_000 })
    expect(fetcher).toHaveBeenCalledTimes(2)      // normal kadence igen
  })
})

describe('sharedRead — fejl må ikke forgifte cachen', () => {
  it('cacher ikke fejl, og lader næste kald prøve igen', async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error('netværk'))
      .mockResolvedValue('ok')
    await expect(sharedRead('k', fetcher, { ttlMs: 5000 })).rejects.toThrow('netværk')
    await expect(sharedRead('k', fetcher, { ttlMs: 5000 })).resolves.toBe('ok')
    expect(fetcher).toHaveBeenCalledTimes(2)
  })
})
