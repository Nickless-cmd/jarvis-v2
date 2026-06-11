import { describe, it, expect } from 'vitest'
import { stringToBlocks } from './normalizeMessage'

describe('stringToBlocks', () => {
  it('wraps a markdown string in one text block', () => {
    expect(stringToBlocks('**hej**')).toEqual([{ type: 'text', text: '**hej**' }])
  })
  it('empty string → empty array', () => {
    expect(stringToBlocks('')).toEqual([])
  })
})
