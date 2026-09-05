import { outgoingChatText } from './chatPrompt'

it('lader almindelige beskeder være uændrede', () => {
  expect(outgoingChatText('Hej', false)).toBe('Hej')
})

it('prefixer research-mode uden at røre provider payload', () => {
  expect(outgoingChatText('Find kilder', true)).toContain('Research mode')
  expect(outgoingChatText('Find kilder', true)).toContain('Find kilder')
})
