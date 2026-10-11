import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * Arbejdslinjen og den kørende runde-linje er smeltet til ÉN linje.
 *
 * Bjørn 11/10-2026: «istedet for to linjer der viser næsten det samme så
 * skulle arbejdslinjen og den igang værende runde linje være en linje».
 *
 * De to linjer blev fodret af SAMME tilstand: arbejdslinjens sætning bygges af
 * `arbejdslinjeTekst(workingStep, workingAction)` — altså den handling der
 * kører lige nu — mens runde-linjen viste rundens etikette og dens diff. To
 * linjer, én aktivitet, to detaljeringsniveauer. Det er dobbelt-visning, ikke
 * to informationer.
 *
 * Linjen, i den rækkefølge Bjørn gav den:
 *
 *     animation → rundens hoved → +/- → turens tid → >
 *
 * mens runden kører, og `</>` i spidsen når den er færdig. Animationen bliver i
 * linjen HELE turen — også i hullet mellem to kald, hvor forklaringen lander
 * (Bjørn 11/10-2026). Kommandoen vises kun mens kaldet kører; når forklaringen
 * lander, ERSTATTER den kommandoen — og står i datid.
 *
 * Testen læser kilden frem for at rendere: `InlineToolGroup` trækker tema,
 * reduceret-bevægelse og diff-arket med sig, og en test der skal mocke det hele
 * for at måle én prop bliver slukket næste gang den er i vejen.
 */
const kilde = (sti: string) => readFileSync(join(__dirname, sti), 'utf8')

it('arbejdslinjen er ikke længere sin EGEN række', () => {
  // Den var en selvstændig række skubbet SIDST i listen. Så længe den findes,
  // står der to linjer om samme arbejde — uanset hvad der står i dem.
  expect(kilde('components/MessageList.tsx')).not.toMatch(/kind: 'arbejdslinje'/)
})

it('listen fører arbejdslinjen og turens ur ind i runden', () => {
  const ml = kilde('components/MessageList.tsx')
  // Kun den SIDSTE runde får dem: et ur på hver runde-linje i tråden ville
  // vise samme tal overalt — også på runder fra helt andre ture.
  expect(ml).toMatch(/arbejdslinje=\{item\.sidsteRunde \? arbejdslinje : null\}/)
  expect(ml).toMatch(/turStart=\{item\.sidsteRunde \? turStart : null\}/)
})

it('skærmen giver turens starttid videre fra streamen — men KUN mens turen kører', () => {
  // Uden dette led bliver `turStart` regnet og gemt uden at nå skærmen.
  //
  // Bjørn 11/10-2026: «tid skal kun vises i den aktuelle linje, ikk i de
  // færdige». Vagtens første udgave bandt uret til `working` — men den prop
  // tænder OGSÅ på serverens efterslæb (`serverBusy`), så mellem
  // `message_stop` og runnets `mark_done` stod uret på en linje hvor alt
  // arbejde var færdigt. Målt 11/10: med én `done`-blok og `working` tegnes
  // BÅDE linjen og uret. `status` er det skarpe signal.
  expect(kilde('screens/ChatScreen.tsx'))
    .toMatch(/turStart=\{stream\.state\.status === 'working' \? stream\.state\.turStart : null\}/)
})

it('mærket i spidsen skifter: puls mens linjen arbejder, </> når den er færdig', () => {
  const g = kilde('components/InlineToolGroup.tsx')
  // Signalet er `arbejder` — IKKE `running`. `running` er sand kun mens et
  // kald udfører, så mærket faldt til `</>` i hullet mellem to kald hvor
  // forklaringen lander (Bjørn 11/10-2026: «animation vises et split sekund
  // og så skiftes den når forklaring kommer»).
  expect(g).toMatch(/arbejder\s*\?\s*<AnimeretPuls/)
  expect(g).toMatch(/const arbejder = streaming && sidste && \(running \|\| !svarBegyndt\)/)
  // `</>` skal BLIVE på de færdige runder — den er rundens mærke, ikke bare
  // et «arbejder nu»-tegn.
  expect(g).toMatch(/<Code2/)
})

it('kommandoen vises mens runden kører — forklaringen når den er færdig', () => {
  // ÉT felt med to tilstande, ikke to felter der skifter. Da
  // `summarizeRound` allerede skriver datid når runden er færdig, er skiftet
  // netop `running ? arbejdslinje : rundens tekst`.
  expect(kilde('components/InlineToolGroup.tsx')).toMatch(/running && arbejdslinje \? arbejdslinje :/)
})

it('token-tallet er ude af linjen — og prop-kæden med det', () => {
  // Bjørn 11/10-2026: «Kan du fjerne token count fra linjen?»
  //
  // Tallet blev ført hele vejen — `ChatScreen` regnede det, `MessageList`
  // gav det videre, `InlineToolGroup` tegnede det som en celle efter uret.
  // Nu maa INGEN af de tre led bære det: en efterladt prop er husets
  // hyppigste fejl — den regnes, sendes og glemmes, og ingen ser den.
  //
  // Testen læser kilden med vilje: den skal ogsaa fange et HALVT tilbageskridt,
  // hvor cellen er væk men prop'en staar tilbage.
  const g = kilde('components/InlineToolGroup.tsx')
  expect(g).not.toMatch(/RullendeTokens/)
  expect(g).not.toMatch(/tokensTal/)
  const ml = kilde('components/MessageList.tsx')
  expect(ml).not.toMatch(/arbejdslinjeTokens/)
  expect(ml).not.toMatch(/tokensTal/)
  expect(kilde('screens/ChatScreen.tsx')).not.toMatch(/arbejdslinjeTokens/)
})

it("turens ur står EFTER diffen og FØR caret'en", () => {
  const g = kilde('components/InlineToolGroup.tsx')
  const iDiff = g.indexOf('styles.tal')
  const iUr = g.indexOf('<RullendeUr')
  const iCaret = g.indexOf('tool-status-caret')
  expect(iDiff).toBeGreaterThan(0)
  expect(iUr).toBeGreaterThan(iDiff)
  expect(iCaret).toBeGreaterThan(iUr)
})

it("caret'en afslutter linjen — også mens runden kører", () => {
  // Før stod den kun på færdige runder (`!running && expandable`). Bjørn vil
  // have den som linjens afslutning.
  expect(kilde('components/InlineToolGroup.tsx')).not.toMatch(/!running && expandable/)
})
