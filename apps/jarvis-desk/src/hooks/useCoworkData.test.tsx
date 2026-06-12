import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

vi.mock('../lib/coworkApi', () => ({
  getCoworkQueue: vi.fn().mockResolvedValue([{ id: 'x', kind: 'initiative', title: 'T', detail: '', source: 'initiative' }]),
  getCoworkPlans: vi.fn().mockResolvedValue([]),
  getCoworkChannels: vi.fn().mockResolvedValue([{ name: 'discord', online: true, unread: 1 }]),
  resolveQueueItem: vi.fn().mockResolvedValue(undefined),
}))

import { useCoworkData } from './useCoworkData'

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('useCoworkData', () => {
  it('henter queue+plans (+channels for owner)', async () => {
    const { result } = renderHook(() => useCoworkData(cfg, true))
    await waitFor(() => expect(result.current.queue.length).toBe(1))
    await waitFor(() => expect(result.current.channels.length).toBe(1))
  })
  it('springer channels over for member', async () => {
    const { result } = renderHook(() => useCoworkData(cfg, false))
    await waitFor(() => expect(result.current.queue.length).toBe(1))
    expect(result.current.channels.length).toBe(0)
  })
})
