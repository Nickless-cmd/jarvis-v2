import type { PushData } from './push'

export const OPEN_RUN_ACTION_ID = 'jarvis-open-run'
export const STOP_RUN_ACTION_ID = 'jarvis-stop-run'
export const APPROVE_ACTION_ID = 'jarvis-approve'
export const DENY_ACTION_ID = 'jarvis-deny'

export interface NotificationAction {
  title: string
  pressAction: { id: string }
  input?: { allowFreeFormInput: boolean; placeholder: string }
}

export function notificationActionsFor(data: Pick<PushData, 'kind' | 'run_id' | 'request_id'>): NotificationAction[] {
  if (data.kind === 'run_in_progress') {
    return [
      { title: 'Åbn', pressAction: { id: OPEN_RUN_ACTION_ID } },
      { title: 'Stop', pressAction: { id: STOP_RUN_ACTION_ID } }
    ]
  }
  if (data.kind === 'approval_requested') {
    return [
      { title: 'Godkend', pressAction: { id: APPROVE_ACTION_ID } },
      { title: 'Afvis', pressAction: { id: DENY_ACTION_ID } }
    ]
  }
  return []
}
