import { describe, it, expect, vi, beforeEach } from 'vitest'

const createSession = vi.fn()
const startStream = vi.fn()
vi.mock('../lib/api', () => ({ createSession: (...a: unknown[]) => createSession(...a) }))
vi.mock('../lib/streamClient', () => ({ startStream: (...a: unknown[]) => startStream(...a) }))
vi.mock('../lib/composerPrefs', () => ({ readModelPrefs: () => ({ model: 'deepseek-flash', providerChoice: 'ollama' }) }))

import { sendHurtigt } from './hurtigChat'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('sendHurtigt', () => {
  beforeEach(() => { createSession.mockReset(); startStream.mockReset() })

  it('opretter en samtale, sender med composerens model og SLIPPER stroemmen ved run-id', async () => {
    createSession.mockResolvedValue({ id: 's-9' })
    const abort = vi.fn()
    startStream.mockImplementation((_req, h) => { setTimeout(() => h.onRunId('run-1'), 0); return { abort, getRunId: () => null } })
    await expect(sendHurtigt(cfg, '  Hvad laver du?  ')).resolves.toBe('s-9')
    expect(createSession).toHaveBeenCalledWith(cfg, 'Hvad laver du?', 'chat')
    expect(startStream.mock.calls[0]?.[0]).toMatchObject({ sessionId: 's-9', message: 'Hvad laver du?', mode: 'chat', model: 'deepseek-flash', providerChoice: 'ollama' })
    // Slipper den — ellers taeller svaret som «set» og bliver aldrig «Faerdig — se svaret».
    expect(abort).toHaveBeenCalled()
  })

  it('en fejl fra stroemmen naar frem til kalderen', async () => {
    createSession.mockResolvedValue({ id: 's-9' })
    startStream.mockImplementation((_req, h) => { setTimeout(() => h.onError({ message: 'HTTP 403' }), 0); return { abort: vi.fn(), getRunId: () => null } })
    await expect(sendHurtigt(cfg, 'x')).rejects.toThrow('HTTP 403')
  })

  it('tom besked sendes ikke', async () => {
    await expect(sendHurtigt(cfg, '   ')).rejects.toThrow()
    expect(createSession).not.toHaveBeenCalled()
  })
})
