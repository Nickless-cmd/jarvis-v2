import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HangPrompt } from './HangPrompt'
import { LivenessIndicator } from './LivenessIndicator'

describe('feedback', () => {
  it('LivenessIndicator viser varighed i CC-form («42s», ikke «0:42»)', () => {
    render(<LivenessIndicator status="working" elapsedMs={42000} density="compact" />)
    expect(screen.getByText(/42s/)).toBeInTheDocument()
  })
  it('LivenessIndicator: tænke-tid i CC-form, gennemstreget når tanken er SLUT', () => {
    const { container, rerender } = render(
      <LivenessIndicator status="working" elapsedMs={3000} density="compact" thoughtMs={2000} />,
    )
    expect(container.textContent).toContain('Thought for 2s')
    expect(container.querySelector('.liveness-thought.afsluttet')).toBeNull()
    rerender(
      <LivenessIndicator status="working" elapsedMs={3000} density="compact" thoughtMs={2000} thoughtAfsluttet />,
    )
    expect(container.querySelector('.liveness-thought.afsluttet')).not.toBeNull()
  })
  it('LivenessIndicator: baggrundsjob — ental og flertal', () => {
    const { container, rerender } = render(
      <LivenessIndicator status="working" elapsedMs={1000} density="compact" runningJobs={1} />,
    )
    expect(container.textContent).toContain('1 job kører')
    rerender(<LivenessIndicator status="working" elapsedMs={1000} density="compact" runningJobs={3} />)
    expect(container.textContent).toContain('3 jobs kører')
  })
  it('LivenessIndicator: tokens i kort form, ingen tomme skilletegn', () => {
    const { container } = render(
      <LivenessIndicator status="working" elapsedMs={1000} density="compact" tokens={12800} />,
    )
    expect(container.textContent).toContain('12.8k tokens')
    // Ingen sektioner → ingen ledende separator før verbet.
    const { container: tom } = render(<LivenessIndicator status="working" elapsedMs={0} density="compact" />)
    expect(tom.textContent).not.toContain(' · ')
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
