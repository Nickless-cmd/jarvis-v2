import { describe, expect, it, vi } from 'vitest'
import { beskrivUdfald, normalisérUdfald, udførDeferredTool } from './fladeHandling'

describe('normalisérUdfald', () => {
  it('en tavs retur er IKKE succes — den er component_unavailable', () => {
    // Den vigtigste regel i filen. En provider der glemmer at svare må ikke
    // se ud som om nogen lyttede; ellers er udfaldet værre end ingen udfald.
    expect(normalisérUdfald(undefined)).toEqual({
      status: 'failed',
      kode: 'component_unavailable',
      besked: '',
      retryable: false,
    })
  })

  it('et tilfældigt tal fra en gammel provider bliver component_unavailable', () => {
    // `set.push(t)` returnerer et tal. En mock der gør det påstår intet om
    // produktionen, og må ikke læses som «delivered».
    expect(normalisérUdfald(3).status).toBe('failed')
  })

  it('delivered bevares', () => {
    expect(normalisérUdfald({ status: 'delivered' })).toEqual({ status: 'delivered', retryable: false })
  })

  it('ukendt fejlkode falder tilbage til tool_failed', () => {
    const u = normalisérUdfald({ status: 'failed', kode: 'noget-nyt' })
    expect(u).toEqual({ status: 'failed', kode: 'tool_failed', besked: '', retryable: false })
  })

  it('en kendt fejlkode bevares med sin besked', () => {
    const u = normalisérUdfald({ status: 'failed', kode: 'empty_action', besked: 'tom' })
    expect(u).toEqual({ status: 'failed', kode: 'empty_action', besked: 'tom', retryable: false })
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
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
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
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      status: 'failed', code: 'tool_failed', message: 'netværk', retryable: true,
      address: request.address,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const result = await udførDeferredTool(
      { apiBaseUrl: 'https://api.test', authToken: 'token' }, request, { fetcher },
    )
    expect(result).toMatchObject({ status: 'failed', kode: 'tool_failed', retryable: true })
  })

  it('venter på approval-kortet og leverer resultatet', async () => {
    const svar = [
      { status: 'approval_required', retryable: false, approvalId: 'approval-1', address: request.address },
      { status: 'delivered', retryable: false, result: { result: '12 grader' }, address: { ...request.address, contentRevision: 1 } },
    ]
    const fetcher = vi.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify(svar.shift()), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }))
    const result = await udførDeferredTool(
      { apiBaseUrl: 'https://api.test', authToken: 'token' }, request,
      { fetcher, wait: async () => undefined },
    )
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(String(fetcher.mock.calls[1]?.[0])).toContain('/status')
    expect(result.status).toBe('delivered')
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
