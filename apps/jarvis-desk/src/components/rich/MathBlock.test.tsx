import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MathBlock } from './MathBlock'

describe('MathBlock', () => {
  it('renders fallback raw text on invalid latex', async () => {
    render(<MathBlock latex={'\\frac{'} />)
    expect(await screen.findByText(/frac/)).toBeInTheDocument()
  })
})
