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

describe('ErrorCard · redning', () => {
  const grund = { error: mk({}), onDismiss: () => {} }

  it('viser kun de redningsknapper der faktisk er givet', () => {
    render(<ErrorCard {...grund} redning={{ onSpoergFoerst: () => {} }} />)
    expect(screen.getByRole('button', { name: /Spørg før ændringer/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Prøv med Pro/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Fortryd/ })).toBeNull()
  })

  it('viser slet ingen når situationen ikke tilbyder noget', () => {
    render(<ErrorCard {...grund} />)
    expect(screen.queryByRole('button', { name: /Fortryd|Pro|Spørg/ })).toBeNull()
  })

  it('kvitterer for en rollback i kortet selv', async () => {
    const onFortryd = vi.fn().mockResolvedValue('Rullet tilbage til abc1234')
    render(<ErrorCard {...grund} redning={{ onFortryd }} />)
    fireEvent.click(screen.getByRole('button', { name: /Fortryd sidste ændringer/ }))
    expect(await screen.findByText(/Rullet tilbage til abc1234/)).toBeTruthy()
  })

  it('siger til når rollback slog fejl i stedet for at tie', async () => {
    const onFortryd = vi.fn().mockRejectedValue(new Error('nej'))
    render(<ErrorCard {...grund} redning={{ onFortryd }} />)
    fireEvent.click(screen.getByRole('button', { name: /Fortryd sidste ændringer/ }))
    expect(await screen.findByText(/Kunne ikke fortryde/)).toBeTruthy()
  })
})
