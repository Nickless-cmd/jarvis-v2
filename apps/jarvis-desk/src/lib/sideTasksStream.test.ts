import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { startSideTasksStream } from './sideTasksStream'

/**
 * Strømmen der erstattede tre pollere (25/10-2026).
 *
 * Testen måler to ting der ikke kan ses i en komponenttest: at et snapshot
 * bliver leveret som en liste, og at en AFVIST forbindelse falder tilbage til
 * ét fetch i stedet for at give op. Den anden er den vigtige — uden den ville
 * et udløbet token gøre panelet permanent tomt, og «tomt» og «kunne ikke
 * hente» er præcis den forveksling panelet blev bygget for at fjerne.
 */

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function sseResponse(frames: string[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder()
      for (const f of frames) controller.enqueue(enc.encode(f))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

describe('sideTasksStream', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => { vi.unstubAllGlobals() })

  it('leverer et snapshot som en liste', async () => {
    const opgaver = [{ side_task_id: 'a', title: 'A', status: 'pending' }]
    fetchMock.mockResolvedValue(
      sseResponse([`data: ${JSON.stringify({ type: 'snapshot', opgaver })}\n\n`]),
    )
    const set: unknown[] = []
    const s = startSideTasksStream(cfg, { onOpgaver: (o) => set.push(o) })
    await vi.waitFor(() => expect(set.length).toBeGreaterThan(0))
    expect(set[0]).toEqual(opgaver)
    s.abort()
  })

  it('ignorerer keepalive-ping og rammer den rigtige rute', async () => {
    fetchMock.mockResolvedValue(
      sseResponse([
        ': ping\n\n',
        `data: ${JSON.stringify({ type: 'snapshot', opgaver: [] })}\n\n`,
      ]),
    )
    const set: unknown[] = []
    const s = startSideTasksStream(cfg, { onOpgaver: (o) => set.push(o) })
    await vi.waitFor(() => expect(set.length).toBe(1))
    expect(fetchMock.mock.calls[0]![0]).toContain('/cowork/side-tasks/stream')
    s.abort()
  })

  it('falder tilbage til ét fetch naar stroemmen afvises', async () => {
    // 403 = ikke ejer. Strømmen kan ikke åbnes, men listen skal stadig kunne
    // vises — ellers ser et manglende token ud som «ingen opgaver».
    const opgaver = [{ side_task_id: 'b', title: 'B', status: 'pending' }]
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/stream')) return new Response('', { status: 403 })
      return new Response(JSON.stringify({ side_tasks: opgaver }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    })
    const set: unknown[] = []
    const fejl: string[] = []
    const s = startSideTasksStream(cfg, {
      onOpgaver: (o) => set.push(o),
      onFejl: (b) => fejl.push(b),
    })
    await vi.waitFor(() => expect(set.length).toBeGreaterThan(0))
    expect(set[0]).toEqual(opgaver)
    expect(fejl.length).toBe(1) // meldt ÉN gang, ikke ved hvert efterfølgende forsøg
    s.abort()
  })

  it('stopper uden at hente videre efter abort', async () => {
    fetchMock.mockResolvedValue(sseResponse([]))
    const set: unknown[] = []
    const s = startSideTasksStream(cfg, { onOpgaver: (o) => set.push(o) })
    s.abort()
    await new Promise((r) => setTimeout(r, 50))
    expect(set).toEqual([])
  })
})
