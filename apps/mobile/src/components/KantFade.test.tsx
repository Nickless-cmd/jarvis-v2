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

  /**
   * UDFOLDET komponist: faden begynder ved kortets OVERKANT, ikke over den,
   * og den er en GRADIENT hele vejen — ikke en flade.
   *
   * Bjoern 28/9-2026: «fade skal ikke vises over composer i udfoldet
   * tilstand.. den skal starte under composers oeverste linje og saa er den
   * helt sort lige nu.. det skal vaere lige som i toppen». Den var strakt
   * 20 dp op over kortet, og under gradienten laa en massiv `bg0`-flade.
   */
  it('udfoldet: begynder ved overkanten og er en gradient, ikke en flade', async () => {
    const screen = await render(<KantFade retning="op" navn="komponist" over={0} under={32} />)
    const ramme = screen.getByTestId('kantfade-ramme-komponist')
    expect(ramme).toHaveStyle({ top: 0, bottom: -32 })
    // Ingen native flade — det var den der gjorde omraadet helt sort.
    expect(screen.queryByTestId('kantfade-bund-komponist')).toBeNull()
    // Og gradienten fylder hele boksen, saa den toner hele vejen ned.
    expect(screen.getByTestId('kantfade-komponist')).toHaveProp('height', '100%')
  })

  it('under-daekningen gaelder ogsaa uden straek — gestus-zonen maa ikke tabes', async () => {
    const screen = await render(<KantFade retning="op" navn="k2" under={32} />)
    expect(screen.getByTestId('kantfade-ramme-k2')).toHaveStyle({ bottom: -32 })
  })

  it('daekker omraadet under en udvidet composer med en rigtig flade', async () => {
    const screen = await render(<KantFade retning="op" navn="komponist" over={20} opaqueBelow under={32} />)
    expect(screen.getByTestId('kantfade-ramme-komponist')).toHaveStyle({ top: -20, bottom: -32 })
    expect(screen.getByTestId('kantfade-komponist')).toHaveProp('height', 20)
    expect(screen.getByTestId('kantfade-bund-komponist')).toHaveStyle({ top: 20, bottom: 0, backgroundColor: '#000000' })
  })
})
