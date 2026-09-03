import { initials } from './SettingsScreen'

describe('initials', () => {
  it('tager foerste og sidste forbogstav', () => {
    expect(initials('Bjørn Slot')).toBe('BS')
  })

  it('et enkelt navn giver ét bogstav', () => {
    expect(initials('Michelle')).toBe('M')
  })

  it('virker paa en email naar navnet mangler', () => {
    expect(initials('onkeladolf@gmail.com')).toBe('OC')
  })

  // En tom cirkel ser ud som om noget ikke blev indlaest.
  it('tomt navn giver et spoergsmaalstegn, ikke ingenting', () => {
    expect(initials('')).toBe('?')
    expect(initials('   ')).toBe('?')
  })
})
