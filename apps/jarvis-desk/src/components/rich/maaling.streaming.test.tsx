// @vitest-environment jsdom
/**
 * MÅLING (29/9-2026) — ikke en vagt. Den printer tal, den dømmer ikke.
 *
 * Spørgsmålet: hakker streamingen fordi `key={i}` får blokke til at remounte
 * når blokgrænserne flytter sig under streaming? Og vokser arbejdet med teksten?
 *
 * Fire uafhængige tal:
 *   A. indeks-forskydning  — ren funktion, gælder OGSÅ mobilen (samme markdownBlokke.ts)
 *   B. DOM-churn           — hvor mange noder fjernes/genindsættes (remount = fjernet+tilføjet)
 *   C. tid pr. render      — vokser den med teksten?
 *   D. forbehandling alene — enforceStructure+stripToolEchoes+stabilize, uden React
 */
import { describe, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render } from '@testing-library/react'
import { delIBlokke } from '../../lib/markdownBlokke'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { MarkdownRenderer } from './MarkdownRenderer'

const replik = readFileSync(resolve(process.cwd(), 'src/components/rich/__fixtures__/replik.txt'), 'utf8')

const afsnit = (i: number) =>
  `## Afsnit ${i}\n\nTekst ${i} med **fed**, \`kode\` og [et link](https://x.dk).\n\n- et ${i}\n\n- to med \`sti.ts:${i}\`\n\n| k | v |\n|---|---|\n| load | ${i} |\n\n\`\`\`ts\nconst a${i} = 1\n\nconst b${i} = 2\n\`\`\`\n\n`
const syntetisk = Array.from({ length: 30 }, (_, i) => afsnit(i)).join('') + 'Slutafsnit.'

const forbehandl = (t: string) => enforceStructure(stripToolEchoes(stabilizeStreamingMarkdown(t)))

const snit = (xs: number[]) => xs.reduce((s, x) => s + x, 0) / xs.length
const pct = (xs: number[], p: number) => [...xs].sort((a, b) => a - b)[Math.min(xs.length - 1, Math.floor(xs.length * p))]!

// ── A. Indeks-forskydning ────────────────────────────────────────────────
// For hvert delta: hvor mange blokke har IKKE længere samme (index, indhold)?
// Ren append → 0-1 (kun den levende hale). Stort tal = indices skifter.
function indeksForskydning(tekst: string, delta: number) {
  let forrige: string[] = []
  let trin = 0
  let trinMedForskydning = 0
  let vaerst = 0
  let sumForskudt = 0
  let maxBlokke = 0
  for (let n = delta; n <= tekst.length; n += delta) {
    const nu = delIBlokke(forbehandl(tekst.slice(0, n)))
    if (forrige.length) {
      let i = 0
      while (i < forrige.length && i < nu.length && forrige[i] === nu[i]) i++
      const forskudt = forrige.length - i
      if (forskudt > 0) {
        trinMedForskydning++
        sumForskudt += forskudt
        vaerst = Math.max(vaerst, forskudt)
      }
      trin++
    }
    maxBlokke = Math.max(maxBlokke, nu.length)
    forrige = nu
  }
  return { trin, trinMedForskydning, vaerst, gnsForskudt: sumForskudt / Math.max(1, trinMedForskydning), maxBlokke }
}

// ── B. DOM-churn ─────────────────────────────────────────────────────────
// Noder der forsvandt men kom igen med samme indhold = remount.
function domChurn(tekst: string, delta: number) {
  const { container, rerender } = render(<MarkdownRenderer text="" streaming />)
  const set = new Set<Element>()
  const snap = () => {
    const nu = new Set(container.querySelectorAll('*'))
    let fjernet = 0
    let tilfoejet = 0
    for (const n of set) if (!nu.has(n)) fjernet++
    for (const n of nu) if (!set.has(n)) tilfoejet++
    set.clear()
    nu.forEach((n) => set.add(n))
    return { fjernet, tilfoejet }
  }
  snap()
  let fjernet = 0
  let tilfoejet = 0
  let trin = 0
  let vaerst = 0
  for (let n = delta; n <= tekst.length; n += delta) {
    rerender(<MarkdownRenderer text={tekst.slice(0, n)} streaming />)
    const r = snap()
    fjernet += r.fjernet
    tilfoejet += r.tilfoejet
    vaerst = Math.max(vaerst, r.fjernet)
    trin++
  }
  const slutNoder = container.querySelectorAll('*').length
  return { trin, fjernet, tilfoejet, vaerst, slutNoder, churnPrTrin: (fjernet + tilfoejet) / trin }
}

// ── C. Tid pr. render ────────────────────────────────────────────────────
function tidPrRender(tekst: string, delta: number) {
  const { rerender } = render(<MarkdownRenderer text="" streaming />)
  const tider: number[] = []
  for (let n = delta; n <= tekst.length; n += delta) {
    const a = performance.now()
    rerender(<MarkdownRenderer text={tekst.slice(0, n)} streaming />)
    tider.push(performance.now() - a)
  }
  const ti = Math.max(1, Math.floor(tider.length / 10))
  return {
    n: tider.length,
    p50: pct(tider, 0.5),
    p95: pct(tider, 0.95),
    start: snit(tider.slice(ti, 2 * ti)),
    slut: snit(tider.slice(-ti)),
    vaekst: snit(tider.slice(-ti)) / Math.max(0.001, snit(tider.slice(ti, 2 * ti))),
  }
}

// ── D. Forbehandling alene ───────────────────────────────────────────────
function forbehandlingTid(tekst: string, delta: number) {
  const tider: number[] = []
  for (let n = delta; n <= tekst.length; n += delta) {
    const a = performance.now()
    forbehandl(tekst.slice(0, n))
    tider.push(performance.now() - a)
  }
  const ti = Math.max(1, Math.floor(tider.length / 10))
  return { n: tider.length, p50: pct(tider, 0.5), p95: pct(tider, 0.95), start: snit(tider.slice(ti, 2 * ti)), slut: snit(tider.slice(-ti)), vaekst: snit(tider.slice(-ti)) / Math.max(0.001, snit(tider.slice(ti, 2 * ti))) }
}

const r2 = (x: number) => Math.round(x * 100) / 100

describe('MÅLING: streaming — indeks, remounts, tid', () => {
  it('måler virkelig replik (30.545 tegn, 123 tomme linjer, 0 fences)', () => {
    const A = indeksForskydning(replik, 48)
    console.log(`\n═══ A. INDEKS-FORSKYDNING — virkelig replik (delta=48) ═══`)
    console.log(`  trin:                        ${A.trin}`)
    console.log(`  trin hvor indices forskød:   ${A.trinMedForskydning}  (${r2((A.trinMedForskydning / A.trin) * 100)}%)`)
    console.log(`  værste forskydning:          ${A.vaerst} blokke`)
    console.log(`  gns. forskudte blokke:       ${r2(A.gnsForskudt)}`)
    console.log(`  max antal blokke:            ${A.maxBlokke}`)

    const B = domChurn(replik, 200)
    console.log(`\n═══ B. DOM-CHURN — virkelig replik (delta=200) ═══`)
    console.log(`  trin:                        ${B.trin}`)
    console.log(`  noder fjernet i alt:         ${B.fjernet}`)
    console.log(`  noder tilføjet i alt:        ${B.tilfoejet}`)
    console.log(`  værste enkelt-trin (fjernet):${B.vaerst}`)
    console.log(`  churn pr. trin:              ${r2(B.churnPrTrin)}`)
    console.log(`  noder i slutdokumentet:      ${B.slutNoder}`)

    const C = tidPrRender(replik, 200)
    console.log(`\n═══ C. TID PR. RENDER — virkelig replik (delta=200) ═══`)
    console.log(`  renders:                     ${C.n}`)
    console.log(`  p50 / p95:                   ${r2(C.p50)} / ${r2(C.p95)} ms`)
    console.log(`  første tiendedel:            ${r2(C.start)} ms`)
    console.log(`  sidste tiendedel:            ${r2(C.slut)} ms`)
    console.log(`  VÆKST:                       ×${r2(C.vaekst)}`)

    const D = forbehandlingTid(replik, 48)
    console.log(`\n═══ D. FORBEHANDLING ALENE (uden React, delta=48) ═══`)
    console.log(`  p50 / p95:                   ${r2(D.p50)} / ${r2(D.p95)} ms`)
    console.log(`  første tiendedel:            ${r2(D.start)} ms`)
    console.log(`  sidste tiendedel:            ${r2(D.slut)} ms`)
    console.log(`  VÆKST:                       ×${r2(D.vaekst)}`)
  }, 300000)

  it('måler syntetisk doc MED fences (4.900 tegn)', () => {
    const A = indeksForskydning(syntetisk, 24)
    console.log(`\n═══ A. INDEKS-FORSKYDNING — syntetisk m. fences (delta=24) ═══`)
    console.log(`  trin:                        ${A.trin}`)
    console.log(`  trin hvor indices forskød:   ${A.trinMedForskydning}  (${r2((A.trinMedForskydning / A.trin) * 100)}%)`)
    console.log(`  værste forskydning:          ${A.vaerst} blokke`)
    console.log(`  gns. forskudte blokke:       ${r2(A.gnsForskudt)}`)
    console.log(`  max antal blokke:            ${A.maxBlokke}`)

    const B = domChurn(syntetisk, 24)
    console.log(`\n═══ B. DOM-CHURN — syntetisk m. fences (delta=24) ═══`)
    console.log(`  trin:                        ${B.trin}`)
    console.log(`  noder fjernet i alt:         ${B.fjernet}`)
    console.log(`  noder tilføjet i alt:        ${B.tilfoejet}`)
    console.log(`  værste enkelt-trin (fjernet):${B.vaerst}`)
    console.log(`  churn pr. trin:              ${r2(B.churnPrTrin)}`)
    console.log(`  noder i slutdokumentet:      ${B.slutNoder}`)
  }, 300000)
})
