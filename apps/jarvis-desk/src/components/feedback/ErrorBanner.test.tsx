import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorBanner } from './ErrorBanner'

describe('ErrorBanner', () => {
  it('viser besked + luk', () => {
    const onDismiss = vi.fn()
    render(<ErrorBanner message="Kan ikke forbinde" onDismiss={onDismiss} />)
    expect(screen.getByText('Kan ikke forbinde')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('luk'))
    expect(onDismiss).toHaveBeenCalled()
  })

  it('viser ikke "Prøv igen" uden onRetry', () => {
    render(<ErrorBanner message="x" onDismiss={vi.fn()} />)
    expect(screen.queryByText('Prøv igen')).not.toBeInTheDocument()
  })

  it('"Prøv igen" kalder onRetry', () => {
    const onRetry = vi.fn()
    render(<ErrorBanner message="x" onDismiss={vi.fn()} onRetry={onRetry} />)
    fireEvent.click(screen.getByText('Prøv igen'))
    expect(onRetry).toHaveBeenCalled()
  })

  it('severity-klasse + fix-hint vises', () => {
    const { container } = render(
      <ErrorBanner message="Rate-limited" severity="warning" fixHint="Vent lidt" onDismiss={vi.fn()} />,
    )
    expect(container.querySelector('.banner-sev-warning')).toBeInTheDocument()
    expect(screen.getByText('Vent lidt')).toBeInTheDocument()
  })
})
