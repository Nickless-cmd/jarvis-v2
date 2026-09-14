import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { Composer } from './Composer'

/**
 * Forslag i komponisten — i sin EGEN fil.
 *
 * Testene stod først i `Composer.test.tsx`. Dér fejlede de alle fem på præcis
 * 1001 ms, også den der hverken bruger `config` eller `fetch`. Årsagen er ikke
 * forslagene: en test med identiske props og uden noget af det nye renderer
 * `null` når filen køres i rækkefølge, og normalt når den køres alene.
 *
 * Altså orden-afhængig forurening i den eksisterende fil — en test der føjes
 * til enden af den, måler noget andet end den tror. Det er værd at rydde op i,
 * men det er en anden opgave end den her, og at lade fem røde tests stå som
 * «kendt fejl» ville gøre suiten til støj.
 */

async function aabn(screen: Awaited<ReturnType<typeof render>>) {
  const rest = screen.queryByTestId('composer-rest')
  if (rest) await act(async () => { fireEvent.press(rest) })
  await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
}

// ─────────────────────────────────────────────────────────────────────────
// Forslag i komponisten (14/9-2026)
//
// Hvad der kunne skrives videre, lavet af en LOKAL model. Linjen staar OVER
// feltet og trykkes paa — ghost-tekst inde i et RN-TextInput kraever en
// usynlig kopi ovenpaa, holdt i synk ved hvert tastetryk, altsaa to sandheder
// om hvad der staar.
// ─────────────────────────────────────────────────────────────────────────

const cfg = { apiBaseUrl: 'http://x/', authToken: 't' }

function svarMed(forslag: string) {
  return jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve({ forslag }) } as Response)
  )
}

describe('Composer — forslag', () => {
  // `fetch` saettes til en HARMLOES stub mellem testene — ikke til undefined.
  // Foerste udgave nulstillede den, og et forsinket forslags-kald fra den
  // forrige test ramte saa `undefined is not a function`. Fejlen landede i en
  // promise ingen ventede paa.
  afterEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ forslag: '' }) } as Response)
    ) as unknown as typeof fetch
  })

  it('viser forslaget naar der er skrevet nok', async () => {
    global.fetch = svarMed(' fejl i filen') as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er')
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
  })

  it('et tryk skriver forslaget ind i feltet', async () => {
    global.fetch = svarMed(' fejl i filen') as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    const felt = screen.getByTestId('composer-input')
    fireEvent.changeText(felt, 'kan du lige tjekke om der er')
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    await act(async () => { fireEvent.press(screen.getByTestId('composer-forslag')) })
    expect(screen.getByTestId('composer-input').props.value)
      .toBe('kan du lige tjekke om der er fejl i filen')
  })

  it('UDEN config spoerges der slet ikke', async () => {
    // Komponisten skal virke fuldt ud uden forslag — det er en bekvemmelighed,
    // ikke en funktion man kan miste.
    const f = svarMed(' noget')
    global.fetch = f as unknown as typeof fetch
    const screen = await render(<Composer onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er')
    // Ingen raa sleep: uden config fyrer effekten slet ikke, saa der er intet
    // at vente paa. En sleep ville kun goere testen langsom og skroebelig.
    expect(f).not.toHaveBeenCalled()
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et NYT tastetryk rydder det gamle forslag med det samme', async () => {
    // Ellers ville linjen staa med noget der passer til en saetning der ikke
    // findes mere.
    global.fetch = svarMed(' fejl i filen') as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er')
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    // `changeText` skal skylles igennem foer vaerdien er sat — maalt i det her
    // harness: uden `act` staar `props.value` tom efter BEGGE skriv, ogsaa i en
    // komponist helt uden forslag. Uden den her linje lignede symptomet at
    // rydningen ikke virkede, og jeg naaede at «rette» to ting der ikke fejlede.
    await act(async () => {
      fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er n')
    })
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et tomt forslag viser ingen linje', async () => {
    // Vent paa at KALDET er sket — ikke paa uret. En test der sover, maaler
    // sin egen taalmodighed.
    const f = svarMed('')
    global.fetch = f as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er')
    await waitFor(() => expect(f).toHaveBeenCalled())
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et DEAKTIVERET felt viser ikke et forslag videre', async () => {
    // Et forslag hen over et slukket felt er noget man kan trykke paa uden at
    // kunne gøre noget ved det.
    global.fetch = svarMed(' fejl i filen') as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    fireEvent.changeText(screen.getByTestId('composer-input'), 'kan du lige tjekke om der er')
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    await act(async () => {
      screen.rerender(<Composer config={cfg} disabled onSend={jest.fn()} onStop={jest.fn()} />)
    })
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })
})
