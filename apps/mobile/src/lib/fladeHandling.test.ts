import { beskrivUdfald, normalisérUdfald, udførDeferredTool } from './fladeHandling'

// Samme kontrakt som desk (`apps/jarvis-desk/src/lib/fladeHandling.ts`). Filen
// er kopieret, så testen er også: driver de to fra hinanden, er det her det
// skal gøre ondt — ikke i en telefon et halvt år senere.
describe('normalisérUdfald', () => {
  it('en tavs retur er IKKE succes — den er component_unavailable', () => {
    expect(normalisérUdfald(undefined)).toEqual({
      status: 'failed',
      kode: 'component_unavailable',
      besked: '',
      retryable: false,
    })
  })

  it('et tilfældigt tal fra en gammel provider bliver component_unavailable', () => {
    expect(normalisérUdfald(3).status).toBe('failed')
  })

  it('delivered bevares', () => {
    expect(normalisérUdfald({ status: 'delivered' })).toEqual({ status: 'delivered', retryable: false })
  })

  it('ukendt fejlkode falder tilbage til tool_failed', () => {
    expect(normalisérUdfald({ status: 'failed', kode: 'noget-nyt' })).toEqual({
      status: 'failed',
      kode: 'tool_failed',
      besked: '',
      retryable: false,
    })
  })
})

describe('udførDeferredTool', () => {
  const request = {
    address: {
      accountId: 'owner-1', conversationId: 'chat-1', sourceMessageId: 'msg-1',
      widgetInstanceId: 'widget-1', contentRevision: 0,
    },
    tool: 'weather', arguments: { location: 'Svendborg' },
  }

  it('leverer resultatet tilbage til samme widget med ny revision', async () => {
    const fetcher = jest.fn(async () => new Response(JSON.stringify({
      status: 'delivered', retryable: false, result: { temperature: 12 },
      address: { ...request.address, contentRevision: 1 },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const result = await udførDeferredTool(
      { apiBaseUrl: 'https://api.test', authToken: 'token' }, request, { fetcher },
    )
    expect(result).toMatchObject({ status: 'delivered', result: { temperature: 12 } })
    expect(result.address.contentRevision).toBe(1)
  })

  it('bevarer tool-fejlens retryable-akse', async () => {
    const fetcher = jest.fn(async () => new Response(JSON.stringify({
      status: 'failed', code: 'tool_failed', message: 'netværk', retryable: true,
      address: request.address,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const result = await udførDeferredTool(
      { apiBaseUrl: 'https://api.test', authToken: 'token' }, request, { fetcher },
    )
    expect(result).toMatchObject({ status: 'failed', kode: 'tool_failed', retryable: true })
  })
})

describe('beskrivUdfald', () => {
  it('delivered siger intet — turen fortsætter af sig selv i tråden', () => {
    expect(beskrivUdfald({ status: 'delivered', retryable: false })).toBe('')
  })

  it('hver fejlkode har sin egen sætning', () => {
    const s = [
      beskrivUdfald({ status: 'failed', kode: 'component_unavailable', besked: '', retryable: false }),
      beskrivUdfald({ status: 'failed', kode: 'empty_action', besked: '', retryable: false }),
      beskrivUdfald({ status: 'failed', kode: 'tool_failed', besked: '', retryable: false }),
    ]
    expect(new Set(s).size).toBe(3)
    for (const x of s) expect(x.length).toBeGreaterThan(0)
  })
})
