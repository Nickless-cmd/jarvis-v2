import { useContext } from 'react'
import { PanelContext, type PanelContextValue } from '../contexts/PanelContext'

export function usePanel(): PanelContextValue {
  const ctx = useContext(PanelContext)
  if (!ctx) throw new Error('usePanel skal bruges inde i <PanelProvider>')
  return ctx
}
