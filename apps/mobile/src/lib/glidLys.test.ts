import { lysKurve } from './glidLys'

it('kurvens input STIGER altid — ellers kaster interpolate', () => {
  // Ved korte tekster falder punkter sammen, fordi vinduet bliver meget lille.
  for (const antal of [1, 2, 3, 5, 12, 80]) {
    for (let i = 0; i < antal; i++) {
      const { input } = lysKurve(i, antal)
      for (let k = 1; k < input.length; k++) {
        expect(input[k]!).toBeGreaterThan(input[k - 1]!)
      }
    }
  }
})

it('input og output har samme laengde', () => {
  const { input, output } = lysKurve(3, 10)
  expect(output).toHaveLength(input.length)
})

it('hvert tegn naar fuld lysstyrke ÉN gang', () => {
  const { output } = lysKurve(4, 10)
  expect(output.filter((v) => v === 1)).toHaveLength(1)
})

it('tegn TIDLIGT i teksten lyser FOER tegn sent i teksten', () => {
  // Ellers vandrer lyset ikke - det blinker.
  const toppen = (i: number) => {
    const { input, output } = lysKurve(i, 20)
    return input[output.indexOf(1)]!
  }
  expect(toppen(0)).toBeLessThan(toppen(10))
  expect(toppen(10)).toBeLessThan(toppen(19))
})

it('foerste og sidste tegn bliver STROEGET, ikke blinket', () => {
  // Rejsen er laengere end teksten, saa lyset kan komme helt ind fra venstre
  // og helt ud til hoejre.
  const { input, output } = lysKurve(0, 10)
  expect(input[output.indexOf(1)]!).toBeGreaterThan(0)
  const sidste = lysKurve(9, 10)
  expect(sidste.input[sidste.output.indexOf(1)]!).toBeLessThan(1)
})

it('en tom tekst braekker ikke', () => {
  const { input } = lysKurve(0, 0)
  expect(input.length).toBeGreaterThan(1)
})
