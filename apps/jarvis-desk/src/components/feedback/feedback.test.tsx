import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HangPrompt } from './HangPrompt'
import { LivenessIndicator } from './LivenessIndicator'

describe('feedback', () => {
  it('LivenessIndicator shows elapsed time when working', () => {
    render(<LivenessIndicator status="working" elapsedMs={42000} density="compact" />)
    expect(screen.getByText(/0:42/)).toBeInTheDocument()
  })
  it('LivenessIndicator: altid synlig — "klar" når idle, working-step når aktiv', () => {
    const { container, rerender } = render(<LivenessIndicator status="idle" elapsedMs={0} density="compact" />)
    expect(container.querySelector('.liveness.is-idle')).not.toBeNull()
    expect(container.textContent).toContain('klar')
    rerender(<LivenessIndicator status="working" elapsedMs={3000} density="compact" workingStep="tænker" />)
    expect(container.querySelector('.liveness.is-working')).not.toBeNull()
    expect(container.textContent).toContain('tænker')
  })
  it('HangPrompt fires onResume and onAbort', async () => {
    const onResume = vi.fn(), onAbort = vi.fn()
    render(<HangPrompt onResume={onResume} onAbort={onAbort} />)
    await userEvent.click(screen.getByRole('button', { name: /genoptag/i }))
    expect(onResume).toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /afbryd/i }))
    expect(onAbort).toHaveBeenCalled()
  })
})
