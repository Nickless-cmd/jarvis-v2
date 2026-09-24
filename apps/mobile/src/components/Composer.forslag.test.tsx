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
 * men det er en anden opgave end den her.
 *
 * ── Formen er nu desks (24/9-2026) ──────────────────────────────────────────
 *
 * Før sendte mobilen hans HALVSKREVNE udkast og bad en lokal model gætte
 * resten af sætningen. Nu hentes ÉT forslag når feltet er TOMT, bygget på
 * samtalen — og med sessionen med, så Jarvis' eget forslag (lagt i hans tur)
 * er det der møder brugeren. Bjørn: «det samme skal ske for suggestions i
 * mobilens composer».
 */

async function aabn(screen: Awaited<ReturnType<typeof render>>) {
  const rest = screen.queryByTestId('composer-rest')
  if (rest) await act(async () => { fireEvent.press(rest) })
  await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())
}

const cfg = { apiBaseUrl: 'http://x/', authToken: 't' }

function svarMed(body: Record<string, unknown>) {
  return jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(body) } as Response))
}

describe('Composer — forslag', () => {
  // `fetch` saettes til en HARMLOES stub mellem testene — ikke til undefined.
  // Foerste udgave nulstillede den, og et forsinket forslags-kald fra den
  // forrige test ramte saa `undefined is not a function`.
  afterEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ forslag: '' }) } as Response)
    ) as unknown as typeof fetch
  })

  it('viser forslaget naar feltet er tomt', async () => {
    global.fetch = svarMed({ forslag: 'Skal vi teste den?', forslag_id: 'cj-1' }) as unknown as typeof fetch
    const screen = await render(
      <Composer config={cfg} sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />
    )
    await aabn(screen)
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
  })

  it('et tryk skriver forslagets tekst ind i feltet', async () => {
    global.fetch = svarMed({ forslag: 'Skal vi teste den?', forslag_id: 'cj-1' }) as unknown as typeof fetch
    const screen = await render(
      <Composer config={cfg} sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />
    )
    await aabn(screen)
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    await act(async () => { fireEvent.press(screen.getByTestId('composer-forslag')) })
    expect(screen.getByTestId('composer-input').props.value).toBe('Skal vi teste den?')
  })

  it('UDEN config spoerges der slet ikke', async () => {
    // Komponisten skal virke fuldt ud uden forslag — det er en bekvemmelighed,
    // ikke en funktion man kan miste.
    const f = svarMed({ forslag: ' noget' })
    global.fetch = f as unknown as typeof fetch
    const screen = await render(<Composer sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    expect(f).not.toHaveBeenCalled()
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('UDEN en session spoerges der slet ikke', async () => {
    // Uden session er der intet at bygge på — og Jarvis' eget forslag kan ikke
    // findes. Serveren ville svare tomt, men klienten spørger ikke forgæves.
    const f = svarMed({ forslag: ' noget' })
    global.fetch = f as unknown as typeof fetch
    const screen = await render(<Composer config={cfg} onSend={jest.fn()} onStop={jest.fn()} />)
    await aabn(screen)
    expect(f).not.toHaveBeenCalled()
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et NYT tastetryk rydder det gamle forslag med det samme', async () => {
    // Ellers ville linjen staa med noget der passer til en saetning der ikke
    // findes mere.
    global.fetch = svarMed({ forslag: 'Skal vi teste den?', forslag_id: 'cj-1' }) as unknown as typeof fetch
    const screen = await render(
      <Composer config={cfg} sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />
    )
    await aabn(screen)
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    // `changeText` skal skylles igennem foer vaerdien er sat — maalt i det her
    // harness: uden `act` staar `props.value` tom efter BEGGE skriv.
    await act(async () => {
      fireEvent.changeText(screen.getByTestId('composer-input'), 'nej jeg vil')
    })
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et tomt forslag viser ingen linje', async () => {
    // Vent paa at KALDET er sket — ikke paa uret. En test der sover, maaler
    // sin egen taalmodighed.
    const f = svarMed({ forslag: '' })
    global.fetch = f as unknown as typeof fetch
    const screen = await render(
      <Composer config={cfg} sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />
    )
    await aabn(screen)
    await waitFor(() => expect(f).toHaveBeenCalled())
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })

  it('et DEAKTIVERET felt viser ikke et forslag videre', async () => {
    // Et forslag hen over et slukket felt er noget man kan trykke paa uden at
    // kunne gøre noget ved det.
    global.fetch = svarMed({ forslag: 'Skal vi teste den?', forslag_id: 'cj-1' }) as unknown as typeof fetch
    const screen = await render(
      <Composer config={cfg} sessionId="s1" onSend={jest.fn()} onStop={jest.fn()} />
    )
    await aabn(screen)
    await waitFor(() => expect(screen.queryByTestId('composer-forslag')).toBeTruthy())
    await act(async () => {
      screen.rerender(
        <Composer config={cfg} sessionId="s1" disabled onSend={jest.fn()} onStop={jest.fn()} />
      )
    })
    expect(screen.queryByTestId('composer-forslag')).toBeNull()
  })
})
