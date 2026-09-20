import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('keeps Puls visible and stops animation when work finishes', () => {
    const { container, rerender, getByLabelText } = render(<PresenceDot status="working" />)
    expect(getByLabelText('Jarvis arbejder…')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse.is-working')).not.toBeNull()
    rerender(<PresenceDot status="done" />)
    expect(getByLabelText('Jarvis')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse')).not.toBeNull()
    expect(container.querySelector('.is-working')).toBeNull()
  })
  it.each(['error', 'interrupted'])('preserves the interrupted signal for %s', (status) => {
    const { container, getByLabelText } = render(<PresenceDot status={status} />)
    expect(getByLabelText('Afbrudt')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse.is-error')).not.toBeNull()
    expect(container.querySelector('.is-working')).toBeNull()
  })
})
