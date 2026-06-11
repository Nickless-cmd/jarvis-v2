import { useContext } from 'react'
import { SessionContext, type SessionContextValue } from '../contexts/SessionContext'

export function useSessions(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSessions must be used within SessionProvider')
  return ctx
}
