import { highlight } from './highlight'

const kinds = (code: string) => highlight(code).map((t) => `${t.kind}:${t.text}`)

describe('highlight', () => {
  it('farver strenge', () => {
    expect(kinds('x = "hej"')).toContain('str:"hej"')
  })

  it('farver kommentarer — også naar de indeholder noegleord', () => {
    const out = highlight('# return const\nx = 1')
    expect(out[0]).toEqual({ text: '# return const', kind: 'com' })
    // 'return' inde i kommentaren maa IKKE vaere blevet et noegleord
    expect(out.filter((t) => t.kind === 'kw')).toHaveLength(0)
  })

  it('lader noegleord inde i en streng vaere', () => {
    const out = highlight('s = "class def"')
    expect(out.some((t) => t.kind === 'kw')).toBe(false)
  })

  it('farver tal og noegleord', () => {
    expect(kinds('const n = 42')).toEqual(
      expect.arrayContaining(['kw:const', 'num:42'])
    )
  })

  it('slaar naboer af samme slags sammen', () => {
    // 'a b c' er tre ord med mellemrum — alt sammen plain, ét token.
    expect(highlight('a b c')).toEqual([{ text: 'a b c', kind: 'plain' }])
  })

  it('bevarer teksten praecis', () => {
    const src = 'def f(x):\n    return x * 2  # dobbelt\n'
    expect(highlight(src).map((t) => t.text).join('')).toBe(src)
  })

  it('taaler tom og underlig indtastning', () => {
    expect(highlight('')).toEqual([])
    expect(highlight('"uafsluttet').map((t) => t.text).join('')).toBe('"uafsluttet')
  })
})
