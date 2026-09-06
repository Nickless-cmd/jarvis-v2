import { voiceStatusCopy } from './voiceUiState'

it('turns voice runtime state into concise mobile copy', () => {
  expect(voiceStatusCopy({ state: 'listening', mode: 'hands-free' }).primary).toBe('Jeg lytter')
  expect(voiceStatusCopy({ state: 'speaking', mode: 'push', canInterrupt: true }).action).toBe('Afbryd')
  expect(voiceStatusCopy({ state: 'idle', mode: 'push' }).hint).toContain('Hold')
})
