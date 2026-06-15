import { describe, it, expect, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, act } from '@testing-library/react'
import { PermissionProvider } from './PermissionContext'
import { usePermission } from '../hooks/usePermission'

const wrapper = ({ children }: { children: ReactNode }) => (
  <PermissionProvider>{children}</PermissionProvider>
)

describe('PermissionContext', () => {
  beforeEach(() => localStorage.clear())

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
