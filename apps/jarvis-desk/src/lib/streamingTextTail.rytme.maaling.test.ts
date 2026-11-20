// @vitest-environment node
/**
 * Ordhalens rytme og samspil med paceren — målt i Chromium.
 *
 * Gates som de øvrige målinger (RUN_BROWSER_LAYOUT_MEASUREMENT=1).
 *
 * Paceren replikeres med den ÆGTE `naesteRate` og samme tick-løkke som
 * `paceRate.maaling.test.ts` (60 fps, kredit, loft pr. frame). Den afspilles i
 * realtid mod den ægte `MarkdownRenderer` + CSS i Chromium.
 */
import { describe, expect, it } from 'vitest'
import { PACE_ANKOMST_VINDUE_S, PACE_GULV, naesteRate } from './paceRate'
import { STREAMING_TEXT_VARIANTS, type StreamingTextVariant } from './streamingTextTail'
import { aabnBaenk, installerMaaler, ordTekst } from './streamingTextTail.baenk'
import { HALE_AFVIKLING_MS } from '../components/rich/MarkdownRenderer'

const KOERT = process.env.RUN_BROWSER_LAYOUT_MEASUREMENT === '1'
const FRAME_S = 1 / 60

/** (tid ms, antal viste tegn) pr. frame hvor noget blev afsløret. */
function pacerSkema(total: number, ankomst: (frame: number) => number | null): { t: number; shown: number }[] {
  let shown = 0, rate = PACE_GULV, maal = 0, vStartMaal = 0, vStartTid = 0, kredit = 0
  const ud: { t: number; shown: number }[] = []
  for (let frame = 1; shown < total && frame < 100_000; frame++) {
    const nu = frame * FRAME_S
    const v = ankomst(frame)
    if (v !== null) maal = Math.min(total, maal + v)
    const pending = Math.max(0, maal - shown)
    if (pending <= 0 && maal < total) continue
    const dtA = vStartTid > 0 ? nu - vStartTid : 0
    const vindueUde = dtA >= PACE_ANKOMST_VINDUE_S
    const a = maal - vStartMaal > 0 && vindueUde ? (maal - vStartMaal) / dtA : null
    if (vindueUde || vStartTid === 0) { vStartMaal = maal; vStartTid = nu }
    rate = naesteRate({ pending, forrigeRate: rate, ankomst: a, dt: FRAME_S })
    const maks = Math.max(6, Math.ceil(rate * 0.1))
    kredit = Math.min(maks, kredit + rate * FRAME_S)
    const step = Math.min(maks, Math.floor(kredit))
    if (step > 0) { kredit -= step; shown = Math.min(maal, shown + step); ud.push({ t: Math.round(nu * 1000), shown }) }
  }
  return ud
}

const SCENARIER: Record<string, { ord: number; ankomst: (f: number) => number | null }> = {
  // ét ord (7 tegn) hver 700 ms
  'langsom enkeltord': { ord: 14, ankomst: (f) => (f % 42 === 0 ? 7 : null) },
  // ~40 tegn hver 100 ms
  'normal': { ord: 60, ankomst: (f) => (f % 6 === 0 ? 40 : null) },
  // store SSE-chunks: 350 tegn hver 400 ms
  'hurtig, store chunks': { ord: 100, ankomst: (f) => (f % 24 === 0 ? 350 : null) },
  // pause på 1,5 s, så burst på 300 tegn, så drypper det igen
  'ujævn: pauser og bursts': { ord: 90, ankomst: (f) => (f === 1 ? 40 : f === 120 ? 300 : f > 240 && f % 20 === 0 ? 14 : null) },
  // serveren er færdig før paceren er begyndt: alt i frame 1 (paceren indhenter efterslæb)
  'serveren færdig før paceren': { ord: 80, ankomst: (f) => (f === 1 ? 80 * 7 : null) },
}

describe.skipIf(!KOERT)('pacer/animations-samspil', () => {
  for (const [navn, sc] of Object.entries(SCENARIER)) {
    it(`${navn}: ingen tilbageholdt tekst, ingen unaturligt tætte starter`, async () => {
      const fuld = ordTekst(sc.ord)
      const skema = pacerSkema(fuld.length, sc.ankomst)
      const b = await aabnBaenk({ theme: 'dark' })
      try {
        const { page } = b
        await installerMaaler(page)
        const m = await page.evaluate(async (args) => {
          const { fuld, skema } = args
          const reveal: Record<string, number> = {}
          const tekstFejl: string[] = []
          const t0 = performance.now()
          let i = 0
          await new Promise<void>((klar) => {
            const tick = () => {
              const nu = performance.now() - t0
              while (i < skema.length && skema[i]!.t <= nu) {
                const vist = fuld.slice(0, skema[i]!.shown)
                ;(window as any).__saetTekst(vist)
                const t = performance.now()
                for (const mm of vist.matchAll(/(\S+)\s/g)) if (!(mm[1]! in reveal)) reveal[mm[1]!] = t
                i++
              }
              if (i < skema.length) requestAnimationFrame(tick); else klar()
            }
            requestAnimationFrame(tick)
          })
          // React committer asynkront: vent to frames, så den sidste afsløring er i DOM'en.
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
          // Teksten i DOM'en skal være PRÆCIS det paceren har afsløret — animationen holder intet tilbage.
          const dom = document.getElementById('krop')!.textContent!.replace(/\s+/g, ' ').trim()
          if (dom !== fuld.replace(/\s+/g, ' ').trim()) tekstFejl.push(dom.slice(-40))
          await new Promise((r) => setTimeout(r, 900))
          return { reveal, tekstFejl, ev: (window as any).__ev as { t: number; type: string; navn: string; ord: string }[] }
        }, { fuld, skema })

        const starter = m.ev.filter((e) => e.type === 'start' && e.navn === 'opacity')
        const slutter = m.ev.filter((e) => e.type === 'end' && e.navn === 'color')
        const holdBack = starter.map((e) => e.t - (m.reveal[e.ord] ?? e.t))
        const gaps = starter.slice(1).map((e, k) => e.t - starter[k]!.t)
        const sammeFrame = gaps.filter((g) => g < 12).length
        const maksHold = Math.max(...holdBack)
        const taet = Math.min(...gaps)
        console.info('[PACER-SAMSPIL]', navn, {
          ord: sc.ord, starter: starter.length, slutter: slutter.length,
          maksHoldMs: Math.round(maksHold), minGapMs: Math.round(taet), starterISammeFrame: sammeFrame,
          pacerVarighedMs: skema[skema.length - 1]!.t,
        })
        expect(b.fejl).toEqual([])
        expect(m.tekstFejl).toEqual([])
        // Ét ord = én start (ingen genstart), og alle landede (ingen afbrudt hale).
        const brugt = new Set(starter.map((e) => e.ord))
        expect(starter.length).toBe(brugt.size)
        expect(slutter.length).toBe(starter.length)
        // Hold-back: ordet må højst vente sin egen forskydning (2 × offset) + to frames
        // på at STARTE. Et enkelt nyt ord skal starte inden for et par frames.
        const offset = STREAMING_TEXT_VARIANTS.Snappy.timeOffsetBetweenParts
        expect(maksHold).toBeLessThanOrEqual(2 * offset + 40)
      } finally { await b.luk() }
    }, 120_000)
  }

  it('slutningen: halen afbrydes ikke når streamen ender midt i de sidste ords animation', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      await installerMaaler(page)
      for (let i = 1; i <= 6; i++) { await page.evaluate((t) => (window as any).__saetTekst(t), ordTekst(i)); await page.waitForTimeout(60) }
      const fg = await page.evaluate(() => getComputedStyle(document.getElementById('krop')!).color)
      const r = await page.evaluate(async (ms) => {
        const w = window as any
        const foer = performance.now()
        const op = (o: string) => { const e = [...document.querySelectorAll('#krop span')].find((x) => x.textContent?.trim() === o); return e ? Number(getComputedStyle(e).opacity) : -1 }
        const op6Foer = op('ord6')
        w.__saetStreaming(false)
        const serie: number[] = []
        const textFoer = document.getElementById('krop')!.textContent
        while (performance.now() - foer < ms + 200) { serie.push(op('ord6')); await new Promise((r) => requestAnimationFrame(r)) }
        return { op6Foer, serie, textFoer, textEfter: document.getElementById('krop')!.textContent, spans: document.querySelectorAll('#krop span').length }
      }, HALE_AFVIKLING_MS)
      const ev = (await page.evaluate(() => (window as any).__ev)) as { type: string; navn: string; ord: string; farve: string }[]
      // Første frame efter slut: ordet findes stadig og har ikke sprunget til 1.
      expect(r.serie[0]!).toBeGreaterThanOrEqual(0)
      expect(r.serie[0]!).toBeLessThanOrEqual(1)
      expect(r.serie[0]! - r.op6Foer).toBeLessThan(0.45) // ingen pop (uden afvikling: 0.67 → 1.0)
      for (let i = 1; i < r.serie.length; i++) if (r.serie[i]! >= 0 && r.serie[i - 1]! >= 0) expect(r.serie[i]!).toBeGreaterThanOrEqual(r.serie[i - 1]! - 1e-6)
      expect(ev.filter((e) => e.type === 'cancel' && e.ord === 'ord6')).toEqual([])
      expect(ev.filter((e) => e.type === 'end' && e.navn === 'color' && e.ord === 'ord6').length).toBe(1)
      expect(ev.find((e) => e.type === 'end' && e.navn === 'color' && e.ord === 'ord6')!.farve).toBe(fg)
      // Teksten er HELE tiden den samme (intet holdt tilbage), og til sidst er wrapperne væk.
      expect(r.textEfter).toBe(r.textFoer)
      expect(r.spans).toBe(0)
    } finally { await b.luk() }
  }, 60_000)
})

describe.skipIf(!KOERT)('rytme: Snappy / Normal under identiske betingelser', () => {
  it('måler landing, opacity-, translate- og farvekurve pr. variant', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      const varianter: StreamingTextVariant[] = ['Snappy', 'Normal']
      const ud = await page.evaluate((vs) => {
        const res: Record<string, any> = {}
        const fg = getComputedStyle(document.getElementById('krop')!).color
        for (const [navn, p] of Object.entries(vs)) {
          const out: any = {}
          for (const order of [0, 2]) {
            const el = document.createElement('span')
            el.className = 'streaming-word-tail'
            el.textContent = 'ord'
            el.style.cssText = `--streaming-tail-order:${order};--streaming-tail-duration:${p.duration}ms;--streaming-tail-color-delay:${p.colorDelay}ms;--streaming-tail-part-offset:${p.off}ms;--streaming-tail-opacity-start:${p.k[0]};--streaming-tail-opacity-early:${p.k[1]};--streaming-tail-opacity-mid:${p.k[2]};--streaming-tail-opacity-end:${p.k[3]};--streaming-tail-easing:cubic-bezier(${p.cp})`
            document.getElementById('krop')!.appendChild(el)
            const anims = el.getAnimations()
            anims.forEach((a) => a.pause())
            const land = p.duration + p.colorDelay + order * p.off
            let t90op = -1, maxTy = 0, t90farve = -1, tFoerste = -1
            const parse = (c: string) => c.match(/[\d.]+/g)!.slice(0, 3).map(Number)
            const f = parse(fg)
            const start = [58, 131, 247]
            for (let t = 0; t <= land + 20; t += 4) {
              anims.forEach((a) => { a.currentTime = t })
              const cs = getComputedStyle(el)
              const op = Number(cs.opacity)
              const ty = new DOMMatrix(cs.transform === 'none' ? undefined : cs.transform).m42
              maxTy = Math.max(maxTy, Math.abs(ty))
              if (tFoerste < 0 && op > 0.05) tFoerste = t
              if (t90op < 0 && op >= 0.9) t90op = t
              const c = parse(cs.color)
              const frac = (c[0]! - start[0]!) / (f[0]! - start[0]!)
              if (t90farve < 0 && frac >= 0.9) t90farve = t
            }
            // opacitet ved 25/50/75 % af landing
            const samples = [0.25, 0.5, 0.75].map((q) => { anims.forEach((a) => { a.currentTime = land * q }); return Number(Number(getComputedStyle(el).opacity).toFixed(2)) })
            out[`order${order}`] = { landingMs: land, foersteSynligMs: tFoerste, opacity90Ms: t90op, farve90Ms: t90farve, maxTranslatePx: Number(maxTy.toFixed(2)), opacityVed25_50_75: samples }
            el.remove()
          }
          res[navn] = out
        }
        return res
      }, Object.fromEntries(varianter.map((v) => {
        const p = STREAMING_TEXT_VARIANTS[v]
        return [v, { duration: p.duration, colorDelay: p.colorDelay, off: p.timeOffsetBetweenParts, k: p.opacityKeyframes, cp: p.controlPoints.join(',') }]
      })))
      console.info('[RYTME-MÅLING]', JSON.stringify(ud, null, 1))
      // Snappy = GPT's `c`: 220 + 99 + 2x30. Normal er den laengere skabelon.
      expect(ud.Snappy.order2.landingMs).toBe(379)
      expect(ud.Normal.order2.landingMs).toBeGreaterThan(ud.Snappy.order2.landingMs)
    } finally { await b.luk() }
  }, 60_000)
})
