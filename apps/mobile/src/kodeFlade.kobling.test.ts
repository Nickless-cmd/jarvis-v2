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
  // Panelets felt fører begge veje, og menuens punkt fører UD. Headerens
  // venstre pil aabner menuen — den er IKKE laengere en vej ud af code.
  expect(app).toMatch(/onSkiftFlade=\{setKodeTilstand\}/)
  expect(app).toMatch(/onTilbageTilChat=\{\(\) => setKodeTilstand\(false\)\}/)
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

it('en ny samtale i code-fladen faar BAADE desk\'s navn og arten', () => {
  // Navnet, saa den ser ens ud paa begge enheder. Arten, saa den ogsaa
  // HAVNER i code-listen - et navn alene er ikke en markoer.
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/sessions\.create\(config, kodeTilstand \? 'Kode-session' : 'Ny samtale', art\)/)
})

it('ALLE fire hentninger spoerger om samme flade', () => {
  // Fire kaldesteder henter sessioner. Glemmer ét af dem arten, ville en
  // omdoebning i code-fladen hente chat-listen tilbage - og samtalen ville
  // se ud som om den forsvandt.
  const cs = kilde('screens/ChatScreen.tsx')
  const kald = cs.match(/sessions\.refresh\(config[^)]*\)/g) || []
  expect(kald.length).toBeGreaterThanOrEqual(4)
  expect(kald.every((k) => k.includes('art'))).toBe(true)
})

it('et fladeskift henter listen OM', () => {
  // Uden det ville man staa i code-fladen med chat-listen foran sig.
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/forrigeArt\.current === art/)
  expect(cs).toMatch(/\}, \[art, config\]\)/)
})

it('ChatScreen henter git-tilstanden — og KUN i code-fladen', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/getGitStatus\(config\)/)
  // Et subprocess-kald pr. opslag skal ikke koere i chat, hvor tallet
  // hverken vises eller er relevant.
  expect(cs).toMatch(/if \(!config \|\| !kodeTilstand\) \{ setGit\(null\); return \}/)
})

it('diff-badgen staar over komponisten og KUN i code', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/<DiffBadge git=\{kodeTilstand \? git : null\} \/>/)
  // ... og faktisk FOER komponisten, ikke et tilfaeldigt sted.
  expect(cs.indexOf('<DiffBadge')).toBeLessThan(cs.indexOf('<Composer'))
})

it('code-headeren faar titel og git meldt OP', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/onKodeKontekst\?\.\(\{ titel: aktivTitel, git \}\)/)
  const app = kilde('App.tsx')
  expect(app).toMatch(/onKodeKontekst=\{setKodeKontekst\}/)
  expect(app).toMatch(/kodeTitel=\{kodeKontekst\.titel\}/)
  expect(app).toMatch(/git=\{kodeKontekst\.git\}/)
})

it('billed-feltet aabner DENNE samtales billeder', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/onOpenBilleder=\{/)
  expect(cs).toMatch(/<BillederScreen\s+sessionId=\{sessions\.activeId \?\? ''\}/)
})

it('fladen gendannes FOER sessionen', () => {
  // Saetter man sessionen foerst, staar man et oejeblik i chat-fladen med en
  // code-samtale og en chat-liste - praecis den modstrid Bjoern beskrev.
  const cs = kilde('screens/ChatScreen.tsx')
  const blok = cs.slice(cs.indexOf('loadLastSession()'), cs.indexOf('loadLastSession()') + 700)
  expect(blok.indexOf('onSkiftFlade?.(plads.kode)')).toBeLessThan(blok.indexOf('sessions.select'))
})

it('samtalens art spoerges KUN naar fladen er uvist', () => {
  // Er fladen gemt, er den brugerens eget valg. Skifter man bevidst til chat
  // med en code-samtale aaben og lukker appen, skal den aabne i chat igen -
  // ikke hoppe tilbage til code.
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/if \(plads\.kode === null\) onSkiftFlade\?\.\(s\.kind === 'code'\)/)
  // ... og en gemt flade saettes uden at spoerge.
  expect(cs).toMatch(/if \(plads\.kode !== null && plads\.kode !== kodeTilstand\) onSkiftFlade\?\.\(plads\.kode\)/)
})

it('fladen gemmes ogsaa naar man skifter UDEN at skifte samtale', () => {
  const cs = kilde('screens/ChatScreen.tsx')
  expect(cs).toMatch(/saveLastSession\(sessions\.activeId, kodeTilstand\)/)
  expect(cs).toMatch(/\}, \[sessions\.activeId, kodeTilstand\]\)/)
})
