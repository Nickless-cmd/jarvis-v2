import { createContext, useCallback, useMemo, useReducer, type ReactNode } from 'react'
import { panelReducer, initialPanelState } from '../lib/panelReducer'
import { loadPanelWidth, savePanelWidth } from '../lib/panelStore'
import type { Artifact } from '../lib/artifacts'
import type { InspectorTarget } from '../lib/inspectorTargets'

export interface PanelContextValue {
  open: boolean
  width: number
  target: InspectorTarget | null
  previousTarget: InspectorTarget | null
  canGoBack: boolean
  openTarget: (target: InspectorTarget, rememberCurrent?: boolean) => void
  openArtifact: (artifact: Artifact) => void
  open_: (artifact: Artifact) => void
  back: () => void
  close: () => void
  toggle: () => void
  resize: (width: number) => void
}

export const PanelContext = createContext<PanelContextValue | null>(null)

export function PanelProvider({ defaultWidth, children }: { defaultWidth: number; children: ReactNode }) {
  const [state, dispatch] = useReducer(panelReducer, loadPanelWidth(defaultWidth), (w) => initialPanelState(w))

  const openTarget = useCallback((target: InspectorTarget, rememberCurrent = false) => {
    dispatch({ type: 'open-target', target, rememberCurrent })
  }, [])
  const openArtifact = useCallback((artifact: Artifact) => {
    openTarget({ type: 'artifact', artifact })
  }, [openTarget])
  const open_ = openArtifact
  const back = useCallback(() => dispatch({ type: 'back' }), [])
  const close = useCallback(() => dispatch({ type: 'close' }), [])
  const toggle = useCallback(() => dispatch({ type: 'toggle' }), [])
  const resize = useCallback((width: number) => {
    dispatch({ type: 'resize', width })
    savePanelWidth(width)
  }, [])

  const value = useMemo<PanelContextValue>(
    () => ({
      open: state.open,
      width: state.width,
      target: state.target,
      previousTarget: state.previousTarget,
      canGoBack: state.previousTarget !== null,
      openTarget,
      openArtifact,
      open_,
      back,
      close,
      toggle,
      resize,
    }),
    [state.open, state.width, state.target, state.previousTarget, openTarget, openArtifact, open_, back, close, toggle, resize],
  )
  return <PanelContext.Provider value={value}>{children}</PanelContext.Provider>
}
