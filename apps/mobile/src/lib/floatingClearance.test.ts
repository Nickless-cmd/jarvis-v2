import { cardSpacerStyle } from './floatingClearance'

describe('cardSpacerStyle', () => {
  // Regressionen 3. sept.: en tom klods aad pladsen mellem traad og komponist,
  // og voksede med tastaturet indtil traaden var vaek fra skaermen.
  it('ingen klods naar der ikke er noget kort', () => {
    expect(cardSpacerStyle(false, 96, 0)).toBeNull()
    expect(cardSpacerStyle(false, 96, 420)).toBeNull()
  })

  it('klods paa komponistens hoejde naar der ER et kort', () => {
    expect(cardSpacerStyle(true, 96, 0)).toEqual({ marginBottom: 96 })
  })

  it('tastaturets loeft laegges til, saa kortet foelger med op', () => {
    expect(cardSpacerStyle(true, 96, 420)).toEqual({ marginBottom: 516 })
  })

  it('negative maal kan ikke give negativ margen', () => {
    expect(cardSpacerStyle(true, -10, -5)).toEqual({ marginBottom: 0 })
  })
})
