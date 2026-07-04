import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorCard } from './ErrorCard'
import { parseCanonicalError } from '../../lib/canonicalError'

function mk(overrides: Record<string, unknown>) {
  return parseCanonicalError({
    code: 'x', severity: 'error', message: 'Basisbesked',
    retryable: true, fix_hint: 'Et hint', correlation_id: '', kind: 'tool.execution_failed',
    ...overrides,
  })
}

describe('ErrorCard', () => {
  it('recoverable=retry → "Jeg prøvede igen"', () => {
    render(<ErrorCard error={mk({ recoverable: 'retry' })} onDismiss={vi.fn()} />)
    expect(screen.getByText('Jeg prøvede igen.')).toBeInTheDocument()
  })

  it('recoverable=degraded → nedsat tilstand', () => {
    render(<ErrorCard error={mk({ recoverable: 'degraded' })} onDismiss={vi.fn()} />)
    expect(screen.getByText('Jeg kører videre i nedsat tilstand.')).toBeInTheDocument()
  })

  it('recoverable=user_action → kræver din handling', () => {
    render(<ErrorCard error={mk({ recoverable: 'user_action' })} onDismiss={vi.fn()} />)
    expect(screen.getByText('Det kræver din handling.')).toBeInTheDocument()
  })

  it('viser message + fix_hint', () => {
    render(<ErrorCard error={mk({})} onDismiss={vi.fn()} />)
    expect(screen.getByText('Basisbesked')).toBeInTheDocument()
    expect(screen.getByText('Et hint')).toBeInTheDocument()
  })

  it('"Prøv igen" kun når retryable + onRetry', () => {
    const onRetry = vi.fn()
    const { rerender } = render(<ErrorCard error={mk({ retryable: true })} onDismiss={vi.fn()} onRetry={onRetry} />)
    fireEvent.click(screen.getByText('Prøv igen'))
    expect(onRetry).toHaveBeenCalled()
    rerender(<ErrorCard error={mk({ retryable: false })} onDismiss={vi.fn()} onRetry={onRetry} />)
    expect(screen.queryByText('Prøv igen')).not.toBeInTheDocument()
  })

  it('dismiss kaldes', () => {
    const onDismiss = vi.fn()
    render(<ErrorCard error={mk({})} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByLabelText('luk'))
    expect(onDismiss).toHaveBeenCalled()
  })

  it('kind-familie → dansk titel (self → afbrudt)', () => {
    render(<ErrorCard error={mk({ kind: 'self.cutoff' })} onDismiss={vi.fn()} />)
    expect(screen.getByText('Mit svar blev afbrudt')).toBeInTheDocument()
  })
})
