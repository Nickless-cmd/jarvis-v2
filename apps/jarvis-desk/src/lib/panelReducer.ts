import type { InspectorTarget } from './inspectorTargets'

export const MIN_WIDTH = 320
export const MAX_WIDTH_FRACTION = 0.7 // af vinduesbredden — clamps i SplitLayout, ikke her

export interface PanelState {
  open: boolean
  width: number
  target: InspectorTarget | null
  previousTarget: InspectorTarget | null
}

export type PanelAction =
  | { type: 'open-target'; target: InspectorTarget; rememberCurrent?: boolean }
  | { type: 'back' }
  | { type: 'close' }
  | { type: 'toggle' }
  | { type: 'resize'; width: number }

export function initialPanelState(width: number): PanelState {
  return { open: false, width: Math.max(MIN_WIDTH, width), target: null, previousTarget: null }
}

export function panelReducer(state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case 'open-target':
      return {
        ...state,
        open: true,
        target: action.target,
        previousTarget: action.rememberCurrent ? state.target : null,
      }
    case 'back':
      return state.previousTarget
        ? { ...state, open: true, target: state.previousTarget, previousTarget: null }
        : { ...state, open: false, target: null, previousTarget: null }
    case 'close':
      return { ...state, open: false, target: null, previousTarget: null }
    case 'toggle':
      return { ...state, open: !state.open }
    case 'resize':
      return { ...state, width: Math.max(MIN_WIDTH, action.width) }
    default:
      return state
  }
}
