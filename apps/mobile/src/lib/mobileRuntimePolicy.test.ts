import { computeRuntimePolicy } from './mobileRuntimePolicy'

describe('computeRuntimePolicy', () => {
  it('streams live only while foreground and active chat is visible', () => {
    expect(computeRuntimePolicy({
      appState: 'active',
      connectivity: 'connected',
      activeRun: true,
      userViewingActiveSession: true,
      batterySaver: false
    })).toMatchObject({
      liveStream: true,
      runNotification: false,
      presenceIntervalMs: 30000,
      activeRunPollMs: 2000
    })
  })

  it('lets the server own the run when the app backgrounds', () => {
    expect(computeRuntimePolicy({
      appState: 'background',
      connectivity: 'connected',
      activeRun: true,
      userViewingActiveSession: false,
      batterySaver: false
    })).toMatchObject({
      liveStream: false,
      runNotification: true,
      presenceIntervalMs: 300000,
      activeRunPollMs: 0
    })
  })

  it('uses the lowest-power behavior when battery saver is on', () => {
    expect(computeRuntimePolicy({
      appState: 'active',
      connectivity: 'connected',
      activeRun: false,
      userViewingActiveSession: false,
      batterySaver: true
    })).toMatchObject({
      liveStream: false,
      runNotification: false,
      presenceIntervalMs: 120000,
      activeRunPollMs: 10000,
      preciseLocationAllowed: false
    })
  })
})
