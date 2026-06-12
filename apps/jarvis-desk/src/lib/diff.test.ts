import { describe, it, expect } from 'vitest'
import { lineDiff } from './diff'

describe('lineDiff', () => {
  it('markerer tilføjede + fjernede linjer', () => {
    expect(lineDiff('a\nb\nc', 'a\nB\nc')).toEqual([
      { type: 'same', text: 'a' },
      { type: 'del', text: 'b' },
      { type: 'add', text: 'B' },
      { type: 'same', text: 'c' },
    ])
  })
  it('tom gammel → alt add', () => {
    expect(lineDiff('', 'x')).toEqual([{ type: 'add', text: 'x' }])
  })
  it('identisk → kun same', () => {
    expect(lineDiff('a\nb', 'a\nb')).toEqual([
      { type: 'same', text: 'a' }, { type: 'same', text: 'b' },
    ])
  })
})
