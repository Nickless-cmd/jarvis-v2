import { beforeAll, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

const select = vi.fn()

vi.mock('../../lib/api', () => ({ getActiveRuns: vi.fn(() => new Promise(() => {})) }))
vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: [{ id: 'michelle-1', title: 'Michelles samtale', updated_at: 'x', kind: 'chat' }],
    activeId: null,
    select,
    newChat: vi.fn(),
    rename: vi.fn(),
    remove: vi.fn(),
    setPinned: vi.fn(),
    setArchived: vi.fn(),
    setWorkspace: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: null, auth: { role: 'member' } }),
}))
vi.mock('../../hooks/useStream', () => ({
  useStreamUdsnit: (pick: (value: { workingSessionId: null }) => unknown) =>
    pick({ workingSessionId: null }),
}))

import { Sidebar } from './Sidebar'

beforeAll(() => {
  class TestPointerEvent extends MouseEvent {
    pointerType: string
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init)
      this.pointerType = init.pointerType ?? 'mouse'
    }
  }
  vi.stubGlobal('PointerEvent', TestPointerEvent)
})

describe('sessions paa touchskaerm', () => {
  it('aabner samtalen paa det foerste touch-slip', () => {
    select.mockClear()
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Michelle" />)
    const row = screen.getByRole('button', { name: /Michelles samtale/i })

    fireEvent.pointerDown(row, { pointerType: 'touch', clientX: 20, clientY: 20 })
    fireEvent.pointerUp(row, { pointerType: 'touch', clientX: 20, clientY: 20 })
    // Safari sender normalt også et efterfølgende syntetisk click.
    fireEvent.click(row)

    expect(select).toHaveBeenCalledOnce()
    expect(select).toHaveBeenCalledWith('michelle-1')
  })

  it('aabner ikke en samtale naar fingeren ruller listen', () => {
    select.mockClear()
    render(<Sidebar surface="chat" onSurface={() => {}} userName="Michelle" />)
    const row = screen.getByRole('button', { name: /Michelles samtale/i })

    fireEvent.pointerDown(row, { pointerType: 'touch', clientX: 20, clientY: 20 })
    fireEvent.pointerMove(row, { pointerType: 'touch', clientX: 20, clientY: 50 })
    fireEvent.pointerUp(row, { pointerType: 'touch', clientX: 20, clientY: 50 })

    expect(select).not.toHaveBeenCalled()
  })
})
