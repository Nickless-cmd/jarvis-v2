/**
 * Lukket udtryks-evaluator til chat-fladerne — chat mode, ikke code mode.
 *
 * ## Hvorfor den findes (målt 14/11-2026)
 * `form`- og `control`-fladerne interpolerede kun RENE bind-navne: `{typer}`
 * virkede, `{seats*29}` blev stående som tekst. Uden aritmetik kan en flade
 * ikke svare brugeren på et regnestykke, og så koster hvert træk et modelkald
 * — hvilket er hele grunden til at fladen findes.
 *
 * ## Hvorfor ikke `eval`
 * En flade er data fra en model. `eval`/`new Function` ville gøre enhver
 * flade til vilkårlig kode i klienten. Her er der i stedet en lukket liste af
 * funktioner og operatorer, og al egenskabsadgang går gennem validerede stier.
 *
 * ## Det vigtigste designvalg: degrader, kast ikke
 * ChatGTP's DIL (målt i APK'en, se `dil_cel`) gør det samme: `round() defaulted
 * invalid value`, `slice() returned original value because "$" is not
 * sliceable`, `localeNumberToString() defaulted invalid value`. Funktionerne
 * defaulter og sender en advarsel i stedet for at kaste.
 *
 * Grunden er målt i vores egen kode: kastede evaluatoren, ville én tastefejl i
 * én formel fjerne HELE fladen — og fejlen ville se ud som en tom besked, ikke
 * som en fejl i en formel. Nu degraderer ét udtryk til sin oprindelige tekst,
 * resten af fladen står, og advarslen kan læses bagefter.
 */

/** Én advarsel pr. degraderet udtryk. Aldrig en kastet fejl. */
export type Advarsel = string

export interface UdtrykResultat {
  vaerdi: unknown
  advarsler: Advarsel[]
}

/** Nøglen `state` er reserveret i DIL (målt: «Invalid widget binding path "state"»).
 *  Vi arver forbuddet: en bind der hedder `state` ville kollidere med selve
 *  state-laget, og fejlen ville være usynlig indtil nogen omdøbte noget. */
const RESERVERET = new Set(['state'])

/** De funktioner et udtryk må kalde. Listen er LUKKET — alt andet afvises.
 *
 *  Navnene er valgt efter DIL's egen liste (målt med `strings` i
 *  `dil_cel`), men kun dem vi kan give en ærlig implementering: `bp()`,
 *  `localeConvertCurrency()` og `localeFormatCurrency()` kræver en
 *  valutakurs vi ikke har, og en gættet kurs er værre end ingen. */
const FUNKTIONER = new Set([
  'round', 'pow', 'slice', 'keys', 'all', 'formatSigFigs', 'expr',
])

/** Hvor dybt `expr()` må kalde `expr()`. Uden loftet kunne en flade få
 *  evaluatoren til at rekursere til stacken døde — og det ville være en
 *  klient-der-fryser, ikke en flade-der-degraderer. */
const MAX_EXPR_DYBDE = 4

// --- bind-stier -------------------------------------------------------------------------------------

/** Er `sti` en bind-sti vi vil slå op i?
 *
 *  Formen er `navn`, `navn.navn`, `navn[0]`, `navn[0].navn` — intet andet.
 *  Hvert navnesegment skal matche `[a-zA-Z_][a-zA-Z0-9_]*`, indeks skal være
 *  ikke-negative heltal, og `state` må ikke være første segment.
 *
 *  Strenge validering frem for en løs regex er det DIL gør, og grunden er
 *  den samme: en sti der ser rigtig ud men ikke kan slås op ville give
 *  `undefined` midt i en flade uden at nogen kunne se hvorfor. */
const NAVN_RE = /^[a-zA-Z_][a-zA-Z0-9_]*/

export function gyldigBindSti(sti: string): boolean {
  if (!sti) return false
  let i = 0
  let forste = true
  while (i < sti.length) {
    const c = sti[i] as string
    if (c === '.') {
      // Et punktum skal efterfølges af et navn. `pris.` er ikke en sti.
      i += 1
      const m = NAVN_RE.exec(sti.slice(i))
      if (!m) return false
      i += m[0].length
      continue
    }
    if (c === '[') {
      // Indeks uden et navn foran er ikke en sti.
      if (forste) return false
      const slut = sti.indexOf(']', i)
      if (slut === -1) return false
      const indeks = sti.slice(i + 1, slut)
      if (!/^\d+$/.test(indeks)) return false
      i = slut + 1
      continue
    }
    const m = NAVN_RE.exec(sti.slice(i))
    if (!m) return false
    if (forste) {
      if (RESERVERET.has(m[0])) return false
      forste = false
    }
    i += m[0].length
  }
  return !forste
}

/** Slå en allerede valideret sti op. Returnerer `undefined` hvis noget undervejs
 *  ikke findes — det er ikke en fejl, det er en manglende værdi. */
export function slaaOp(sti: string, kontekst: Record<string, unknown>): unknown {
  const dele: Array<string | number> = []
  const re = /([a-zA-Z_][a-zA-Z0-9_]*)|\[(\d+)\]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(sti)) !== null) {
    if (m[1] !== undefined) dele.push(m[1])
    else dele.push(Number(m[2]))
  }
  let vaerdi: unknown = kontekst
  for (const d of dele) {
    if (typeof d === 'number') {
      if (!Array.isArray(vaerdi)) return undefined
      vaerdi = vaerdi[d]
    } else {
      if (vaerdi === null || typeof vaerdi !== 'object') return undefined
      // KUN egne nøgler. Almindelig `obj[k]` arver fra prototypen, så
      // `constructor` gav `Object`-funktionen og `constructor.constructor`
      // ville give `Function` — altså en vej til vilkårlig kode gennem en
      // sti der ser ud som et bind-navn. Målt 14/11-2026: uden dette tjek
      // returnerede `vurderUdtryk('constructor')` en funktion.
      if (!Object.prototype.hasOwnProperty.call(vaerdi, d)) return undefined
      vaerdi = (vaerdi as Record<string, unknown>)[d]
    }
    if (vaerdi === undefined) return undefined
  }
  return vaerdi
}

// --- tokenizer --------------------------------------------------------------------------------------

type TokType = 'tal' | 'tekst' | 'navn' | 'op' | 'punct'
interface Tok { type: TokType; v: string; n?: number }

const OPERATORER = ['<=', '>=', '==', '!=', '&&', '||', '+', '-', '*', '/', '%', '<', '>', '!']

function tokenisér(kilde: string): Tok[] {
  const toks: Tok[] = []
  let i = 0
  while (i < kilde.length) {
    const c = kilde[i] as string
    if (/\s/.test(c)) { i += 1; continue }
    // Tal. Komma som decimalseparator accepteres, fordi flader skrives på
    // dansk og «29,5» ellers ville blive læst som «29» efterfulgt af skrald.
    //
    // MEN kun når kommaet faktisk er efterfulgt af et ciffer. Uden det tjek
    // spiste tallet argument-adskilleren: `pow(2, 10)` blev læst som `pow(2.`
    // efterfulgt af `10)`, og hele kaldet fejlede med «forventede )». Målt
    // 14/11-2026 — det ramte hver eneste funktion med flere argumenter.
    if (/[0-9]/.test(c) || (c === '.' && /[0-9]/.test(kilde[i + 1] ?? ''))) {
      let j = i
      while (j < kilde.length && /[0-9]/.test(kilde[j] as string)) j += 1
      const næste = kilde[j]
      const decimal = næste === '.' || (næste === ',' && /[0-9]/.test(kilde[j + 1] ?? ''))
      if (decimal) {
        j += 1
        while (j < kilde.length && /[0-9]/.test(kilde[j] as string)) j += 1
      }
      const raa = kilde.slice(i, j).replace(',', '.')
      toks.push({ type: 'tal', v: raa, n: Number(raa) })
      i = j
      continue
    }
    if (c === '"' || c === "'") {
      let j = i + 1
      let ud = ''
      while (j < kilde.length && kilde[j] !== c) {
        if (kilde[j] === '\\' && j + 1 < kilde.length) { ud += kilde[j + 1]; j += 2; continue }
        ud += kilde[j]; j += 1
      }
      if (j >= kilde.length) return [] // uafsluttet streng: hele udtrykket afvises
      toks.push({ type: 'tekst', v: ud })
      i = j + 1
      continue
    }
    if (/[a-zA-Z_]/.test(c)) {
      let j = i
      while (j < kilde.length && /[a-zA-Z0-9_]/.test(kilde[j] as string)) j += 1
      toks.push({ type: 'navn', v: kilde.slice(i, j) })
      i = j
      continue
    }
    if (c === '(' || c === ')' || c === '[' || c === ']' || c === ',' || c === '.') {
      toks.push({ type: 'punct', v: c })
      i += 1
      continue
    }
    const op = OPERATORER.find((o) => kilde.startsWith(o, i))
    if (op) {
      toks.push({ type: 'op', v: op })
      i += op.length
      continue
    }
    return [] // ukendt tegn: udtrykket afvises som helhed
  }
  return toks
}

// --- evaluator --------------------------------------------------------------------------------------

class UdtrykFejl extends Error {}

function erTal(v: unknown): v is number {
  // `typeof v === 'number'` slipper NaN og Infinity igennem. Det er ikke
  // teoretisk: `value={NaN}` på en slider giver en TAVS tom kontrol, og
  // `Infinity` giver en bjælke der løber ud over rammen.
  return typeof v === 'number' && Number.isFinite(v)
}

function somTal(v: unknown, advarsler: Advarsel[], hvad: string): number {
  if (erTal(v)) return v
  if (typeof v === 'string') {
    const n = Number(v.replace(',', '.'))
    if (Number.isFinite(n) && v.trim() !== '') return n
  }
  if (typeof v === 'boolean') return v ? 1 : 0
  advarsler.push(`${hvad}: "${String(v)}" er ikke et tal — brugt som 0`)
  return 0
}

function somTekst(v: unknown): string {
  if (typeof v === 'string') return v
  if (erTal(v)) return String(v)
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  if (v === null || v === undefined) return ''
  return String(v)
}

function kaldFunktion(navn: string, args: unknown[], advarsler: Advarsel[], dybde: number): unknown {
  switch (navn) {
    case 'round': {
      const n = somTal(args[0], advarsler, 'round()')
      let d = 0
      if (args.length > 1) {
        const raa = args[1]
        if (erTal(raa) && Number.isInteger(raa) && raa >= 0 && raa <= 10) d = raa
        else advarsler.push(`round() ignored invalid precision: "${String(raa)}"`)
      }
      const faktor = 10 ** d
      return Math.round(n * faktor) / faktor
    }
    case 'pow': {
      const a = somTal(args[0], advarsler, 'pow()')
      const b = somTal(args[1], advarsler, 'pow()')
      const r = a ** b
      if (!Number.isFinite(r)) {
        advarsler.push(`pow(${a}, ${b}) er ikke et endeligt tal — brugt som 0`)
        return 0
      }
      return r
    }
    case 'slice': {
      const kilde = args[0]
      const start = somTal(args[1], advarsler, 'slice()')
      const slut = args.length > 2 ? somTal(args[2], advarsler, 'slice()') : undefined
      if (typeof kilde === 'string') return slut === undefined ? kilde.slice(start) : kilde.slice(start, slut)
      if (Array.isArray(kilde)) return slut === undefined ? kilde.slice(start) : kilde.slice(start, slut)
      // DIL's egen formulering — den er præcis, og den forklarer sig selv.
      advarsler.push(`slice() returned original value because "${somTekst(kilde)}" is not sliceable`)
      return kilde
    }
    case 'keys': {
      const v = args[0]
      if (v !== null && typeof v === 'object' && !Array.isArray(v)) return Object.keys(v as Record<string, unknown>)
      advarsler.push('keys() defaulted invalid value — ikke et objekt')
      return []
    }
    case 'all': {
      return args.every((a) => {
        if (typeof a === 'boolean') return a
        if (erTal(a)) return a !== 0
        if (typeof a === 'string') return a !== ''
        return a !== null && a !== undefined
      })
    }
    case 'formatSigFigs': {
      const n = somTal(args[0], advarsler, 'formatSigFigs()')
      let d = 3
      if (args.length > 1) {
        const raa = args[1]
        if (erTal(raa) && Number.isInteger(raa) && raa >= 1 && raa <= 15) d = raa
        else advarsler.push(`formatSigFigs() ignored invalid precision: "${String(raa)}"`)
      }
      if (n === 0) return 0
      const potens = Math.floor(Math.log10(Math.abs(n)))
      const faktor = 10 ** (d - 1 - potens)
      return Math.round(n * faktor) / faktor
    }
    case 'expr': {
      // `expr()` evaluerer en STRENG som et nyt udtryk. Den findes i DIL, og
      // den er den eneste vej til betinget tekst uden en `Show`-intrinsics.
      if (dybde >= MAX_EXPR_DYBDE) {
        advarsler.push(`expr() nåede dybdegrænsen (${MAX_EXPR_DYBDE}) — returneret uændret`)
        return args[0]
      }
      const indre = somTekst(args[0])
      if (!indre) return ''
      try {
        return evaluérTokens(tokenisér(indre), kontekstGlobal, advarsler, dybde + 1)
      } catch {
        advarsler.push(`expr("${indre}") kunne ikke læses — returneret som tekst`)
        return indre
      }
    }
    default:
      throw new UdtrykFejl(`ukendt funktion: ${navn}`)
  }
}

/** Konteksten sættes pr. kald. `expr()` arver den fra det kald der startede
 *  evalueringen — derfor modul-niveau frem for en parameter gennem 12 led. */
let kontekstGlobal: Record<string, unknown> = {}

function evaluérTokens(
  toks: Tok[],
  kontekst: Record<string, unknown>,
  advarsler: Advarsel[],
  dybde = 0,
): unknown {
  let p = 0
  const kig = (): Tok | undefined => toks[p]
  const erOp = (v: string): boolean => {
    const t = kig()
    return t !== undefined && t.type === 'op' && t.v === v
  }
  const erPunct = (v: string): boolean => {
    const t = kig()
    return t !== undefined && t.type === 'punct' && t.v === v
  }
  const vent = (v: string): void => {
    if (!erOp(v) && !erPunct(v)) throw new UdtrykFejl(`forventede "${v}"`)
    p += 1
  }

  function eller(): unknown {
    let venstre = og()
    while (erOp('||')) {
      p += 1
      const højre = og()
      venstre = Boolean(venstre) || Boolean(højre)
    }
    return venstre
  }
  function og(): unknown {
    let venstre = lighed()
    while (erOp('&&')) {
      p += 1
      const højre = lighed()
      venstre = Boolean(venstre) && Boolean(højre)
    }
    return venstre
  }
  function lighed(): unknown {
    let venstre = sammenligning()
    for (;;) {
      if (erOp('==')) { p += 1; venstre = venstre === sammenligning(); continue }
      if (erOp('!=')) { p += 1; venstre = venstre !== sammenligning(); continue }
      return venstre
    }
  }
  function sammenligning(): unknown {
    let venstre = additiv()
    for (;;) {
      const t = kig()
      if (t === undefined || t.type !== 'op') return venstre
      const op = t.v
      if (op !== '<' && op !== '<=' && op !== '>' && op !== '>=') return venstre
      p += 1
      const højre = additiv()
      if (typeof venstre === 'string' && typeof højre === 'string') {
        const c = venstre.localeCompare(højre, 'da')
        venstre = op === '<' ? c < 0 : op === '<=' ? c <= 0 : op === '>' ? c > 0 : c >= 0
      } else {
        const a = somTal(venstre, advarsler, `"${op}"`)
        const b = somTal(højre, advarsler, `"${op}"`)
        venstre = op === '<' ? a < b : op === '<=' ? a <= b : op === '>' ? a > b : a >= b
      }
    }
  }
  function additiv(): unknown {
    let venstre = multiplikativ()
    for (;;) {
      if (erOp('+')) {
        p += 1
        const højre = multiplikativ()
        // `+` er både addition og sammensætning. Er begge sider tal, er det
        // regnestykket; ellers limes de sammen som tekst — ellers ville
        // `{"pris: " + pris}` blive «pris: 0».
        if (erTal(venstre) && erTal(højre)) venstre = venstre + højre
        else if (typeof venstre === 'string' || typeof højre === 'string') venstre = somTekst(venstre) + somTekst(højre)
        else venstre = somTal(venstre, advarsler, '"+"') + somTal(højre, advarsler, '"+"')
        continue
      }
      if (erOp('-')) {
        p += 1
        const højre = multiplikativ()
        venstre = somTal(venstre, advarsler, '"-"') - somTal(højre, advarsler, '"-"')
        continue
      }
      return venstre
    }
  }
  function multiplikativ(): unknown {
    let venstre = unær()
    for (;;) {
      const t = kig()
      if (t === undefined || t.type !== 'op' || (t.v !== '*' && t.v !== '/' && t.v !== '%')) return venstre
      p += 1
      const højre = unær()
      const a = somTal(venstre, advarsler, `"${t.v}"`)
      const b = somTal(højre, advarsler, `"${t.v}"`)
      if ((t.v === '/' || t.v === '%') && b === 0) {
        // Division med nul ville give Infinity, som slipper gennem `typeof`.
        advarsler.push(`"${t.v}" med nul — brugt som 0`)
        venstre = 0
        continue
      }
      venstre = t.v === '*' ? a * b : t.v === '/' ? a / b : a % b
    }
  }
  function unær(): unknown {
    if (erOp('-')) { p += 1; return -somTal(unær(), advarsler, 'unær "-"') }
    if (erOp('!')) { p += 1; return !unær() }
    if (erOp('+')) { p += 1; return somTal(unær(), advarsler, 'unær "+"') }
    return primær()
  }
  function primær(): unknown {
    const t = kig()
    if (t === undefined) throw new UdtrykFejl('udtrykket slutter for tidligt')
    if (t.type === 'tal') { p += 1; return t.n ?? 0 }
    if (t.type === 'tekst') { p += 1; return t.v }
    if (erPunct('(')) {
      p += 1
      const v = eller()
      vent(')')
      return v
    }
    if (t.type === 'navn') {
      p += 1
      // Funktionskald — kun fra den lukkede liste.
      if (erPunct('(')) {
        const navn = t.v
        if (!FUNKTIONER.has(navn)) throw new UdtrykFejl(`ukendt funktion: ${navn}`)
        p += 1
        const args: unknown[] = []
        if (!erPunct(')')) {
          for (;;) {
            args.push(eller())
            if (erPunct(',')) { p += 1; continue }
            break
          }
        }
        vent(')')
        return kaldFunktion(navn, args, advarsler, dybde)
      }
      // Bind-sti: `navn`, `navn.navn`, `navn[0]` …
      let sti = t.v
      for (;;) {
        if (erPunct('.')) {
          p += 1
          const næste = kig()
          if (næste === undefined || næste.type !== 'navn') throw new UdtrykFejl('sti mangler et navn efter "."')
          sti += `.${næste.v}`
          p += 1
          continue
        }
        if (erPunct('[')) {
          p += 1
          const idx = kig()
          if (idx === undefined || idx.type !== 'tal') throw new UdtrykFejl('sti-indeks skal være et tal')
          sti += `[${Math.trunc(idx.n ?? 0)}]`
          p += 1
          vent(']')
          continue
        }
        break
      }
      if (!gyldigBindSti(sti)) throw new UdtrykFejl(`ugyldig bind-sti: ${sti}`)
      return slaaOp(sti, kontekst)
    }
    throw new UdtrykFejl(`uventet token: "${t.v}"`)
  }

  const resultat = eller()
  if (p < toks.length) throw new UdtrykFejl(`uventet token: "${toks[p]?.v ?? ''}"`)
  return resultat
}

/**
 * Evaluer ét udtryk. Kaster ALDRIG.
 *
 * @param kilde     Udtrykket, uden krølleparenteser.
 * @param kontekst  Bind-værdier (felt-navne → værdi).
 */
export function vurderUdtryk(kilde: string, kontekst: Record<string, unknown> = {}): UdtrykResultat {
  const advarsler: Advarsel[] = []
  const trimmet = kilde.trim()
  if (!trimmet) return { vaerdi: undefined, advarsler }
  const toks = tokenisér(trimmet)
  if (toks.length === 0) {
    advarsler.push(`"${trimmet}" kunne ikke læses som udtryk`)
    return { vaerdi: undefined, advarsler }
  }
  const forrige = kontekstGlobal
  kontekstGlobal = kontekst
  try {
    const vaerdi = evaluérTokens(toks, kontekst, advarsler)
    // Et resultat der ikke kan vises er ikke et resultat.
    if (typeof vaerdi === 'number' && !Number.isFinite(vaerdi)) {
      advarsler.push(`"${trimmet}" gav et uendeligt tal`)
      return { vaerdi: undefined, advarsler }
    }
    return { vaerdi, advarsler }
  } catch (e) {
    const grund = e instanceof Error ? e.message : String(e)
    advarsler.push(`"${trimmet}" blev ikke regnet: ${grund}`)
    return { vaerdi: undefined, advarsler }
  } finally {
    kontekstGlobal = forrige
  }
}

/**
 * Interpolér `{udtryk}` i en tekst. Kaster ALDRIG.
 *
 * Et udtryk der ikke kan regnes bliver stående som sin oprindelige tekst —
 * `{seats*29}` bliver `{seats*29}`, ikke tomt og ikke «undefined». Det er
 * med vilje: en læser kan se at der står noget forkert, hvor en tom plads
 * ville se ud som om fladen bare ikke havde noget at sige.
 */
export function interpolérUdtryk(
  tekst: string,
  kontekst: Record<string, unknown> = {},
): { tekst: string; advarsler: Advarsel[] } {
  if (!tekst || !tekst.includes('{')) return { tekst, advarsler: [] }
  // Kontrolstrukturer (lag 2) udfoldes FØR interpolering; en uudfoldelig struktur bliver tekst.
  const udfoldet = udfoldKontrol(tekst, kontekst)
  tekst = udfoldet.tekst
  const advarsler: Advarsel[] = [...udfoldet.advarsler]
  const ud = tekst.replace(/\{([^{}]+)\}/g, (hel, indre: string) => {
    // Uudfoldede kontrol-tags (se udfoldKontrol) er ikke udtryk.
    if (/^\s*(#|\/(each|if)\s*$|:else\s*$)/.test(indre)) return hel
    const r = vurderUdtryk(indre, kontekst)
    for (const a of r.advarsler) advarsler.push(a)
    if (r.vaerdi === undefined) return hel
    if (typeof r.vaerdi === 'number') {
      // Dansk decimalseparator: en flade der viser «29.5» i en dansk tekst
      // ser oversat ud. Kun når tallet faktisk har decimaler.
      return Number.isInteger(r.vaerdi) ? String(r.vaerdi) : String(r.vaerdi).replace('.', ',')
    }
    return somTekst(r.vaerdi)
  })
  return { tekst: ud, advarsler }
}

// --- kontrolstrukturer (DIL lag 2) --------------------------------------------------------------------
//
// `{#each liste som navn}…{/each}` og `{#if udtryk}…{:else}…{/if}` over SKALARE lister.
// Samme grammatik og samme grænser som `_udfold_kontrol` i `core/services/jarvis_ui_guard.py`
// (paritet vogtes af `tests/test_dil_bind_sti_paritet.py`). Der er INGEN ny evaluator:
// betingelser går gennem `vurderUdtryk` ovenfor. Kaster aldrig — en struktur der ikke kan
// udfoldes bliver stående som sin oprindelige tekst, og en advarsel forklarer hvorfor.

export const KONTROL_MAX_DYBDE = 3
export const KONTROL_MAX_LISTE = 50
export const KONTROL_MAX_TEGN = 20000

const KONTROL_TAG = /\{(#each [^{}]*|#if [^{}]*|:else|\/each|\/if)\}/g
const EACH_RE = /^#each\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\])*)\s+som\s+([a-zA-Z_][a-zA-Z0-9_]*)$/

type KontrolNode =
  | { t: 'tekst'; s: string }
  | { t: 'each'; liste: string; navn: string; krop: KontrolNode[]; kilde: string }
  | { t: 'if'; udtryk: string; da: KontrolNode[]; ellers: KontrolNode[]; kilde: string }

function erSkalarVaerdi(v: unknown): boolean {
  return typeof v === 'string' || typeof v === 'boolean' || (typeof v === 'number' && Number.isFinite(v))
}

function sandhed(v: unknown): boolean {
  return v !== undefined && v !== null && v !== false && v !== 0 && v !== ''
}

function skalarTekst(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(v).replace('.', ',')
  return somTekst(v)
}

function parsKontrol(tekst: string, advarsler: Advarsel[]): KontrolNode[] | null {
  type Ramme = { node: KontrolNode | null; liste: KontrolNode[]; efterElse: boolean; start: number }
  const rod: KontrolNode[] = []
  const stak: Ramme[] = [{ node: null, liste: rod, efterElse: false, start: 0 }]
  let sidste = 0
  KONTROL_TAG.lastIndex = 0
  let m: RegExpExecArray | null
  const top = () => stak[stak.length - 1]
  while ((m = KONTROL_TAG.exec(tekst)) !== null) {
    if (m.index > sidste) top().liste.push({ t: 'tekst', s: tekst.slice(sidste, m.index) })
    sidste = m.index + m[0].length
    const tag = m[1]
    if (tag.startsWith('#each ')) {
      const em = EACH_RE.exec(tag)
      if (!em || !gyldigBindSti(em[1])) { advarsler.push(`ugyldig #each: "${m[0]}"`); return null }
      if (stak.length > KONTROL_MAX_DYBDE) { advarsler.push(`kontrolstrukturer er for dybt nested (max ${KONTROL_MAX_DYBDE})`); return null }
      const node: KontrolNode = { t: 'each', liste: em[1], navn: em[2], krop: [], kilde: '' }
      top().liste.push(node)
      stak.push({ node, liste: node.krop, efterElse: false, start: m.index })
    } else if (tag.startsWith('#if ')) {
      if (stak.length > KONTROL_MAX_DYBDE) { advarsler.push(`kontrolstrukturer er for dybt nested (max ${KONTROL_MAX_DYBDE})`); return null }
      const udtryk = tag.slice(4).trim()
      if (!udtryk) { advarsler.push('#if uden udtryk'); return null }
      const node: KontrolNode = { t: 'if', udtryk, da: [], ellers: [], kilde: '' }
      top().liste.push(node)
      stak.push({ node, liste: node.da, efterElse: false, start: m.index })
    } else if (tag === ':else') {
      const r = top()
      if (!r.node || r.node.t !== 'if' || r.efterElse) { advarsler.push('{:else} uden tilhørende #if'); return null }
      r.efterElse = true
      r.liste = r.node.ellers
    } else {
      const r = top()
      const vent = tag === '/each' ? 'each' : 'if'
      if (!r.node || r.node.t !== vent) { advarsler.push(`{${tag}} uden tilhørende #${vent}`); return null }
      r.node.kilde = tekst.slice(r.start, sidste)
      stak.pop()
    }
  }
  if (sidste < tekst.length) top().liste.push({ t: 'tekst', s: tekst.slice(sidste) })
  if (stak.length > 1) { advarsler.push('kontrolstruktur er ikke lukket'); return null }
  return rod
}

function udfoldNoder(noder: KontrolNode[], kontekst: Record<string, unknown>, advarsler: Advarsel[]): string {
  let ud = ''
  for (const n of noder) {
    if (n.t === 'tekst') { ud += n.s; continue }
    if (n.t === 'each') {
      const liste = slaaOp(n.liste, kontekst)
      if (!Array.isArray(liste) || !liste.every(erSkalarVaerdi)) {
        advarsler.push(`#each ${n.liste}: er ikke en liste af skalarer`)
        ud += n.kilde
        continue
      }
      if (liste.length > KONTROL_MAX_LISTE) {
        advarsler.push(`#each ${n.liste}: listen har ${liste.length} elementer (max ${KONTROL_MAX_LISTE})`)
        ud += n.kilde
        continue
      }
      for (const element of liste) {
        const indre = udfoldNoder(n.krop, { ...kontekst, [n.navn]: element }, advarsler)
        ud += indre.split(`{${n.navn}}`).join(skalarTekst(element))
      }
      continue
    }
    const r = vurderUdtryk(n.udtryk, kontekst)
    if (r.vaerdi === undefined) {
      for (const a of r.advarsler) advarsler.push(a)
      advarsler.push(`#if ${n.udtryk}: kunne ikke afgøres`)
      ud += n.kilde
      continue
    }
    ud += udfoldNoder(sandhed(r.vaerdi) ? n.da : n.ellers, kontekst, advarsler)
  }
  return ud
}

/** Udfold `{#each}`/`{#if}` i en tekst. Kaster ALDRIG. */
export function udfoldKontrol(
  tekst: string,
  kontekst: Record<string, unknown> = {},
): { tekst: string; advarsler: Advarsel[] } {
  const advarsler: Advarsel[] = []
  if (!tekst || !tekst.includes('{#')) return { tekst, advarsler }
  const noder = parsKontrol(tekst, advarsler)
  if (noder === null) return { tekst, advarsler }
  const ud = udfoldNoder(noder, kontekst, advarsler)
  if (ud.length > KONTROL_MAX_TEGN) {
    advarsler.push(`udfoldet tekst er for lang (${ud.length} tegn, max ${KONTROL_MAX_TEGN})`)
    return { tekst, advarsler }
  }
  return { tekst: ud, advarsler }
}
