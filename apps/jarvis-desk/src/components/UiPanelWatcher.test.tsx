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

  it('preview med en filsti i detail → åbner filen (kind=file)', async () => {
    pending.push({ id: 'f1', panel: 'preview', action: 'open', session_id: '', detail: 'docs/spec.md', status: 'pending', created_at: '' })
    wrap(<UiPanelWatcher config={cfg} />)
    await waitFor(() => expect(panelRef?.artifact?.kind).toBe('file'))
    expect(panelRef?.artifact?.filePath).toBe('docs/spec.md')
  })

  it('preview med en note i detail → markdown (ikke fil)', async () => {
    pending.push({ id: 'n1', panel: 'preview', action: 'open', session_id: '', detail: 'her er resultatet', status: 'pending', created_at: '' })
    wrap(<UiPanelWatcher config={cfg} />)
    await waitFor(() => expect(panelRef?.artifact?.kind).toBe('markdown'))
  })

  it('panel=settings → skifter surface til cowork', async () => {
    const surfaces: string[] = []
    pending.push({ id: 'st1', panel: 'settings', action: 'open', session_id: '', detail: '', status: 'pending', created_at: '' })
    wrap(<UiPanelWatcher config={cfg} setSurface={(s) => surfaces.push(s)} />)
    await waitFor(() => expect(surfaces).toContain('cowork'))
  })
})
