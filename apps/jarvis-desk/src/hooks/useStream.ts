import { useContext } from 'react'
import { StreamContext, type StreamContextValue } from '../contexts/StreamContext'

export function useStream(): StreamContextValue {
  const ctx = useContext(StreamContext)
  if (!ctx) throw new Error('useStream must be used within StreamProvider')
  return ctx
}
