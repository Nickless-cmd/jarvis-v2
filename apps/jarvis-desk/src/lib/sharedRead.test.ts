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

describe('sharedRead — loftSynligMs: den delte cache må ikke skjule et nyt run i ro', () => {
  // Cachen ganges med hvile-faktoren (2 s × 8 = 16 s), så selv en hurtig poll fik et
  // GAMMELT «intet run» tilbage — lag nummer to i de 24 s der skjulte wake-runnet.
  async function iRo() {
    vi.useFakeTimers()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    const ro = await import('./ro')
    let roNu = 5_000_000
    ro._saetUr(() => roNu)
    ro._nulstil()                      // livstegn = nu
    roNu += ro.ROLIG_EFTER_MS + 1      // 3 min uden input → faktor 8
    return ro
  }

  afterEach(async () => {
    const ro = await import('./ro')
    ro._saetUr(() => Date.now())
    vi.restoreAllMocks()
  })

  it('et synligt, hvilende vindue genbruger højst loftet — ikke TTL × faktor', async () => {
    await iRo()
    const fetcher = vi.fn().mockResolvedValue('v')
    const valg = { ttlMs: 2000, streamingTtlMs: 10_000, loftSynligMs: 2000 }

    await sharedRead('k', fetcher, valg)
    vi.advanceTimersByTime(2100)
    await sharedRead('k', fetcher, valg)

    expect(fetcher).toHaveBeenCalledTimes(2)       // uden loft: 16 s cache → 1 hent
  })

  it('uden loftSynligMs er cachen uændret forlænget i ro', async () => {
    await iRo()
    const fetcher = vi.fn().mockResolvedValue('v')

    await sharedRead('k2', fetcher, { ttlMs: 2000 })
    vi.advanceTimersByTime(2100)
    await sharedRead('k2', fetcher, { ttlMs: 2000 })

    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('et SKJULT vindue holder sin lange cache — loftet gælder kun synlige', async () => {
    await iRo()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    const fetcher = vi.fn().mockResolvedValue('v')
    const valg = { ttlMs: 2000, loftSynligMs: 2000 }

    await sharedRead('k4', fetcher, valg)
    vi.advanceTimersByTime(2100)
    await sharedRead('k4', fetcher, valg)

    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('mens EGEN stream kører, gælder streamingTtlMs stadig (poll-storm må ikke kvæle SSE)', async () => {
    await iRo()
    setStreamActive(true)
    const fetcher = vi.fn().mockResolvedValue('v')
    const valg = { ttlMs: 2000, streamingTtlMs: 10_000, loftSynligMs: 2000 }

    await sharedRead('k3', fetcher, valg)
    vi.advanceTimersByTime(5000)
    await sharedRead('k3', fetcher, valg)

    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
