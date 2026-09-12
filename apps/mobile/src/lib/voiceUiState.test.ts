import { voiceStatusCopy } from './voiceUiState'

it('turns voice runtime state into concise mobile copy', () => {
  expect(voiceStatusCopy({ state: 'listening' }).primary).toBe('Jeg lytter')
  expect(voiceStatusCopy({ state: 'speaking', canInterrupt: true }).action).toBe('Afbryd')
  expect(voiceStatusCopy({ state: 'idle' }).hint).toContain('Tal frit')
})
