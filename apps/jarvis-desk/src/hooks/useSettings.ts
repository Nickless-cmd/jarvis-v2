import { useContext } from 'react'
import { SettingsContext, type SettingsContextValue } from '../contexts/SettingsContext'

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider')
  return ctx
}
