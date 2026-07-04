import { describe, it, expect } from 'vitest'
import { parseCanonicalError, isCanonical } from './canonicalError'

describe('parseCanonicalError', () => {
  it('parser en fuld canonical to_client_event payload', () => {
    const err = parseCanonicalError({
      type: 'error', code: 'self.cutoff', severity: 'error',
      message: 'Mit svar blev afbrudt før tid.', retryable: false,
      fix_hint: 'Stil spørgsmålet igen.', correlation_id: 'run-abc123',
      kind: 'self.cutoff', recoverable: 'user_action', scope: 'run',
    })
    expect(err.code).toBe('self.cutoff')
    expect(err.kind).toBe('self.cutoff')
    expect(err.severity).toBe('error')
    expect(err.recoverable).toBe('user_action')
    expect(err.scope).toBe('run')
    expect(err.correlationId).toBe('run-abc123')
    expect(err.origin).toBe('stream')
    expect(isCanonical(err)).toBe(true)
  })

  it('legacy payload uden kind/recoverable/scope → back-compat', () => {
    const err = parseCanonicalError({
      code: 'provider_error', severity: 'error',
      message: 'Min udbyder returnerede en fejl.', retryable: true,
      fix_hint: 'Prøv igen om lidt.', correlation_id: '',
    })
    expect(err.code).toBe('provider_error')
    expect(err.kind).toBeUndefined()
    expect(err.recoverable).toBeUndefined()
    expect(isCanonical(err)).toBe(false)
    expect(err.retryable).toBe(true)
  })

  it('ukendt severity/recoverable/scope → sikre defaults', () => {
    const err = parseCanonicalError({ severity: 'bogus', recoverable: 'nope', scope: 'weird' })
    expect(err.severity).toBe('error')
    expect(err.recoverable).toBeUndefined()
    expect(err.scope).toBeUndefined()
  })

  it('tom/null payload → fallback uden kast', () => {
    const err = parseCanonicalError(null)
    expect(err.code).toBe('ui.unknown')
    expect(err.message).toContain('Noget gik galt')
    expect(err.retryable).toBe(true)
  })

  it('origin kan overrides til client', () => {
    expect(parseCanonicalError({ code: 'x' }, 'client').origin).toBe('client')
  })
})
