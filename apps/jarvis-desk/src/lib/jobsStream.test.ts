import { afterEach, describe, expect, it, vi } from 'vitest'
import { startJobsStream } from './jobsStream'

const config = { apiBaseUrl: 'https://jarvis.test/', authToken: 'secret' }

function response(text: string): Response {
  const encoder = new TextEncoder()
  return new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text))
    },
  }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

afterEach(() => vi.unstubAllGlobals())

describe('jobsStream', () => {
  it('sender bearer-token og resume-cursor og leverer eventet', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(
      'id: 8\nevent: job_output\ndata: {"type":"job_output","cursor":8,"job_key":"x","payload":{"chunk":"a"}}\n\n',
    ))
    vi.stubGlobal('fetch', fetchMock)
    const onEvent = vi.fn()
    const control = startJobsStream(config, {
      sessionId: 'chat-7', after: 7, onEvent, onError: vi.fn(),
    })
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(1))
    expect(fetchMock.mock.calls[0]?.[0]).toContain('session_id=chat-7&after=7')
    expect(fetchMock.mock.calls[0]?.[1]?.headers).toEqual({ Authorization: 'Bearer secret' })
    control.abort()
  })

  it('afviser en malformed ramme som protokolfejl', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(
      'event: job_output\ndata: ikke-json\n\n',
    )))
    const onError = vi.fn()
    startJobsStream(config, { onEvent: vi.fn(), onError })
    await vi.waitFor(() => expect(onError).toHaveBeenCalledTimes(1))
    expect(onError.mock.calls[0]?.[0]).toMatchObject({ kind: 'protocol' })
  })
})
