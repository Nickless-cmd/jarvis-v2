import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const getSession = vi.fn()
const startStream = vi.fn()
vi.mock('../../lib/api', () => ({
  getSession: (...args: unknown[]) => getSession(...args),
  getSessionPermission: vi.fn().mockResolvedValue('ask'),
  setSessionPermission: vi.fn().mockResolvedValue(undefined),
  approveTool: vi.fn(), denyTool: vi.fn(),
}))
vi.mock('../../lib/streamClient', () => ({ startStream: (...args: unknown[]) => startStream(...args) }))
vi.mock('./Composer', () => ({ Composer: ({ showPermissions, onSend }: {
  showPermissions: boolean
  onSend: (text: string, opts: unknown) => void
}) => <div>
  {showPermissions && <span>Permissions</span>}
  <button onClick={() => onSend('Fortsæt', {
    permission: 'trust', model: 'test-model', providerChoice: 'deepseek',
    thinkingMode: 'think', attachments: [], planMode: false,
  })}>Send test</button>
</div> }))

import { NotifikationSessionPanel } from './NotifikationSessionPanel'

const cfg = { apiBaseUrl: 'http://example', authToken: 'token' }

describe('NotifikationSessionPanel', () => {
  it('shows the target conversation and sends with composer permissions to that session', async () => {
    getSession.mockResolvedValue({ session: { id: 'other', title: 'Anden samtale' }, messages: [], etag: null })
    startStream.mockReturnValue({ abort: vi.fn(), getRunId: () => null })
    render(<NotifikationSessionPanel config={cfg} sessionId="other" isOwner onClose={() => {}} onOpenFull={() => {}} />)
    expect(await screen.findByText('Anden samtale')).toBeInTheDocument()
    expect(screen.getByText('Permissions')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Send test' }))
    await waitFor(() => expect(startStream).toHaveBeenCalled())
    expect(startStream.mock.calls[0]![0]).toEqual(expect.objectContaining({
      sessionId: 'other', message: 'Fortsæt', approvalMode: 'trust',
    }))
  })
})
