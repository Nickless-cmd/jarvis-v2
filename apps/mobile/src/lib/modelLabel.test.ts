import { shortModelLabel } from './modelLabel'

describe('shortModelLabel', () => {
  it('fjerner udbyder-gentagelsen', () => {
    expect(shortModelLabel('deepseek · deepseek-v4-flash')).toBe('v4-flash')
  })

  it('taaler skraastreg-form', () => {
    expect(shortModelLabel('openai · openai/gpt-5')).toBe('gpt-5')
    expect(shortModelLabel('anthropic/claude-opus-5')).toBe('claude-opus-5')
  })

  it('lader et navn uden gentagelse staa', () => {
    expect(shortModelLabel('ollama · qwen3-coder')).toBe('qwen3-coder')
  })

  it('beholder input naar der ikke er noget at skaere', () => {
    expect(shortModelLabel('gpt-5')).toBe('gpt-5')
  })

  it('taaler tomt og udefineret', () => {
    expect(shortModelLabel('')).toBe('')
    expect(shortModelLabel(undefined)).toBe('')
    expect(shortModelLabel(null)).toBe('')
  })
})
