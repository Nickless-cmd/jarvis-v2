import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Kaskade-vagten (26/9-2026).
 *
 * Baggrun­den er en fejl der kostede en hel runde: `.rh-rows` fik
 * `padding-top: 18px` i app.css, men målingen på skærmen var *identisk* med
 * før. Årsagen var ikke tallet — det var kaskaden. Elementet bærer både
 * `env-rows` og `rh-rows`, og `.env-rows { padding: 0 }` bor i
 * `environment-inspector.css`, som App.tsx importerer EFTER app.css.
 * Samme specificitet (0,1,0) → den senere vinder → `padding: 0` åd de 18 px.
 *
 * Testen findes fordi ingen af de andre fangede det: tokens.test.ts ser kun
 * tokens, RunHealth.test.tsx ser kun DOM'en. En regel der står rigtigt i
 * kilden og alligevel taber til en anden fil er usynlig for begge.
 *
 * Den måler det der faktisk afgør sagen: hvem vinder for et element med
 * class="env-rows rh-rows".
 */

const laes = (f: string) => readFileSync(join(__dirname, f), 'utf8')

/**
 * Kommentarer VÆK før parsing. Uden det spiser regex'en dem med: `[^{}]`
 * matcher newline, så en kommentar der slutter lige før en regel bliver
 * hale på den næste selektor — og så ser vi reglen slet ikke. Det kostede
 * en fejlet kørsel at finde ud af.
 */
const rens = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')

/** (id, klasse, element) — den kaskade-vægt browseren selv bruger. */
function vaegt(selektor: string): [number, number, number] {
  const id = (selektor.match(/#[\w-]+/g) ?? []).length
  const klasse = (
    selektor.match(/\.[\w-]+/g) ?? []
  ).length + (selektor.match(/\[[^\]]+\]/g) ?? []).length
  const element = (
    selektor
      .replace(/[#.][\w-]+/g, '')
      .replace(/\[[^\]]+\]/g, '')
      .match(/[a-z]+/g) ?? []
  ).length
  return [id, klasse, element]
}

const stoerre = (a: [number, number, number], b: [number, number, number]) =>
  a[0] !== b[0] ? a[0] > b[0] : a[1] !== b[1] ? a[1] > b[1] : a[2] > b[2]

interface Regel {
  fil: string
  selektor: string
  krop: string
  raekkefoelge: number
}

/** Alle regler i én fil hvis selektor udelukkende består af klasse-navne. */
function regler(fil: string, kilde: string, startOffset = 0): Regel[] {
  const ud: Regel[] = []
  // Simpel nok til vores formål: selektor { krop }. Ingen næstning, ingen @media
  // med regler indeni der sætter padding på dette element.
  const re = /([^{}@\n][^{}]*?)\{([^{}]*)\}/g
  let m: RegExpExecArray | null
  while ((m = re.exec(kilde)) !== null) {
    const selektor = (m[1] ?? '').trim()
    if (!/^[.\w\s,:-]+$/.test(selektor)) continue
    ud.push({
      fil,
      selektor,
      krop: m[2] ?? '',
      raekkefoelge: startOffset + m.index,
    })
  }
  return ud
}

/** Regler der rammer et element med class="env-rows rh-rows" og sætter top-padding. */
function kandidater(): Regel[] {
  const app = rens(laes('app.css'))
  const insp = rens(laes('environment-inspector.css'))
  // app.css indlæses først (App.tsx linje 40-41) — derfor får dens regler
  // lavere rækkefølge-nummer end inspector'ens.
  const alle = [...regler('app.css', app, 0), ...regler('environment-inspector.css', insp, 1_000_000)]

  return alle.filter((r) => {
    const dele = r.selektor.split(',').map((s) => s.trim())
    // En selektor rammer kun hvis HVER del er en ren klasse-kæde af env-rows/rh-rows.
    const rammer = dele.some((s) => {
      const klasser = s.match(/\.[\w-]+/g) ?? []
      if (klasser.length === 0) return false
      return klasser.every((k) => k === '.env-rows' || k === '.rh-rows')
    })
    if (!rammer) return false
    // Padding-top kan sættes direkte eller via shorthand.
    return /padding-top\s*:/.test(r.krop) || /(^|;)\s*padding\s*:/.test(r.krop)
  })
}

/** Top-padding som browseren ville regne den ud for elementet. */
function vinderPaddingTop(regler: Regel[]): { vaerdi: string; selektor: string } | null {
  let vinder: Regel | null = null
  let vinderVaegt: [number, number, number] = [0, 0, 0]

  for (const r of regler) {
    // Den mest specifikke selektor INDE i reglen er den der gælder for os.
    const dele = r.selektor
      .split(',')
      .map((s) => s.trim())
      .filter((s) => (s.match(/\.[\w-]+/g) ?? []).every((k) => k === '.env-rows' || k === '.rh-rows'))
    const bedste = dele
      .map((s) => ({ s, v: vaegt(s) }))
      .sort((a, b) => (stoerre(b.v, a.v) ? 1 : -1))[0]
    if (!bedste) continue

    if (
      vinder === null ||
      stoerre(bedste.v, vinderVaegt) ||
      (!stoerre(vinderVaegt, bedste.v) &&
        bedste.v.join() === vinderVaegt.join() &&
        r.raekkefoelge >= vinder.raekkefoelge)
    ) {
      vinder = r
      vinderVaegt = bedste.v
    }
  }

  if (!vinder) return null
  const direkte = /padding-top\s*:\s*([^;]+)/.exec(vinder.krop)
  if (direkte) return { vaerdi: (direkte[1] ?? '').trim(), selektor: vinder.selektor }
  const short = /(?:^|;)\s*padding\s*:\s*([^;]+)/.exec(vinder.krop)
  const dele = short ? (short[1] ?? '').trim().split(/\s+/) : []
  // shorthand: top er ALTID første værdi (1, 2, 3 eller 4 værdier).
  const top = dele.length === 0 ? null : dele[0]
  return top ? { vaerdi: top, selektor: vinder.selektor } : null
}

describe('kaskaden for miljø-feltets kontekst-række', () => {
  it('padding-top over Kontekst vinder over .env-rows i inspector-filen', () => {
    const kand = kandidater()
    // Begge regler SKAL findes — ellers måler testen ingenting.
    const selektoerer = kand.map((r) => r.selektor)
    expect(selektoerer.some((s) => s.includes('.env-rows') && s.includes('.rh-rows'))).toBe(true)

    const vinder = vinderPaddingTop(kand)
    expect(vinder).not.toBeNull()
    // 14 px — ikke 18. Maalt paa skaermen 26/9-2026: med 18 laa linjen 24 px
    // over teksten mod 18 under. Regnestykket staar i app.css:
    //   over  = margin-top (6) + padding-top (14) = 20
    //   under = listens bundmargin (8) + skillestregens margin (10) = 18
    // `.env-row` har ingen egen padding — den antagelse kostede 4 px.
    expect(vinder!.vaerdi).toBe('14px')
  })

  it('den vægtede selektor har højere specificitet end den bare .env-rows', () => {
    // Dette er selve mekanismen: er de lige, vinder inspector-filen (senere).
    const vaegtet = vaegt('.env-rows.rh-rows')
    const bar = vaegt('.env-rows')
    expect(stoerre(vaegtet, bar)).toBe(true)
    expect(vaegtet).toEqual([0, 2, 0])
    expect(bar).toEqual([0, 1, 0])
  })
})
