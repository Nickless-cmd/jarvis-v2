import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getGitStatus = vi.fn()
vi.mock('../../lib/api', async (orig) => ({ ...(await orig() as object), getGitStatus: (...a: unknown[]) => getGitStatus(...a) }))

import { EnvironmentPanel } from './EnvironmentPanel'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('EnvironmentPanel', () => {
  beforeEach(() => getGitStatus.mockReset())

  it('vises ikke når der ikke køres', () => {
    const { container } = render(<EnvironmentPanel config={cfg} kind="container" root="/r" working={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('vises under run med branch + ændringer + live-step', async () => {
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 3, added: 12, removed: 4 })
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working workingStep="redigerer fil" tokens={42} />)
    expect(screen.getByText('Miljø')).toBeInTheDocument()
    expect(screen.getByText('redigerer fil')).toBeInTheDocument()
    expect(screen.getByText('42 tokens')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('main')).toBeInTheDocument())
    expect(screen.getByText('+12')).toBeInTheDocument()
  })
})
