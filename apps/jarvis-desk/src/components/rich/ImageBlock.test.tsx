import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ImageBlock } from './ImageBlock'

describe('ImageBlock', () => {
  it('renders https image', () => {
    render(<ImageBlock src="https://x/i.png" alt="billede" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://x/i.png')
  })
  it('blocks data: src → shows alt placeholder, no img', () => {
    render(<ImageBlock src="data:image/svg+xml,<svg>" alt="ondsindet" />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText(/ondsindet/)).toBeInTheDocument()
  })
})
