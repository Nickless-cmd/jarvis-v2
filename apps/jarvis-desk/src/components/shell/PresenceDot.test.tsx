import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('green when connected/idle', () => {
    const { container } = render(<PresenceDot status="idle" />)
    expect(container.querySelector('.presence-dot.green')).not.toBeNull()
  })
  it('yellow when working', () => {
    const { container } = render(<PresenceDot status="working" />)
    expect(container.querySelector('.presence-dot.yellow')).not.toBeNull()
  })
  it('red when interrupted or error', () => {
    const { container: c1 } = render(<PresenceDot status="interrupted" />)
    expect(c1.querySelector('.presence-dot.red')).not.toBeNull()
    const { container: c2 } = render(<PresenceDot status="error" />)
    expect(c2.querySelector('.presence-dot.red')).not.toBeNull()
  })
})
