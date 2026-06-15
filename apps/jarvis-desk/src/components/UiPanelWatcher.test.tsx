import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { PanelProvider } from '../contexts/PanelContext'
import { usePanel } from '../hooks/usePanel'
import { UiPanelWatcher } from './UiPanelWatcher'

const pending: unknown[] = []
vi.mock('../lib/coworkApi', () => ({
  getUiPanelPending: () => Promise.resolve(pending.splice(0, pending.length)),
  ackUiPanel: () => Promise.resolve(),
}))

let panelRef: ReturnType<typeof usePanel> | null = null
function Probe() { panelRef = usePanel(); return null }
const wrap = (ui: ReactNode) => render(<PanelProvider defaultWidth={400}><Probe />{ui}</PanelProvider>)
const cfg = { apiBaseUrl: 'http://t', authToken: 't' }

describe('UiPanelWatcher', () => {
  beforeEach(() => { panelRef = null; pending.length = 0 })

  it('close-request calls panel.close()', async () => {
    pending.push({ id: 'p1', panel: 'preview', action: 'open', session_id: '', detail: 'x', status: 'pending', created_at: '' })
    wrap(<UiPanelWatcher config={cfg} />)
    await waitFor(() => expect(panelRef?.open).toBe(true))
    pending.push({ id: 'p2', panel: 'preview', action: 'close', session_id: '', detail: '', status: 'pending', created_at: '' })
    // watcheren poller hvert 4000ms → giv close-ticket tid til at blive fanget.
    await waitFor(() => expect(panelRef?.open).toBe(false), { timeout: 6000 })
  })
})
