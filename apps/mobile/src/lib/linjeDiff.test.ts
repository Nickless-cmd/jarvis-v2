import { linjeDiff, MAKS } from './linjeDiff'

it('en ændret linje midt i: fælles omkring, - og + i midten', () => {
  expect(linjeDiff('a\nb\nc', 'a\nB\nc')).toEqual([
    { slags: ' ', tekst: 'a' }, { slags: '-', tekst: 'b' }, { slags: '+', tekst: 'B' }, { slags: ' ', tekst: 'c' },
  ])
})
it('en ny fil (intet gammelt) er kun tilføjelser', () => {
  expect(linjeDiff('', 'x\ny').map((l) => l.slags)).toEqual(['+', '+'])
})
it('en sletning er kun fjernelser', () => {
  expect(linjeDiff('x\ny', '').map((l) => l.slags)).toEqual(['-', '-'])
})
it('store tekster regnes ikke kvadratisk — alt gammelt ud, alt nyt ind', () => {
  const stor = Array.from({ length: MAKS + 1 }, (_, k) => `l${k}`).join('\n')
  const ud = linjeDiff(stor, 'kort')
  expect(ud.filter((l) => l.slags === '-')).toHaveLength(MAKS + 1)
  expect(ud[ud.length - 1]).toEqual({ slags: '+', tekst: 'kort' })
})
