import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const læs = (n: string) => readFileSync(join(__dirname, n), 'utf8')
const tokens = læs('tokens.css')
const app = læs('app.css')

const brugte = (css: string) =>
  new Set([...css.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]))
const definerede = (css: string) =>
  new Set([...css.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]))

describe('design-tokens', () => {
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
