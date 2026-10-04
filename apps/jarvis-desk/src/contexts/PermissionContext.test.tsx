import { describe, it, expect, beforeEach, vi } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'

const getSessionPermission = vi.fn()
const setSessionPermission = vi.fn()
vi.mock('../lib/api', () => ({
  getSessionPermission: (...args: unknown[]) => getSessionPermission(...args),
  setSessionPermission: (...args: unknown[]) => setSessionPermission(...args),
}))
import { PermissionProvider } from './PermissionContext'
import { usePermission } from '../hooks/usePermission'

const wrapper = ({ children }: { children: ReactNode }) => (
  <PermissionProvider>{children}</PermissionProvider>
)

describe('PermissionContext', () => {
  beforeEach(() => { localStorage.clear(); getSessionPermission.mockReset(); setSessionPermission.mockReset() })

  it('scopes a side-panel permission to its target session', async () => {
    const config = { apiBaseUrl: 'http://example', authToken: 'token' }
    getSessionPermission.mockResolvedValue('ask')
    setSessionPermission.mockResolvedValue(undefined)
    const panelWrapper = ({ children }: { children: ReactNode }) => (
      <PermissionProvider config={config} sessionId="target-session">{children}</PermissionProvider>
    )
    const { result } = renderHook(() => usePermission(), { wrapper: panelWrapper })
    await waitFor(() => expect(getSessionPermission).toHaveBeenCalledWith(config, 'target-session'))
    act(() => result.current.setPermission('trust'))
    expect(setSessionPermission).toHaveBeenCalledWith(config, 'target-session', 'trust')
    expect(localStorage.getItem('jarvis-desk:permission:target-session')).toBe('trust')
    expect(localStorage.getItem('jarvis-desk:permission')).toBeNull()
  })

  it('defaults to ask', () => {
    const { result } = renderHook(() => usePermission(), { wrapper })
    expect(result.current.permission).toBe('ask')
  })

  it('setPermission updates and persists', () => {
    const { result } = renderHook(() => usePermission(), { wrapper })
    act(() => result.current.setPermission('trust'))
    expect(result.current.permission).toBe('trust')
    expect(localStorage.getItem('jarvis-desk:permission')).toBe('trust')
  })

  it('initialises from localStorage', () => {
    localStorage.setItem('jarvis-desk:permission', 'trust')
    const { result } = renderHook(() => usePermission(), { wrapper })
    expect(result.current.permission).toBe('trust')
  })
})
