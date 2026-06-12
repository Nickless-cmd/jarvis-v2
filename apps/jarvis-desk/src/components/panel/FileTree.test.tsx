import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FileTree } from './FileTree'

vi.mock('../../lib/api', () => ({
  getTree: vi.fn().mockResolvedValue([
    { name: 'services', kind: 'dir' }, { name: 'x.py', kind: 'file' },
  ]),
}))

describe('FileTree', () => {
  it('viser rod-entries og kalder onOpenFile ved fil-klik', async () => {
    const onOpenFile = vi.fn()
    render(<FileTree config={{ apiBaseUrl: 'http://t', authToken: 't' }} kind="container" root="core" onOpenFile={onOpenFile} />)
    expect(await screen.findByText('x.py')).toBeInTheDocument()
    fireEvent.click(screen.getByText('x.py'))
    expect(onOpenFile).toHaveBeenCalledWith('x.py')
  })
})
