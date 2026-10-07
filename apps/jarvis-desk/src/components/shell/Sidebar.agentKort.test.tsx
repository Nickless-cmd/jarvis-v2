import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({ sessions: [], activeId: 'sess-nu', select: vi.fn(), newChat: vi.fn() }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))
vi.mock('../../hooks/useStream', () => ({
  useStream: () => ({ workingSessionId: null }),
  useStreamUdsnit: (vaelg: (v: any) => unknown) => vaelg(({ workingSessionId: null })),
}))
vi.mock('./Klokke', () => ({ Klokke: ({ onAaben }: { onAaben: () => void }) => <button onClick={onAaben}>Klokke</button> }))
// Feedet leverer et agentkort fra en ANDEN session end den brugeren står i («sess-nu»).
vi.mock('./NotifikationsFeed', () => ({
  NotifikationsFeed: ({ onAabnAgent }: { onAabnAgent: (c: unknown) => void }) => (
    <div role="dialog" aria-label="Notifikationer">
      <button onClick={() => onAabnAgent({ origin_session_id: 'sess-oprindelse', agent_id: 'agent-9', title: 'researcher: find X', bucket: 'failed' })}>Agentkort</button>
    </div>
  ),
}))
vi.mock('./NotifikationSessionPanel', () => ({ NotifikationSessionPanel: ({ sessionId }: { sessionId: string }) => <div role="dialog" aria-label="Samtale fra notifikation" data-session={sessionId} /> }))

import { Sidebar } from './Sidebar'

describe('Sidebar — agentkort i notifikationsfeedet', () => {
  it('åbner den OPRINDELIGE session og den rigtige inspector, også fra en anden session', () => {
    const aabn = vi.fn()
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" onOpenAgent={aabn} />)
    fireEvent.click(screen.getByRole('button', { name: 'Klokke' }))
    fireEvent.click(screen.getByRole('button', { name: 'Agentkort' }))
    expect(screen.getByRole('dialog', { name: 'Samtale fra notifikation' })).toHaveAttribute('data-session', 'sess-oprindelse')
    expect(aabn).toHaveBeenCalledWith({ agentId: 'agent-9', role: '', goal: 'researcher: find X', status: 'failed', dispatchToolUseId: '' })
    expect(screen.queryByRole('dialog', { name: 'Notifikationer' })).toBeNull()
  })
})
