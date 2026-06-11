import { describe, it, expect, vi } from 'vitest'
import { startStream } from './streamClient'

function sseResponse(chunks: string[]): Response {
  const body = new ReadableStream({
    start(controller) {
      const enc = new TextEncoder()
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

describe('startStream R1-R3', () => {
  it('calls onRunId with message_start id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"visible-42","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    const runIds: string[] = []
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onRunId: (id) => runIds.push(id), onComplete: () => resolve() },
      )
    })
    expect(runIds).toEqual(['visible-42'])
  })

  it('message_stop → onComplete og IKKE onInterrupted (ingen falsk genoptag)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n',
      'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"ok"}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    let completed = false
    let interrupted = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => { completed = true; resolve() }, onInterrupted: () => { interrupted = true; resolve() } },
      )
    })
    expect(completed).toBe(true)
    expect(interrupted).toBe(false)
  })

  it('does NOT auto-reconnect (re-POST) on broken stream when autoReconnect=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"r","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      // stream lukker uden message_stop → interrupted
    ]))
    vi.stubGlobal('fetch', fetchMock)
    let interrupted = false
    await new Promise<void>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onInterrupted: () => { interrupted = true; resolve() }, onError: () => resolve() },
      )
    })
    expect(interrupted).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(1) // ingen re-POST
  })

  it('returns an abort handle with getRunId', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(sseResponse([
      'event: message_start\ndata: {"type":"message_start","message":{"id":"visible-7","model":"m","provider":"p","lane":"l","session_id":"s","usage":{"input_tokens":0,"output_tokens":0}}}\n\n',
      'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ])))
    const handle = await new Promise<{ abort: () => void; getRunId: () => string | null }>((resolve) => {
      const h = startStream(
        { apiBaseUrl: 'http://t', authToken: null, sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onComplete: () => resolve(h) },
      )
    })
    expect(typeof handle.abort).toBe('function')
    expect(handle.getRunId()).toBe('visible-7')
  })
})
