import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const getCheckpoints = vi.fn()
const rollbackCheckpoint = vi.fn()
vi.mock('../lib/coworkApi', () => ({
  getCheckpoints: (...a: unknown[]) => getCheckpoints(...a),
  rollbackCheckpoint: (...a: unknown[]) => rollbackCheckpoint(...a),
}))

import { useRedning } from './useRedning'
import { PermissionProvider } from '../contexts/PermissionContext'
import { PERM_KEY } from '../lib/composerPrefs'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function Prøve(props: Partial<Parameters<typeof useRedning>[0]> = {}) {
  const r = useRedning({
    config: cfg, sessionId: 's1', isOwner: false, aktiv: true,
    model: 'standard', prøvIgenMed: vi.fn(), ...props,
  })
  return (
    <div>
      {r.onStaerkere && <button onClick={r.onStaerkere}>staerkere</button>}
      {r.onFortryd && <button onClick={() => void r.onFortryd!()}>fortryd</button>}
      {r.onSpoergFoerst && <button onClick={r.onSpoergFoerst}>spoerg</button>}
    </div>
  )
}
const vis = (p: Parameters<typeof Prøve>[0] = {}) =>
  render(<PermissionProvider><Prøve {...p} /></PermissionProvider>)

describe('useRedning', () => {
  beforeEach(() => {
    localStorage.clear()
    getCheckpoints.mockReset().mockResolvedValue({ antal: 0, punkter: [] })
    rollbackCheckpoint.mockReset().mockResolvedValue({ status: 'ok', gendannet: 'abc1234' })
  })

  it('tilbyder Pro til en member på standard', async () => {
    vis()
    expect(screen.getByText('staerkere')).toBeTruthy()
  })

  it('tilbyder IKKE Pro til owner — «stærkere» er ikke defineret der', () => {
    vis({ isOwner: true, model: 'deepseek-v4' })
    expect(screen.queryByText('staerkere')).toBeNull()
  })

  it('tilbyder kun fortryd når sessionen faktisk har checkpoints', async () => {
    vis()
    await waitFor(() => expect(getCheckpoints).toHaveBeenCalledWith(cfg, 's1'))
    expect(screen.queryByText('fortryd')).toBeNull()

    getCheckpoints.mockResolvedValue({ antal: 3, punkter: [] })
    vis()
    await waitFor(() => expect(screen.getAllByText('fortryd').length).toBeGreaterThan(0))
  })

  it('slår ikke checkpoints op når der ikke er nogen fejl', async () => {
    vis({ aktiv: false })
    await new Promise((r) => setTimeout(r, 15))
    expect(getCheckpoints).not.toHaveBeenCalled()
  })

  it('tilbyder «spørg først» kun når man står i trust', async () => {
    localStorage.setItem(PERM_KEY, 'trust')
    vis()
    expect(screen.getByText('spoerg')).toBeTruthy()
    fireEvent.click(screen.getByText('spoerg'))
    await waitFor(() => expect(localStorage.getItem(PERM_KEY)).toBe('ask'))
  })

  it('viser ikke «spørg først» når man allerede spørger', () => {
    localStorage.setItem(PERM_KEY, 'ask')
    vis()
    expect(screen.queryByText('spoerg')).toBeNull()
  })

  it('ruller tilbage på den viste session', async () => {
    getCheckpoints.mockResolvedValue({ antal: 1, punkter: [] })
    vis()
    const knap = await screen.findByText('fortryd')
    fireEvent.click(knap)
    await waitFor(() => expect(rollbackCheckpoint).toHaveBeenCalledWith(cfg, 's1'))
  })
})
