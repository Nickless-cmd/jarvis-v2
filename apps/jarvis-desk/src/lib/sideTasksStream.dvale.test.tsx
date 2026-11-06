import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSideTasks } from './sideTasksStream'

/**
 * Dvale-fixet (6/11-2026).
 *
 * ## Hvad der blev målt
 *
 * Opgaven `side-92c36d3a0f` blev lukket 06:07:14, og `runtime.side_tasks_changed`
 * fyrede 0,02 s senere — lageret var altså korrekt. Alligevel viste panelet den
 * stadig som ÅBEN kl. 06:09. Årsagen er forbindelsen, ikke dataene: efter dvale
 * er SSE-socket'en halvt-åben, og `reader.read()` hverken fejler eller
 * returnerer. Strømmens løkke står stille, panelet beholder sit gamle snapshot,
 * og der findes ingen klient-side timeout der kan opdage det.
 *
 * ## Hvad testen kræver
 *
 * At `useSideTasks` lytter på `visibilitychange` og — når dokumentet bliver
 * synligt igen — henter listen på ny OG erstatter den døde strøm. Fjernes
 * lytteren, skal denne test fejle. Det er hele pointen: en test der består
 * uanset koden beviser intet.
 */

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

/** En SSE-forbindelse der forbliver ÅBEN — som en rigtig strøm der ikke fejler. */
function aabenSseResponse(opgaver: unknown[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder()
      controller.enqueue(enc.encode(`data: ${JSON.stringify({ type: 'snapshot', opgaver })}\n\n`))
      // Ingen close(): en halvt-åben socket ligner præcis dette — åben, tavs.
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

function antalKald(fetchMock: ReturnType<typeof vi.fn>, del: string): number {
  return fetchMock.mock.calls.filter((c) => String(c[0]).includes(del)).length
}

/**
 * Kun LISTE-kaldet. `/cowork/side-tasks` er en delstreng af
 * `/cowork/side-tasks/stream`, så en naiv `includes` tæller begge — den første
 * version af denne test fik 2 hvor svaret var 1.
 */
function antalListeKald(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((c) => {
    const url = String(c[0])
    return url.includes('/cowork/side-tasks') && !url.includes('/stream')
  }).length
}

describe('sideTasksStream — dvale', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => { vi.unstubAllGlobals() })

  it('henter listen igen og genstarter strømmen når dokumentet bliver synligt', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/stream')) return aabenSseResponse([])
      return new Response(JSON.stringify({ side_tasks: [] }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    })

    renderHook(() => useSideTasks(cfg))

    // Mount: ét fetch til listen + én strøm.
    await waitFor(() => expect(antalKald(fetchMock, '/cowork/side-tasks/stream')).toBe(1))
    const listeVedMount = antalListeKald(fetchMock)
    expect(listeVedMount).toBe(1)

    // Maskinen vågner. Uden lytteren sker der intet — forbindelsen er død,
    // men ser levende ud, så der kommer aldrig et nyt snapshot af sig selv.
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => {
      expect(antalListeKald(fetchMock)).toBe(listeVedMount + 1)
    })
    // Og den døde forbindelse skal være erstattet, ikke genbrugt.
    expect(antalKald(fetchMock, '/cowork/side-tasks/stream')).toBe(2)
  })

  it('gør ingenting når dokumentet bliver skjult', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes('/stream')) return aabenSseResponse([])
      return new Response(JSON.stringify({ side_tasks: [] }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    })

    renderHook(() => useSideTasks(cfg))
    await waitFor(() => expect(antalKald(fetchMock, '/cowork/side-tasks/stream')).toBe(1))

    const foer = fetchMock.mock.calls.length
    const original = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState')
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    try {
      document.dispatchEvent(new Event('visibilitychange'))
      await new Promise((r) => setTimeout(r, 30))
      expect(fetchMock.mock.calls.length).toBe(foer)
    } finally {
      if (original) Object.defineProperty(Document.prototype, 'visibilityState', original)
      else delete (document as unknown as Record<string, unknown>).visibilityState
    }
  })
})
