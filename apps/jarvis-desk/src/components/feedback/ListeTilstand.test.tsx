import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ListeTilstand } from './ListeTilstand'

/**
 * Codex' punkt 2: brugeren skal kunne se forskel på «der er intet endnu»,
 * «det hentes» og «det kunne ikke hentes». Målt i 0.6.64 havde 14 af 18
 * datahentende lister ingen fejl-tilstand — en fejl så præcis ud som en tom
 * kasse.
 *
 * Ordlyden for «henter» og «fejl» kommer fra `SettingsState`, som fandtes i
 * forvejen. Testene her måler derfor ADFÆRDEN — hvilken tilstand der vinder —
 * ikke den præcise formulering, som hører hjemme i SettingsState's egne tests.
 */
describe('ListeTilstand', () => {
  it('siger TOM med kaldernes egne ord når der intet er endnu', () => {
    render(<ListeTilstand antal={0} navn="servere" tomTekst="Ingen servere tilføjet endnu." onIgen={null} />)
    expect(screen.getByText('Ingen servere tilføjet endnu.')).toBeTruthy()
  })

  it('siger HENTER — og ikke «tomt» — mens kaldet er undervejs', () => {
    render(<ListeTilstand antal={0} henter navn="servere" tomTekst="Intet endnu." onIgen={null} />)
    expect(screen.getByText(/Henter/)).toBeTruthy()
    expect(screen.queryByText('Intet endnu.')).toBeNull()
  })

  it('siger FEJL med en vej videre', () => {
    const igen = vi.fn()
    render(<ListeTilstand antal={0} fejl navn="servere" tomTekst="Intet." onIgen={igen} />)
    expect(screen.getByText(/Kunne ikke hente servere/)).toBeTruthy()
    fireEvent.click(screen.getByText('Prøv igen'))
    expect(igen).toHaveBeenCalledOnce()
  })

  it('en fejl må ikke ligne en tom kasse', () => {
    render(<ListeTilstand antal={0} fejl navn="servere" tomTekst="Intet tilføjet endnu." onIgen={null} />)
    expect(screen.queryByText('Intet tilføjet endnu.')).toBeNull()
  })

  it('en fejl skjules IKKE af et gammelt resultat', () => {
    // Ellers ser man forrige hentnings data og tror de er friske.
    render(
      <ListeTilstand antal={3} fejl navn="servere" tomTekst="Intet." onIgen={null}>
        <div>gammel række</div>
      </ListeTilstand>,
    )
    expect(screen.getByText(/Kunne ikke hente/)).toBeTruthy()
    expect(screen.queryByText('gammel række')).toBeNull()
  })

  it('en genhentning blinker ikke «tom» forbi når der allerede er data', () => {
    render(
      <ListeTilstand antal={2} henter navn="servere" tomTekst="Intet." onIgen={null}>
        <div>række</div>
      </ListeTilstand>,
    )
    expect(screen.getByText('række')).toBeTruthy()
    expect(screen.queryByText(/Henter/)).toBeNull()
  })

  it('viser listen når der ER noget og intet gik galt', () => {
    render(
      <ListeTilstand antal={1} navn="servere" tomTekst="Intet." onIgen={null}>
        <div>indhold</div>
      </ListeTilstand>,
    )
    expect(screen.getByText('indhold')).toBeTruthy()
  })

  it('bruger SAMME ordlyd som resten af appen — ikke sin egen', () => {
    // Dubletten var den egentlige fejl: to komponenter med hver sin
    // formulering giver to slags app. Den her uddelegerer til SettingsState.
    render(<ListeTilstand antal={0} fejl navn="fanerne" tomTekst="x" onIgen={null} />)
    expect(screen.getByText('Kunne ikke hente fanerne.')).toBeTruthy()
  })
})
