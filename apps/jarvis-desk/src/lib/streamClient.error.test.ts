import { describe, it, expect } from 'vitest'
import { StreamError } from './streamClient'

describe('StreamError back-compat + canonical extension', () => {
  it('gammel konstruktion (uden kind/origin) virker uændret', () => {
    const err = new StreamError('network', 'Kunne ikke nå serveren', {
      retryable: true, statusCode: null, context: { url: 'x' },
    })
    expect(err.category).toBe('network')
    expect(err.retryable).toBe(true)
    expect(err.kind).toBeUndefined()
    expect(err.origin).toBe('client')
  })

  it('kind + origin kan sættes additivt', () => {
    const err = new StreamError('server', 'HTTP 500', {
      retryable: true, statusCode: 500, kind: 'server.error', origin: 'stream',
    })
    expect(err.kind).toBe('server.error')
    expect(err.origin).toBe('stream')
  })

  it('canonicalKind() udleder fra category når kind mangler', () => {
    expect(new StreamError('auth', 'x').canonicalKind()).toBe('auth.token_expired')
    expect(new StreamError('rate_limit', 'x').canonicalKind()).toBe('model.rate_limited')
    expect(new StreamError('network', 'x').canonicalKind()).toBe('network.unreachable')
    expect(new StreamError('network', 'x', { kind: 'network.timeout' }).canonicalKind()).toBe('network.timeout')
  })
})
