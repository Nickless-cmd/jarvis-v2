import type { Artifact } from './artifacts'

export const MIN_WIDTH = 320
export const MAX_WIDTH_FRACTION = 0.7 // af vinduesbredden — clamps i SplitLayout, ikke her

export interface PanelState {
  open: boolean
  width: number
  artifact: Artifact | null
}

export type PanelAction =
  | { type: 'open'; artifact: Artifact }
  | { type: 'replace'; artifact: Artifact }
  | { type: 'close' }
  | { type: 'toggle' }
  | { type: 'resize'; width: number }

export function initialPanelState(width: number): PanelState {
  return { open: false, width: Math.max(MIN_WIDTH, width), artifact: null }
}

export function panelReducer(state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case 'open':
    case 'replace':
      return { ...state, open: true, artifact: action.artifact }
    case 'close':
      return { ...state, open: false }
    case 'toggle':
      return { ...state, open: !state.open }
    case 'resize':
      return { ...state, width: Math.max(MIN_WIDTH, action.width) }
    default:
      return state
  }
}
