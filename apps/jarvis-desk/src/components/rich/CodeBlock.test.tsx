import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeBlock } from './CodeBlock'

describe('CodeBlock', () => {
  it('renders the code text', async () => {
    render(<CodeBlock code={'const x = 1'} lang="js" />)
    expect(await screen.findByText(/const x = 1/)).toBeInTheDocument()
  })
  it('copy button copies raw code', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<CodeBlock code={'line1\nline2'} lang="txt" />)
    await userEvent.click(screen.getByRole('button', { name: /kopiér/i }))
    expect(writeText).toHaveBeenCalledWith('line1\nline2')
  })
})
