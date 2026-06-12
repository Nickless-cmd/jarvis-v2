import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CodePanel } from './CodePanel'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([{ name: 'x.py', kind: 'file' }]),
  getFile: vi.fn().mockResolvedValue({ path: 'core/x.py', content: 'print(1)', language: 'python' }),
}))

describe('CodePanel', () => {
  it('åbner en fil i visningen ved klik i træet', async () => {
    render(<CodePanel config={{ apiBaseUrl: 'http://t', authToken: 't' }} kind="container" root="core" />)
    fireEvent.click(await screen.findByText('x.py'))
    expect(await screen.findByText(/print\(1\)/)).toBeInTheDocument()
  })
})
