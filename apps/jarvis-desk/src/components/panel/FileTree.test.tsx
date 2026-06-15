import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FileTree } from './FileTree'

const getTreeMock = vi.fn()
vi.mock('../../lib/api', () => ({
  getTree: (...args: unknown[]) => getTreeMock(...args),
}))

const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('FileTree', () => {
  beforeEach(() => {
    getTreeMock.mockReset()
    getTreeMock.mockResolvedValue([{ name: 'services', kind: 'dir' }, { name: 'x.py', kind: 'file' }])
  })

  it('viser rod-entries og kalder onOpenFile ved fil-klik', async () => {
    const onOpenFile = vi.fn()
    render(<FileTree config={cfg} kind="container" root="core" onOpenFile={onOpenFile} />)
    expect(await screen.findByText('x.py')).toBeInTheDocument()
    fireEvent.click(screen.getByText('x.py'))
    expect(onOpenFile).toHaveBeenCalledWith('x.py')
  })

  it('surfacer en fejl i stedet for tavst at vise ingenting', async () => {
    getTreeMock.mockRejectedValue(new Error('403 root uden for jail'))
    render(<FileTree config={cfg} kind="container" root="badroot" onOpenFile={() => {}} />)
    await waitFor(() => expect(screen.getByText(/kunne ikke hente|403/i)).toBeInTheDocument())
  })

  it('viser tydelig tom-tilstand når mappen faktisk er tom', async () => {
    getTreeMock.mockResolvedValue([])
    render(<FileTree config={cfg} kind="container" root="docs" onOpenFile={() => {}} />)
    await waitFor(() => expect(screen.getByText(/tom mappe/i)).toBeInTheDocument())
  })
})
