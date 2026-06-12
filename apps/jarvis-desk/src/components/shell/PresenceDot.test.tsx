import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('idle: ring til stede, drejer ikke', () => {
    const { container } = render(<PresenceDot status="idle" />)
    expect(container.querySelector('.presence-mark.idle')).not.toBeNull()
    expect(container.querySelector('.presence-mark.working')).toBeNull()
  })
  it('working: drejer (working-tone)', () => {
    const { container } = render(<PresenceDot status="working" />)
    expect(container.querySelector('.presence-mark.working')).not.toBeNull()
  })
  it('error/interrupted: error-tone', () => {
    const { container: c1 } = render(<PresenceDot status="interrupted" />)
    expect(c1.querySelector('.presence-mark.error')).not.toBeNull()
    const { container: c2 } = render(<PresenceDot status="error" />)
    expect(c2.querySelector('.presence-mark.error')).not.toBeNull()
  })
})
