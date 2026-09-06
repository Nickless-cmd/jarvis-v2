import type { AppStateStatus } from 'react-native'

export interface RuntimePolicyInput {
  appState: AppStateStatus
  connectivity: 'connected' | 'reconnecting' | 'offline'
  activeRun: boolean
  userViewingActiveSession: boolean
  batterySaver: boolean
}

export interface RuntimePolicy {
  liveStream: boolean
  runNotification: boolean
  presenceIntervalMs: number
  activeRunPollMs: number
  preciseLocationAllowed: boolean
}

export function computeRuntimePolicy(input: RuntimePolicyInput): RuntimePolicy {
  const foreground = input.appState === 'active'
  const online = input.connectivity !== 'offline'
  const liveStream =
    foreground &&
    online &&
    input.activeRun &&
    input.userViewingActiveSession &&
    !input.batterySaver

  if (!foreground) {
    return {
      liveStream: false,
      runNotification: input.activeRun,
      presenceIntervalMs: input.activeRun ? 300000 : 600000,
      activeRunPollMs: 0,
      preciseLocationAllowed: false
    }
  }

  if (input.batterySaver) {
    return {
      liveStream: false,
      runNotification: false,
      presenceIntervalMs: 120000,
      activeRunPollMs: input.activeRun ? 5000 : 10000,
      preciseLocationAllowed: false
    }
  }

  return {
    liveStream,
    runNotification: false,
    presenceIntervalMs: input.activeRun ? 30000 : 120000,
    activeRunPollMs: input.activeRun ? 2000 : 10000,
    preciseLocationAllowed: true
  }
}
