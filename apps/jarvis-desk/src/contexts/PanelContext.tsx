import { createContext, useCallback, useMemo, useReducer, type ReactNode } from 'react'
import { panelReducer, initialPanelState } from '../lib/panelReducer'
import { loadPanelWidth, savePanelWidth } from '../lib/panelStore'
import type { Artifact } from '../lib/artifacts'

export interface PanelContextValue {
  open: boolean
  width: number
  artifact: Artifact | null
  open_: (artifact: Artifact) => void
  close: () => void
  toggle: () => void
  resize: (width: number) => void
}

export const PanelContext = createContext<PanelContextValue | null>(null)

export function PanelProvider({ defaultWidth, children }: { defaultWidth: number; children: ReactNode }) {
  const [state, dispatch] = useReducer(panelReducer, loadPanelWidth(defaultWidth), (w) => initialPanelState(w))

  const open_ = useCallback((artifact: Artifact) => {
    dispatch({ type: state.open ? 'replace' : 'open', artifact })
  }, [state.open])
  const close = useCallback(() => dispatch({ type: 'close' }), [])
  const toggle = useCallback(() => dispatch({ type: 'toggle' }), [])
  const resize = useCallback((width: number) => {
    dispatch({ type: 'resize', width })
    savePanelWidth(width)
  }, [])

  const value = useMemo<PanelContextValue>(
    () => ({ open: state.open, width: state.width, artifact: state.artifact, open_, close, toggle, resize }),
    [state.open, state.width, state.artifact, open_, close, toggle, resize],
  )
  return <PanelContext.Provider value={value}>{children}</PanelContext.Provider>
}
