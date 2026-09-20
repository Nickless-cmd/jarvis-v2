import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const læs = (n: string) => readFileSync(join(__dirname, n), 'utf8')
const tokens = læs('tokens.css')
const app = læs('app.css')

const brugte = (css: string) =>
  new Set([...css.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]))
const definerede = (css: string) =>
  new Set([...css.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]))

describe('design-tokens', () => {
  it('holder miljø- og inspector-stil ude af den store app.css', () => {
    const miljø = læs('environment-inspector.css')
    expect(app).not.toMatch(/\.env-panel\s*\{/)
    expect(miljø).toMatch(/\.env-panel\s*\{/)
    expect(miljø).toMatch(/\.git-add/)
    expect(miljø).toMatch(/\.git-del/)
  })

  // 17/9-2026: et heredoc-script i kommandoen gjorde godkendelseskortet højere
  // end vinduet, og Godkend/Afvis kunne ikke nås.
  it('lader godkendelseskortets kommandotekst rulle, så knapperne kan nås', () => {
    const regel = app.match(/\.approvalcard-action\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(regel).toMatch(/max-height:/)
    expect(regel).toMatch(/overflow:\s*auto/)
  })

  it('inline-kode er teal, ikke guld (Bjørn 17/9-2026)', () => {
    const regel = app.match(/\.jarvis-body :not\(pre\) > code\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(regel).toMatch(/var\(--accent\)/)
    expect(app).not.toMatch(/#d4b97a/i)
  })

  it('composerens fokus-kant er teal (accent), ikke den blå #2c3e54', () => {
    const regel = app.match(/\.composer:focus-within\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(regel).toMatch(/var\(--accent\)/)
    expect(regel).not.toMatch(/#2c3e54/i)
  })

  // Et var(--x) uden definition er ikke en skønhedsfejl: uden fallback
  // bliver `background: var(--bg)` gennemsigtig og `color: var(--fg)` arvet.
  // Med fallback brænder den en literal ind, som ikke følger temaskift.
  it('bruger ingen tokens der ikke er defineret', () => {
    const def = new Set([...definerede(tokens), ...definerede(app)])
    const manglende = [...brugte(app), ...brugte(tokens)].filter((t) => !def.has(t))
    expect([...new Set(manglende)].sort()).toEqual([])
  })

  // Hvert tema skal kunne stå alene: arver et tema en farve fra det mørke
  // :root, ender fx gul #ffd166 som tekst på hvid baggrund.
  it('definerer de semantiske farver i alle tre temaer', () => {
    const semantiske = ['--accent', '--error-fg', '--warn-fg', '--ok', '--tint', '--fg-0']
    for (const tema of ['light', 'contrast']) {
      const blok = tokens.match(
        new RegExp(`:root\\[data-theme="${tema}"\\]\\s*\\{([\\s\\S]*?)\\n\\}`),
      )
      expect(blok, `tema ${tema} mangler`).toBeTruthy()
      const har = definerede(blok?.[1] ?? "")
      expect(semantiske.filter((t) => !har.has(t)), `tema ${tema}`).toEqual([])
    }
  })

  // Bjørn 16/9-2026: «alt for mørk og alt har den samme farve sort», og efter
  // første forsøg: «du ramte oik farverne … nu lige har den stadig den brune».
  //
  // Den gamle test krævede mindst 1,10 mellem hvert trin. Det tal var MIT, ikke
  // forlæggets — CC's egne trin er 1,03 og 1,05. Kravet er nu 1:1 med det han
  // peger på, så tærsklen er skiftet ud med selve målingen.
  const MAALT_I_CC: Record<string, string> = {
    '--bg-0': '#111111',   // sidebar
    '--bg-1': '#151515',   // chat/hovedflade
    '--bg-2': '#1a1a19',   // hævet panel (miljøfelt, jobs-rude)
    '--bg-3': '#252524',   // kort i panelet
    '--bg-4': '#343434',   // valgt række
    '--line': '#292929',
    '--user-bubble': '#202020',
    '--field-bg': '#20201f',
  }

  it('det mørke tema er de MÅLTE pixels fra CC, ikke et skøn', () => {
    const blok = tokens.match(/^:root \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    const v = (navn: string) =>
      (blok.match(new RegExp(`${navn}:\\s*(#[0-9a-f]{6})`, 'i')) ?? [])[1]?.toLowerCase() ?? ''
    for (const [navn, forventet] of Object.entries(MAALT_I_CC)) {
      expect(v(navn), `${navn} skal være ${forventet} (målt på hans venstre skærm)`).toBe(forventet)
    }
    expect(v('--bg-0')).not.toBe('#000000')
  })

  // Netop DET han kalder brunt: blå-kanalen under den røde. Første forsøg lå
  // 2-4 point under (#141413, #1e1e1b, #2a2926). Forlægget ligger højst 1 under.
  it('rampen er neutral — ikke brun', () => {
    const blok = tokens.match(/^:root \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    for (const navn of ['--bg-0', '--bg-1', '--bg-2', '--bg-3', '--bg-4', '--line']) {
      const h = (blok.match(new RegExp(`${navn}:\\s*(#[0-9a-f]{6})`, 'i')) ?? [])[1] ?? '#000000'
      const [r, , b] = [1, 3, 5].map((i) => parseInt(h.substr(i, 2), 16)) as [number, number, number]
      expect(r - b, `${navn} (${h}) er ${r - b} point varmere end neutral`).toBeLessThanOrEqual(1)
    }
  })

  // Den egentlige fejl bag «alt har den samme farve»: sidebaren og hovedfladen
  // stod bogstaveligt på samme token. En farvetest alene ville ikke se det —
  // rampen kan være helt rigtig og begge flader stadig hente det samme trin.
  it('sidebar, hovedflade og panel står på HVER sin flade', () => {
    const bg = (vaelger: string) => {
      const regel = app.match(new RegExp(`^\\${vaelger} \\{([\\s\\S]*?)\\n\\}`, 'm'))?.[1] ?? ''
      return regel.match(/background:\s*var\((--[a-z0-9-]+)/)?.[1] ?? ''
    }
    const sidebar = bg('.sidebar')
    const main = bg('.main')
    expect(sidebar, 'sidebaren skal være den mørkeste flade').toBe('--bg-0')
    expect(main).toBe('--bg-1')
    expect(sidebar).not.toBe(main)
  })

  // Bjørn 16/9-2026: «fade i enden af sessionerne i venstre panel». «…» koster
  // tre tegn af netop den del af titlen der skiller to sessioner ad — og to
  // sessioner der begge hedder «Check system status and connecti…» er ikke til
  // at skelne. Fade'en lader tegnene stå.
  it('sessionstitlen fader i enden i stedet for at ende i «…»', () => {
    // Masken bor paa TITLEN, ikke paa knappen (20/9-2026). Flyttet fordi
    // aktivitets-maerket til hoejre sidder i praecis den zone fade'en rammer:
    // laa masken paa knappen, blev maerket klippet vaek.
    const regel = app.match(/^\.session-titel \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    expect(regel, '.session-titel findes ikke').toBeTruthy()
    expect(regel).not.toContain('text-overflow: ellipsis')
    expect(regel).toMatch(/mask-image:\s*linear-gradient\(to right/)
    // Uden -webkit-praefiks fader den ikke i Electrons Chromium-udgave.
    expect(regel).toContain('-webkit-mask-image')
    // Overflow skal stadig klippes — ellers flyder titlen ud over kanten og
    // fade'en maskerer noget der alligevel ikke var klippet.
    expect(regel).toContain('overflow: hidden')

    // Og knappen maa IKKE baere masken — saa ville aktivitets-maerket forsvinde.
    const knap = app.match(/^\.session-item-label \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    expect(knap, '.session-item-label findes ikke').toBeTruthy()
    expect(knap).not.toContain('mask-image')
  })

  // En menu der svæver over fladen i FLADENS egen farve har intet at løfte sig
  // fra — kun skyggen siger at den ligger ovenpå. Målt i CC: popups ligger på
  // #20201F med en lysere kant #363635.
  //
  // Bemærk hvad denne test IKKE kræver: at ALLE kort skiller sig ud. 18 kort i
  // app.css står i hovedfladens farve, og jeg var på vej til at «rette» dem
  // alle — indtil målingen viste at CC's eget «Edited 2 files»-kort står i
  // NØJAGTIG samme #151515 som chatten bag det. Inline-kort flugter med vilje;
  // det er kun de svævende der skal løfte sig.
  it('svævende menuer og dialoger løfter sig fra fladen', () => {
    for (const vaelger of ['.file-context-menu', '.connector-menu', '.mention-liste', '.pv-bekraeft']) {
      const regel = app.match(new RegExp(`\\${vaelger} \\{([\\s\\S]*?)\\n\\}`))?.[1] ?? ''
      expect(regel, `${vaelger} findes ikke`).toBeTruthy()
      const bg = regel.match(/background:\s*var\((--[a-z0-9-]+)/)?.[1]
      expect(bg, `${vaelger} svæver i hovedfladens egen farve`).toBe('--overlay-bg')
    }
  })

  // Miljoe-feltet flyttede til sin egen fil i samme uge som farven blev maalt.
  // Sammenfletningen ville have rullet farven tilbage i stilhed: den ene gren
  // SLETTEDE reglen i app.css, den anden RETTEDE den samme regel. Git kalder
  // det en konflikt ét sted og loeser det tavst det andet. Derfor maales
  // farven dér hvor reglen bor nu.
  it('miljø-feltet har panelfarven, uanset hvilken fil reglen bor i', () => {
    const miljø = læs('environment-inspector.css')
    const regel = miljø.match(/^\.env-panel \{([\s\S]*?)\}/m)?.[1] ?? ''
    expect(regel, '.env-panel findes ikke i environment-inspector.css').toBeTruthy()
    expect(regel.match(/background:\s*var\((--[a-z0-9-]+)/)?.[1]).toBe('--bg-2')
  })

  // Et kort der har samme farve som sin rude er usynligt. I CC er der to trin
  // mellem dem (#1A1A19 → #252524) — det er sådan jobs-kortene træder frem.
  it('kort ligger over deres panel, ikke i det', () => {
    const kort = app.match(/^\.jobs-kort \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    const panel = app.match(/^\.jobs-panel \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    expect(kort.match(/background:\s*var\((--[a-z0-9-]+)/)?.[1]).toBe('--bg-3')
    expect(panel.match(/background:\s*var\((--[a-z0-9-]+)/)?.[1]).toBe('--bg-2')
  })

  it('holder tekst og accent læsbare i mørkt tema', () => {
    const blok = tokens.match(/^:root \{([\s\S]*?)\n\}/m)?.[1] ?? ''
    const v = (navn: string) => (blok.match(new RegExp(`${navn}:\\s*(#[0-9a-f]{6})`, 'i')) ?? [])[1] ?? '#000000'
    const lum = (h: string) =>
      [1, 3, 5].map((i) => parseInt(h.substr(i, 2), 16) / 255)
        .map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4))
        .reduce((a, c, i) => a + [0.2126, 0.7152, 0.0722][i]! * c, 0)
    const kontrast = (a: string, b: string) => {
      const par = [lum(a), lum(b)].sort((p, q) => q - p)
      return ((par[0] ?? 0) + 0.05) / ((par[1] ?? 0) + 0.05)
    }
    const panel = v('--bg-1')
    // `--accent` er FLADE-farven og maa gerne vaere maettet; `--accent-text` er
    // den der skal kunne laeses. Netop den forskel er grunden til at de er to.
    for (const navn of ['--fg-1', '--fg-2', '--fg-3', '--accent-text', '--error-fg', '--warn-fg', '--ok']) {
      const forhold = kontrast(v(navn), panel)
      expect(forhold, `${navn} mod ${panel} gav ${forhold.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5)
    }
  })

  // Lyst tema arvede før de mørke semantiske farver fra :root — gul #ffd166
  // på hvid gav 1,44:1. Kontrast er målbar, så den måles.
  it('holder de semantiske farver læsbare i lyst tema', () => {
    const m = tokens.match(/:root\[data-theme="light"\]\s*\{([\s\S]*?)\n\}/)
    expect(m).toBeTruthy()
    const blok = m?.[1] ?? ''
    const vaerdi = (navn: string) => {
      const t = blok.match(new RegExp(`${navn}:\\s*(#[0-9a-f]{6})`, 'i'))
      expect(t, `${navn} mangler i lyst tema`).toBeTruthy()
      return t?.[1] ?? '#000000'
    }
    const lum = (h: string) =>
      [1, 3, 5]
        .map((i) => parseInt(h.substr(i, 2), 16) / 255)
        .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
        .reduce((a, c, i) => a + [0.2126, 0.7152, 0.0722][i]! * c, 0)
    const kontrast = (a: string, b: string) => {
      const par = [lum(a), lum(b)].sort((p, q) => q - p)
      return ((par[0] ?? 0) + 0.05) / ((par[1] ?? 0) + 0.05)
    }
    const grund = vaerdi('--bg-0')
    for (const navn of ['--ok', '--error-fg', '--warn-fg']) {
      const forhold = kontrast(vaerdi(navn), grund)
      expect(forhold, `${navn} mod ${grund} gav ${forhold.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5)
    }
  })
})

/**
 * Klassenavne må ikke deles af to komponenter.
 *
 * `.central-badge` blev brugt af BÅDE status-mærket i headeren og en tælle-pille
 * inde i Central-panelet. Panelets regel stod ~1350 linjer senere i filen og
 * vandt derfor: headerens mærke stod som en fyldt accent-farvet pille med hvid
 * tekst uanset hvad dens egne regler sagde. Det lignede et designvalg.
 *
 * Testen er bevidst smal — den vogter de navne der ER stødt sammen, ikke alle
 * tænkelige. En regel der larmer om alt bliver slået fra.
 */
describe('klassenavne uden sammenfald', () => {
  const css = readFileSync(join(__dirname, 'app.css'), 'utf-8')

  it('.central-badge tilhører kun header-mærket', () => {
    // Base-reglen må kun stå ét sted. Flere `.central-badge {` betyder at en
    // anden komponent har taget navnet igen.
    const baser = css.match(/^\.central-badge \{/gm) || []
    expect(baser.length).toBe(1)
  })

  it('tælle-pillen har sit eget navn', () => {
    expect(css).toContain('.central-count-badge')
  })
})

/**
 * Fade'en i bunden af Kilder og Tool-kald må KUN sidde når listen er klippet.
 * Sad den altid, ville den sidste række i en komplet liste være dæmpet uden
 * grund — og så betyder fade'en ikke længere «her er mere».
 */
describe('miljø-feltets klippede lister', () => {
  const miljø = readFileSync(join(__dirname, 'environment-inspector.css'), 'utf8')

  it('masken hænger på er-klippet, ikke på listen selv', () => {
    expect(miljø).toMatch(/\.env-rows\.er-klippet[^{]*\{[^}]*mask-image/)
    // .env-rows uden modifier må ikke have en maske.
    const bar = miljø.match(/^\.env-rows \{([^}]*)\}/m)?.[1] ?? ''
    expect(bar).not.toContain('mask-image')
  })

  it('fader NEDAD — en vandret fade hører til titler, ikke til lister', () => {
    expect(miljø).toMatch(/\.env-rows\.er-klippet[\s\S]{0,200}linear-gradient\(to bottom/)
  })
})

/**
 * Titelbjælken har sin egen linje (Bjørn 16/9-2026). To ting skal holde
 * sammen, ellers ligger knapperne oven i appens header igen:
 * bjælken er 34 px høj, og .window starter 34 px nede.
 */
describe('vinduets egen titelbjælke', () => {
  const bjaelke = app.match(/body\.egen-ramme \.vinduesbjaelke \{([\s\S]*?)\n\}/)?.[1] ?? ''
  const hoved = app.match(/body\.egen-ramme \.main \{([^}]*)\}/)?.[1] ?? ''
  const vindue = app.match(/body\.egen-ramme \.window \{([^}]*)\}/)?.[1] ?? ''

  it('bjælken er altid der — også uden skallen', () => {
    // Uden OS-ramme er den den eneste måde at flytte vinduet på. Den må ikke
    // være betinget af at en bestemt flade er tegnet.
    expect(bjaelke, 'bjælken mangler').toBeTruthy()
    expect(bjaelke).toContain('-webkit-app-region: drag')
    expect(bjaelke).toContain('display: block')
  })

  it('sidebaren går HELT op — bjælken starter hvor den slutter', () => {
    // Bjørn 16/9-2026: «venstre panel skal gå helt op». Før lå bjælken henover
    // hele bredden, og sidebaren begyndte 34 px nede.
    expect(bjaelke).toContain('left: var(--sidebar-bredde)')
    expect(vindue).toContain('height: 100vh')
    expect(vindue).toContain('margin-top: 0')
  })

  it('uden skallen dækker bjælken hele bredden', () => {
    // På setup- og fejlskærmen findes sidebaren ikke. Lod vi bjælken starte
    // 260 px inde, kunne de første 260 px ikke trækkes — og så sidder et
    // vindue uden OS-ramme fast.
    const uden = app.match(/body\.egen-ramme:not\(:has\(\.window\)\) \.vinduesbjaelke \{([^}]*)\}/)?.[1] ?? ''
    expect(uden, 'reglen for skærme uden skal mangler').toBeTruthy()
    expect(uden).toContain('left: 0')
  })

  it('hovedfladen starter PRÆCIS under bjælken', () => {
    const hoejde = bjaelke.match(/height:\s*(\d+)px/)?.[1]
    expect(hoejde, 'bjælken har ingen højde').toBeTruthy()
    expect(hoved).toContain(`padding-top: ${hoejde}px`)
  })

  it('bredden står ÉT sted — bjælken er søskende til .window', () => {
    // Custom properties arver nedad, ikke sidelæns. Defineret på .window ville
    // variablen aldrig nå bjælken; den ville falde tavst tilbage på en
    // fallback, og de to tal kunne komme i utakt uden at nogen så det.
    expect(tokens).toMatch(/--sidebar-bredde:\s*\d+px/)
    const vindueRegel = app.match(/^\.window \{([^}]*)\}/m)?.[1] ?? ''
    expect(vindueRegel).toContain('var(--sidebar-bredde)')
    expect(vindueRegel).not.toMatch(/--sidebar-bredde:/)
  })

  it('HELE fladen gør plads til skinnen — ikke kun headeren', () => {
    // Første udgave paddede kun headeren, og skinnen lå oven på samtalen:
    // «Redigerede 2 filer»-kortet blev klippet midt over af jobs-ruden.
    // Find den regel der FAKTISK gør plads — ikke en kommentar der nævner
    // klassen. Uden det matchede regexen kommentaren lige over reglen.
    const regel = app.match(/([^{}]*har-skinne[^{}]*)\{[^}]*padding-right:\s*calc\(var\(--skinne-bredde\)[^}]*\}/)?.[0] ?? ''
    for (const flade of ['.chatview-head', '.transcript', '.composer-area']) {
      expect(regel, `${flade} gør ikke plads`).toContain(flade)
    }
  })

  it('headeren ER titellinjen — pladsen til knapperne regnes ÉT sted', () => {
    // 16/9: knapperne fik deres egen linje over headeren. 19/9 (Jarvis' maaling
    // af CC Desktop 2.110.0, Bjoern: «byg den som cc desktop»): header og
    // knapper paa SAMME linje. Den gamle fejl var 152 px skrevet i headeren
    // som en usynlig aftale med knappernes stoerrelse. Nu regnes pladsen af
    // de samme variabler knapperne selv bruger.
    // Alle regler med præcis den selektor — der er to (træk + plads).
    const head = [...app.matchAll(/body\.egen-ramme \.chatview-head \{([^}]*)\}/g)].map((m) => m[1]).join(' ')
    expect(head).toContain('padding-right: var(--vk-plads)')
    expect(app).toMatch(/--vk-plads:\s*calc\(3 \* var\(--vk-str\) \+ 2 \* var\(--vk-mellemrum\) \+ var\(--vk-hoejre\)/)
    const knapper = app.match(/^\.vinduesknapper \{([^}]*)\}/m)?.[1] ?? ''
    expect(knapper).toContain('right: var(--vk-hoejre)')
    expect(knapper).toContain('gap: var(--vk-mellemrum)')
  })

  it('CC-maalene: 24 px cirkler, 13 px imellem, 10 px til kanten', () => {
    expect(app).toMatch(/--vk-str:\s*24px/)
    expect(app).toMatch(/--vk-mellemrum:\s*13px/)
    expect(app).toMatch(/--vk-hoejre:\s*10px/)
    const knap = app.match(/^\.vinduesknapper button \{([^}]*)\}/m)?.[1] ?? ''
    expect(knap).toContain('border-radius: 50%')
  })

  it('med aaben skinne goer headeren plads til BAADE knapper og skinne', () => {
    const r = app.match(/body\.egen-ramme \.har-skinne \.chatview-head \{([^}]*)\}/)?.[1] ?? ''
    expect(r).toContain('max(var(--vk-plads), calc(var(--skinne-bredde) + 16px))')
  })

  it('en flade med header har ingen ekstra bjaelke og intet skub', () => {
    expect(app).toMatch(/body\.egen-ramme:has\(\.main \.chatview-head\) \.vinduesbjaelke \{ display: none; \}/)
    expect(app).toMatch(/body\.egen-ramme \.main:has\(\.chatview-head\) \{ padding-top: 0; \}/)
  })
})

/**
 * Tekst OVENPÅ accent-fladen.
 *
 * Accenten skiftede fra ler-orange til teal 16/9-2026. Tre regler satte
 * `color: #fff` på en accent-flade. Det gik an på den mørke orange (4,0:1 —
 * stadig lavt); på teal #3FC7B4 er hvid 2,1:1 og reelt ulæselig.
 *
 * Kontrasten mod accenten kan ikke måles ud fra tokens alene, for `#fff` er
 * en literal i app.css. Derfor måles REGLEN: en accent-flade må ikke bære lys
 * tekst. Accenten er lys — teksten på den skal være mørk.
 */
describe('tekst på accent-flader', () => {
  const regler = [...app.matchAll(/([^{}]+)\{([^{}]*background:\s*var\(--accent\)[^{}]*)\}/g)]

  it('findes overhovedet nogle accent-flader at måle', () => {
    expect(regler.length).toBeGreaterThan(0)
  })

  it('ingen accent-flade bærer lys tekst', () => {
    const lyse = /color:\s*(#fff\b|#ffffff\b|white\b|var\(--fg-0\)|var\(--fg-1\))/i
    const syndere = regler
      .filter(([, , krop]) => lyse.test(krop!))
      .map(([, vaelger]) => vaelger!.trim().split('\n').pop()!.trim())
    expect(syndere, 'lys tekst på lys accent er ulæselig').toEqual([])
  })
})

/**
 * Højre skinne: hvem strækkes, og hvem gør ikke?
 *
 * Jobs og Ændringer er lister der vokser — de skal dele højden. Miljø-feltet
 * er en oversigt på få rækker; strakt ud over en hel skærm ville det være en
 * halv meter luft under fem linjer tekst (Bjørn 16/9-2026).
 */
describe('højre skinne', () => {
  const stak = app.match(/\.code-right-stack \{([^}]*)\}/)?.[1] ?? ''
  const boern = app.match(/\.code-right-stack > \* \{([^}]*)\}/)?.[1] ?? ''
  const miljoe = læs('environment-inspector.css').match(/\.code-right-stack > \.env-panel \{([^}]*)\}/)?.[1] ?? ''

  it('skinnen går fra top til bund', () => {
    expect(stak).toContain('bottom:')
    // top: 0, ikke 34. Beholderen starter allerede under titelbjælken; 34 px
    // oveni skød ruderne ned i headerens underkant (Bjørn 16/9-2026:
    // «baggrundjob og changes paneler skal gå længere op»).
    expect(stak).toMatch(/top:\s*0(;|\s)/)
  })

  it('ruderne deler højden LIGELIGT — ikke efter indhold', () => {
    // flex: 1 1 auto ville lade ruden med flest job tage det hele og den
    // anden blive en stribe.
    expect(boern).toMatch(/flex:\s*1 1 0/)
  })

  it('miljø-feltet strækkes IKKE', () => {
    expect(miljoe, 'undtagelsen for miljø-feltet mangler').toBeTruthy()
    expect(miljoe).toMatch(/flex:\s*0 0 auto/)
  })

  it('miljø-feltet ligger UNDER headeren, ikke oven i den', () => {
    // Målt 16/9-2026: headeren fylder 34-76 px og skinnen starter ved 68, så
    // feltet lå oven i dens sidste 8 px. Uden en top-margen havner det dér
    // igen, næste gang nogen flytter skinnen.
    const m = Number(miljoe.match(/margin-top:\s*(\d+)px/)?.[1] ?? 0)
    expect(m, 'for lidt til at rydde headeren').toBeGreaterThanOrEqual(8)
  })

  it('miljø-feltet er smallere end skinnen — og flugter til højre', () => {
    const bredde = Number(miljoe.match(/width:\s*(\d+)px/)?.[1] ?? 0)
    expect(bredde, 'miljø-feltet har ingen egen bredde').toBeGreaterThan(0)
    expect(bredde).toBeLessThan(360)          // skinnens bredde
    expect(miljoe).toContain('align-self: flex-end')
  })
})

/**
 * DØDE SELEKTORER i skinne-reglen.
 *
 * Tre gange 16/9-2026 skrev jeg en regel mod en klasse ingen komponent
 * bruger: `.codeview-head` (Code-visningen bruger .chatview-head) og
 * `.composer-wrap` (begge views bruger .composer-area). Den sidste var den
 * Bjørn så: «chatview rykker sig men composer gør ikke».
 *
 * En regel der peger på ingenting ser rigtig ud i en diff, består enhver
 * test der læser CSS'en, og gør intet på skærmen. Derfor måles klasserne
 * mod det der faktisk RENDERES.
 */
describe('skinne-reglen rammer klasser der findes', () => {
  const kilder = (() => {
    const ud: string[] = []
    const gaa = (mappe: string) => {
      for (const navn of readdirSync(mappe)) {
        const sti = join(mappe, navn)
        if (statSync(sti).isDirectory()) gaa(sti)
        else if (/\.tsx?$/.test(navn) && !/\.test\./.test(navn)) ud.push(readFileSync(sti, 'utf8'))
      }
    }
    gaa(join(__dirname, '..'))
    return ud.join('\n')
  })()

  it('hver klasse i .har-skinne-reglen bruges af en komponent', () => {
    const regel = app.match(/((?:\.har-skinne [^,{]+,\s*)*\.har-skinne [^,{]+)\{[^}]*--skinne-bredde/)?.[1] ?? ''
    expect(regel, 'reglen blev ikke fundet').toBeTruthy()
    const klasser = [...regel.matchAll(/\.har-skinne \.([a-z0-9-]+)/g)].map((m) => m[1]!)
    expect(klasser.length).toBeGreaterThan(1)
    const døde = klasser.filter((k) => !kilder.includes(`"${k}"`) && !kilder.includes(`${k} `) && !kilder.includes(`${k}\``))
    expect(døde, 'klasser ingen komponent bruger').toEqual([])
  })
})

/**
 * Skinnen må ikke fange klik hvor den er tom.
 *
 * Den er en beholder i FULD HØJDE, også når den kun indeholder miljø-feltet
 * på få rækker. Et element uden baggrund modtager stadig museklik, så hele
 * højre kolonne var død: header-ikonerne kunne ikke trykkes, og det så ud som
 * om appen var gået i stå (Bjørn 16/9-2026: «nu kan jeg slet ikk trykke på
 * nogen af ikonerne … det er miljø feltet der skaber problemer»).
 *
 * HVAD DENNE TEST KAN OG IKKE KAN: den læser CSS'en. Den kan se at reglen er
 * væk, men den kan ikke se om noget ANDET lægger sig oven på headeren — det
 * kræver layout, og jsdom regner ikke layout. Den del blev målt i browseren
 * med elementFromPoint.
 */
describe('skinnen fanger ikke klik hvor den er tom', () => {
  const stak = app.match(/\.code-right-stack \{([^}]*)\}/)?.[1] ?? ''
  const boern = app.match(/\.code-right-stack > \* \{([^}]*)\}/)?.[1] ?? ''

  it('selve skinnen er klik-gennemsigtig', () => {
    expect(stak).toMatch(/pointer-events:\s*none/)
  })

  it('men ruderne i den tager imod', () => {
    // Uden denne ville rettelsen gøre panelerne ubrugelige i stedet for
    // headeren — samme fejl, flyttet et skridt.
    expect(boern).toMatch(/pointer-events:\s*auto/)
  })
})

describe('animationer under streaming maler ikke hele samtalen (19/9-2026)', () => {
  it('dot-wave animerer kun opacity — ikke box-shadow', () => {
    const kf = app.match(/@keyframes dot-wave \{([\s\S]*?)\n\}/)?.[1] ?? ''
    expect(kf).toContain('opacity')
    expect(kf).not.toMatch(/box-shadow|background|width|height|filter/)
  })
  it('shimmer har sit eget lag, og sweepet er uændret (2.25s)', () => {
    const r = app.match(/^\.shimmer \{([^}]*)\}/m)?.[1] ?? ''
    expect(r).toContain('will-change: transform')
    expect(r).toContain('contain: paint')
    expect(r).toContain('shimmer-sweep 2.25s linear infinite')
  })
})

describe('headerens menuer ligger over højre-ruderne (19/9-2026)', () => {
  it('z-index over Miljø-stakken (50) og sideopgave-kortet (30)', async () => {
    const fs = await import('node:fs'); const path = await import('node:path')
    const css = fs.readFileSync(path.resolve(__dirname, 'transcript-ydelse.css'), 'utf8')
    const z = Number(css.match(/\.chatview-head \.mode-dd-menu \{ z-index: (\d+); \}/)?.[1] ?? 0)
    const stak = Number(app.match(/\.code-right-stack \{[\s\S]*?z-index: (\d+);/)?.[1] ?? 999)
    expect(z).toBeGreaterThan(stak)
    expect(z).toBeGreaterThan(30)
  })
})
