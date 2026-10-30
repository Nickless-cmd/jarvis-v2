/**
 * MÅLING, ikke en vagt: hvilke argumenter sender de to flader til `TurHoved` —
 * og hvor er de uenige?
 *
 * Bjørn 30/10-2026: «Sammenlign alle TurHoved-argumenter fra begge flader».
 * Baggrunden er at ÉN divergens (`koerer`) levede utestet i uger, indtil den
 * blev fundet ved en tilfældig gennemlæsning. Spørgsmålet er om der er flere.
 *
 * ## Kontrakten har ni argumenter
 *
 * `tekst` · `aaben` · `onToggle` · `koerer` · `sekunder` · `meta` ·
 * `skillelinje` · `foldbar` · `knapRef`
 *
 * ## Hvad målingen viser
 *
 * Fire af dem er reelt forskellige, og de er IKKE alle fejl:
 *
 * 1. `tekst` — chat: `model.hovedTekst` («Arbejder»/«Arbejdet»/«Tænker»).
 *    code: `turFortalt(...)` («Læste 3 filer · 42s»). TO SPROG, ikke en fejl:
 *    chat har ingen værktøjsliste at fortælle om, code har.
 * 2. `sekunder` — chat: `useTurSekunder(...) ?? varighedSekunder` (altid sat).
 *    code: `!streaming ? turSekunder : null` (kun når turen er ovre).
 *    Chat viser uret mens den kører, code gør ikke. Reelt forskelligt.
 * 3. `skillelinje` — chat: bar prop (altid sand). code: `visSkillelinje`
 *    (sand når svaret er begyndt). **AFGJORT 30/10-2026: forskellen BLIVER.**
 *    Bjørn valgte «behold som nu — stregen glider ind ved turstart og bliver».
 *    `turhoved.css` er allerede bygget til netop det (`animation … both`,
 *    så `from` er den faktiske starttilstand uanset hvornår attributten
 *    sættes), og hans ord fra 22/10 står i CSS-kommentaren: «det burde komme
 *    fra starten og blive». Chat mode har ingen svar-lås at vente på, så
 *    code-modens gate ville fjerne stregen i præcis den fase hvor hovedet
 *    står og siger «Arbejder».
 *
 *    ⚠️ UMÅLT sidefund: fordi `data-skillelinje` er sand fra første render,
 *    fyrer `@keyframes` også ved MOUNT af historikken — et reload animerer
 *    alle persisterede tures streger ind samtidig. Det er ikke målt i en
 *    browser, og en gate ville ikke løse det (historik har tekst, så
 *    `harSynligTekst` er sand). Den rigtige rettelse ville være at binde
 *    animationen til den LEVENDE tur, ikke til mount.
 * 4. `knapRef` — kun code sender den (`useFoldPosition` bruger den til at
 *    holde foldelinjen på skærmen). Chat har ingen scroll-anker.
 *
 * `aaben`, `onToggle`, `koerer`, `foldbar` og `meta` er ens i form (meta er
 * betinget begge steder, men af samme grund: kun når der er tokens).
 *
 * ## Hvorfor testen er en MÅLING
 *
 * Den låser ikke adfærden. Den dokumenterer hvad de to flader gør NU, så en
 * fremtidig ændring kan se om den flyttede en forskel — og så en beslutning
 * om at ensrette dem kan træffes på målte tal i stedet for på hukommelse.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const RICH = resolve(__dirname)

function kilde(fil: string): string {
  return readFileSync(resolve(RICH, fil), 'utf8')
}

/** Træk argument-blokken ud af det FØRSTE `<TurHoved` i filen.
 *
 *  FÆLDE (målt 30/10-2026): den første `/>` i blokken er IKKE elementets
 *  afslutning — `meta` indeholder `<RullendeTokens … />`, så et naivt
 *  `indexOf('/>')` klipper blokken midt i `meta` og gør alt derefter
 *  usynligt. Vi tæller derfor klammer: elementet slutter ved den `/>` der
 *  står på klamme-niveau 0. */
function argumenter(fil: string): Map<string, string> {
  const tekst = kilde(fil)
  const start = tekst.indexOf('<TurHoved')
  expect(start, `${fil} kalder ikke TurHoved`).toBeGreaterThan(-1)

  let dybde = 0
  let slut = -1
  for (let i = start; i < tekst.length - 1; i++) {
    const c = tekst[i]
    if (c === '{') dybde++
    else if (c === '}') dybde--
    else if (c === '/' && tekst[i + 1] === '>' && dybde === 0) {
      slut = i
      break
    }
  }
  expect(slut, `${fil}: fandt ikke TurHoved-elementets afslutning`).toBeGreaterThan(-1)
  const blok = tekst.slice(start, slut)

  const ud = new Map<string, string>()
  // Hvert argument står som `navn={...}` eller `navn` (bar prop). Vi tager
  // kun topniveau: en linje der starter med whitespace og et navn.
  //
  // FÆLDE (målt 30/10-2026): `onToggle` har en flerlinjet arrow-body, så
  // klamme-tællingen ikke stopper ved elementets slutning — `const` og `if`
  // fra dens body blev læst som argumenter. Vi accepterer derfor KUN navne
  // fra kontrakten; alt andet er indhold, ikke props.
  const KONTRAKT = new Set([
    'tekst', 'aaben', 'onToggle', 'koerer', 'sekunder', 'meta',
    'skillelinje', 'foldbar', 'knapRef',
  ])
  for (const linje of blok.split('\n')) {
    const m = /^\s{2,}([a-zA-Z][a-zA-Z0-9]*)(=\{|\s|$)/.exec(linje)
    const navn = m?.[1]
    if (!navn) continue
    if (!KONTRAKT.has(navn)) continue
    ud.set(navn, linje.trim())
  }
  return ud
}

describe('TurHoved-argumenter — de to flader sammenlignet', () => {
  const chat = argumenter('ChatFlowPresentation.tsx')
  const code = argumenter('RaekkeTranskript.tsx')

  it('begge flader sender de samme ni argumenter fra kontrakten', () => {
    const kontrakt = [
      'tekst', 'aaben', 'onToggle', 'koerer', 'sekunder', 'meta',
      'skillelinje', 'foldbar', 'knapRef',
    ]
    const chatNavne = [...chat.keys()].sort()
    const codeNavne = [...code.keys()].sort()

    // MÅLT: chat sender otte (ingen knapRef), code sender ni.
    expect(chatNavne).toEqual(
      kontrakt.filter((n) => n !== 'knapRef').sort(),
    )
    expect(codeNavne).toEqual([...kontrakt].sort())
  })

  it('koerer er ensrettet — begge sender arbejdeKoerer uden guard', () => {
    // Dette er den divergens der blev rettet 30/10-2026 (c608b89a5f31).
    // Testen står her som kontrast: den var FORSKELLIG før.
    expect(chat.get('koerer')).toBe('koerer={arbejdeKoerer}')
    expect(code.get('koerer')).toBe('koerer={arbejdeKoerer}')
  })

  it('tekst er to sprog — og det er tilsigtet, ikke en divergens', () => {
    // chat: hovedTekst («Arbejder»/«Arbejdet»/«Tænker»/«Tænkte»)
    // code: turFortalt («Læste 3 filer · 42s»)
    expect(chat.get('tekst')).toContain('model.hovedTekst')
    expect(code.get('tekst')).toContain('turFortalt')
  })

  it('sekunder er reelt forskellige: chat viser uret mens turen kører', () => {
    // chat: `sekunder` = useTurSekunder(...) ?? varighedSekunder — altid et tal
    // code: `!streaming ? turSekunder : null` — kun når turen er ovre
    // (chat sender VARIABLEN, ikke hook-kaldet; udledningen står på linje 267)
    expect(chat.get('sekunder')).toBe('sekunder={sekunder}')
    expect(code.get('sekunder')).toContain('!streaming')
  })

  it('skillelinje er reelt forskellig — og forskellen er AFGJORT, ikke en fejl', () => {
    // AFGJORT 30/10-2026: chat beholder den bare prop. Bjørn valgte «behold
    // som nu — stregen glider ind ved turstart og bliver», og CSS'en er
    // bygget til det (`animation … both` i turhoved.css:59-62).
    // chat: bar prop → data-skillelinje fra FØRSTE render
    // code: visSkillelinje = !streaming || finalAnswerStarted || harSynligTekst
    //       (code har en svar-lås at vente på; chat har ikke)
    expect(chat.get('skillelinje')).toBe('skillelinje')
    expect(code.get('skillelinje')).toBe('skillelinje={visSkillelinje}')
  })

  it('kun code sender knapRef — chat har intet scroll-anker', () => {
    expect(chat.has('knapRef')).toBe(false)
    expect(code.get('knapRef')).toBe('knapRef={turRef}')
  })

  it('foldbar er ens i form: begge gater på om der ER arbejde', () => {
    expect(chat.get('foldbar')).toBe('foldbar={harArbejde}')
    expect(code.get('foldbar')).toBe('foldbar={arbejde.length > 0}')
  })
})
