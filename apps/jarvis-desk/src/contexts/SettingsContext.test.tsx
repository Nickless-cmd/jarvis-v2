import { describe, it, expect, vi } from 'vitest'
import type { ReactNode } from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { SettingsProvider } from './SettingsContext'
import { useSettings } from '../hooks/useSettings'

vi.mock('../lib/api', () => ({
  whoami: vi.fn().mockResolvedValue({ user_id: 'u1', display_name: 'Bjørn', role: 'owner' }),
}))

describe('SettingsContext', () => {
  it('isConfigured=false when no apiBaseUrl/token', () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <SettingsProvider initialConfig={{ apiBaseUrl: '', authToken: null }}>{children}</SettingsProvider>
    )
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.isConfigured).toBe(false)
  })

  it('loads auth.role via whoami when configured', async () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <SettingsProvider initialConfig={{ apiBaseUrl: 'http://t', authToken: 'tok' }}>{children}</SettingsProvider>
    )
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.isConfigured).toBe(true)
    await waitFor(() => expect(result.current.auth?.role).toBe('owner'))
  })
})
