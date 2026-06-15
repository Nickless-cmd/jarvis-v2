export type AppAction = 'switch_to_code_mode' | 'request_full_access'

export interface AppActionDeps {
  setSurface: (s: 'code') => void
  setPermission: (p: 'trust') => void
  armAutoContinue: (message: string) => void
}

/** Ren oversættelse: app-action → konkrete state-mutationer. Holdes ren så
 *  approve-logikken er unit-testbar uden React. */
export function resolveAppAction(
  action: AppAction,
  deps: AppActionDeps,
  originalMessage: string,
): void {
  if (action === 'switch_to_code_mode') deps.setSurface('code')
  if (action === 'request_full_access') deps.setPermission('trust')
  if (originalMessage) deps.armAutoContinue(originalMessage)
}
