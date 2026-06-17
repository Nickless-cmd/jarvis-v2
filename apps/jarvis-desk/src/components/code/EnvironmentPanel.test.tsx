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

  it('vises under run med branch + ændringer + session-totaler', async () => {
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 3, added: 12, removed: 4 })
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working workingStep="redigerer fil"
      totalTokens={420} totalToolCalls={7}
      tools={[{ name: 'operator_bash', input: { command: 'git status' } }]} />)
    expect(screen.getByText('Miljø')).toBeInTheDocument()
    expect(screen.getByText('redigerer fil')).toBeInTheDocument()
    expect(screen.getByText(/420 tokens/)).toBeInTheDocument()
    expect(screen.getByText(/7 kald/)).toBeInTheDocument()
    // operator_bash formateres som "Terminal: git status" (ikke rå navn)
    expect(screen.getByText('Terminal: git status')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('main')).toBeInTheDocument())
    expect(screen.getByText('+12')).toBeInTheDocument()
  })
})
