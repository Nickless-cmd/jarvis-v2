import { render } from '@testing-library/react-native'
import { KantFade, delAlpha } from './KantFade'

describe('delAlpha', () => {
  it('deler en rgba-streng i farve og alpha', () => {
    // Det er alphaen der baerer daekningen. Kommer den med ind i stopColor,
    // ganger SVG den med stop-opacity og kanten bliver for svag.
    expect(delAlpha('rgba(0, 0, 0, 0.72)')).toEqual({ farve: 'rgb(0, 0, 0)', alpha: 0.72 })
  })

  it('giver alpha 1 naar strengen ikke baerer nogen', () => {
    expect(delAlpha('rgb(250, 250, 250)')).toEqual({ farve: 'rgb(250, 250, 250)', alpha: 1 })
  })

  it('lader et ukendt format staa uaendret — hellere en daarlig farve end ingen kant', () => {
    expect(delAlpha('#000000')).toEqual({ farve: '#000000', alpha: 1 })
  })
})

describe('KantFade', () => {
  it('tegner et lag med det navn den fik', async () => {
    const screen = await render(<KantFade retning="ned" navn="topbar" />)
    expect(screen.getByTestId('kantfade-topbar')).toBeTruthy()
  })

  it('navnet gor gradient-id-et unikt — to kanter maa ikke dele', async () => {
    // Gradient-id'er er globale i SVG. Delte de id, ville den ene kant arve
    // den andens farve og stiltiende forsvinde.
    const a = await render(<KantFade retning="ned" navn="topbar" />)
    const b = await render(<KantFade retning="op" navn="komponist" />)
    expect(a.getByTestId('kantfade-topbar')).toBeTruthy()
    expect(b.getByTestId('kantfade-komponist')).toBeTruthy()
  })

  it('forlaenger composer-faden opad og helt ned til bunden af dens boks', async () => {
    const screen = await render(<KantFade retning="op" navn="komponist" over={56} />)
    expect(screen.getByTestId('kantfade-ramme-komponist')).toHaveStyle({ top: -56, bottom: 0 })
    expect(screen.getByTestId('kantfade-komponist')).toHaveProp('height', '100%')
  })
})
