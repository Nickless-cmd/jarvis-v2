import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * Er ringen, menuen og code-fladen FAKTISK koblet på?
 *
 * Hver komponent er prøvet for sig, og hver af dem består. Det beviser at de
 * virker når nogen kalder dem — ikke at nogen gør det. Det hul har kostet
 * dyrt nok i denne kodebase til at fortjene en test: `expire_stale`,
 * `record_action`, `prune`, skill-matcheren. Mekanismen fandtes hver gang;
 * kalderen manglede.
 *
 * Testen læser kilden frem for at rendere App, fordi App trækker push,
 * presence, opdateringstjek og tre udbydere med sig. En test der skal mocke
 * halve appen for at måle én prop bliver slukket næste gang den er i vejen.
 */
const kilde = (sti: string) => readFileSync(join(__dirname, sti), 'utf8')

it('App fører kontekst-tallet OP i headerens ring', () => {
  const app = kilde('App.tsx')
  expect(app).toMatch(/kontekst=\{/)
  // ... og tallet skal komme fra ChatScreen, ikke fra ingenting.
  expect(app).toMatch(/onKontekst=\{setKontekst\}/)
})

it('App tegner tre-prik menuen og giver headeren en vej til den', () => {
  const app = kilde('App.tsx')
  expect(app).toMatch(/<TopBarMenu/)
  expect(app).toMatch(/onMereMenu=\{/)
})

it('opdatér virker stadig — den bor bare i menuen nu', () => {
  // Flytningen maa ikke have kappet forbindelsen til syncSignal.
  const app = kilde('App.tsx')
  const menu = app.slice(app.indexOf('<TopBarMenu'))
  expect(menu).toMatch(/onSync=\{[^}]*setSyncSignal/s)
})

it('code-fladen kan baade aabnes og forlades', () => {
  const app = kilde('App.tsx')
  // Panelet fører IND ...
  expect(app).toMatch(/onSkiftFlade=\{setKodeTilstand\}/)
  // ... og headerens tilbage-pil fører UD.
  expect(app).toMatch(/onBack=\{\(\) => setKodeTilstand\(false\)\}/)
})

it('ChatScreen spørger faktisk serveren om kontekst-fyldet', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/getContextUsage\(config, sid\)/)
  // Og den melder det op. Et kald uden en modtager er ingen kobling.
  expect(cs).toMatch(/onKontekst\?\.\(brug\)/)
})

it('ChatScreen giver panelet flade-feltet', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  const panel = cs.slice(cs.indexOf('<SidePanel'))
  expect(panel).toMatch(/kodeTilstand=\{kodeTilstand\}/)
  expect(panel).toMatch(/onSkiftFlade=\{/)
})

it('komprimér-signalet når helt ud til serveren', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/compactSignal/)
  expect(cs).toMatch(/compactNow\(config, sessions\.activeId\)/)
})

it('en ny samtale i code-fladen faar desk\'s eget navn', () => {
  // Der findes ingen markoer paa en code-session - «Kode-session» er
  // udelukkende den titel desk's CodeView giver ved oprettelse. Listen kan
  // derfor ikke filtreres aerligt, men navnet kan matche paa begge enheder.
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/sessions\.create\(config, kodeTilstand \? 'Kode-session' : undefined\)/)
})
