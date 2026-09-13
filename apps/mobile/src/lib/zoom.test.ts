import { begraensForskydning, begraensSkala, fingerAfstand, MAKS_SKALA } from './zoom'

describe('fingerAfstand', () => {
  it('maaler afstanden mellem to fingre', () => {
    // 3-4-5: vandret 3, lodret 4.
    expect(fingerAfstand([
      { pageX: 0, pageY: 0 },
      { pageX: 3, pageY: 4 },
    ])).toBe(5)
  })

  it('svarer 0 naar der ikke ER to fingre', () => {
    // Et knib der begynder eller slutter midt i en bevægelse giver en liste der
    // skrumper. Der findes ingen afstand at maale — og det er svaret, ikke en fejl.
    expect(fingerAfstand([])).toBe(0)
    expect(fingerAfstand([{ pageX: 1, pageY: 1 }])).toBe(0)
  })
})

describe('begraensSkala', () => {
  it('holder skalaen mellem 1 og loftet', () => {
    expect(begraensSkala(0.2)).toBe(1)
    expect(begraensSkala(2.5)).toBe(2.5)
    expect(begraensSkala(99)).toBe(MAKS_SKALA)
  })

  it('falder tilbage til 1 naar forholdet er 0/0', () => {
    // To fingre der staar stille paa samme punkt giver 0/0. Uden dette ville
    // NaN forplante sig gennem transformen og billedet forsvinde.
    expect(begraensSkala(NaN)).toBe(1)
    expect(begraensSkala(Infinity)).toBe(MAKS_SKALA)
  })
})

describe('begraensForskydning', () => {
  const ramme = { bredde: 400, hoejde: 200 }

  it('der er INTET at panorere i naar billedet ikke er zoomet', () => {
    expect(begraensForskydning({ x: 50, y: 50 }, 1, ramme)).toEqual({ x: 0, y: 0 })
  })

  it('tillader praecis saa meget som billedet rager ud over rammen', () => {
    // Skala 2: billedet er dobbelt saa bredt, altsaa 200 punkt til hver side.
    expect(begraensForskydning({ x: 999, y: 999 }, 2, ramme)).toEqual({ x: 200, y: 100 })
    expect(begraensForskydning({ x: -999, y: -999 }, 2, ramme)).toEqual({ x: -200, y: -100 })
  })

  it('lader en lovlig forskydning staa urørt', () => {
    expect(begraensForskydning({ x: 30, y: -20 }, 2, ramme)).toEqual({ x: 30, y: -20 })
  })

  it('taaler en ramme der endnu ikke er maalt', () => {
    // onLayout er ikke fyrret endnu naar det foerste knib kommer.
    expect(begraensForskydning({ x: 10, y: 10 }, 3, { bredde: 0, hoejde: 0 }))
      .toEqual({ x: 0, y: 0 })
  })
})
