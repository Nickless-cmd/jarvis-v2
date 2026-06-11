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
  it('LivenessIndicator renders nothing when not working', () => {
    const { container } = render(<LivenessIndicator status="idle" elapsedMs={0} density="compact" />)
    expect(container.firstChild).toBeNull()
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
