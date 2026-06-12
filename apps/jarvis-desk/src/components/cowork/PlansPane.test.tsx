import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PlansPane } from './PlansPane'

describe('PlansPane', () => {
  it('viser plan-titel + trin-progress', () => {
    render(<PlansPane plans={[{ id: 'p', title: 'Cowork v1', status: 'active', steps_done: 3, steps_total: 7 }]} />)
    expect(screen.getByText('Cowork v1')).toBeInTheDocument()
    expect(screen.getByText(/3.*7/)).toBeInTheDocument()
  })
  it('tom tilstand', () => {
    render(<PlansPane plans={[]} />)
    expect(screen.getByText(/ingen planer/i)).toBeInTheDocument()
  })
})
