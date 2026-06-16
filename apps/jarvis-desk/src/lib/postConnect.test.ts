import { describe, it, expect, beforeEach } from 'vitest'
import { setPendingHint, takePendingHint } from './postConnect'

describe('postConnect-hint', () => {
  beforeEach(() => localStorage.clear())

  it('gemmer og henter engangs-hint', () => {
    setPendingHint('Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
    expect(takePendingHint()).toBe('Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
    expect(takePendingHint()).toBeNull() // forbrugt
  })

  it('ignorerer tomt/blankt hint', () => {
    setPendingHint('')
    setPendingHint('   ')
    setPendingHint(null)
    expect(takePendingHint()).toBeNull()
  })
})
