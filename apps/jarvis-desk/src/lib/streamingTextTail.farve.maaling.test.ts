// @vitest-environment node
/**
 * Ordhalens farve, genstarter, layout og reduced-motion — målt i Chromium.
 *
 * Gates som de øvrige målinger: springes over uden RUN_BROWSER_LAYOUT_MEASUREMENT=1.
 *
 * FØR (20/11-2026, mørkt tema): slutfarven var hårdkodet #8f8f8f mod brødtekstens
 * var(--fg-1) = rgb(240,239,236); og hvert ord animerede op til TRE gange fordi
 * react-markdown nøgler børn `<tagName>-<antal>` og halen af tre rykkede positioner.
 */
import { describe, expect, it } from 'vitest'
import { aabnBaenk, installerMaaler, ordTekst } from './streamingTextTail.baenk'

const KOERT = process.env.RUN_BROWSER_LAYOUT_MEASUREMENT === '1'

type Prove = { t: number; ord: string; color: string; opacity: number; x: number; y: number; w: number; h: number; klasse: string }
type Ev = { t: number; type: string; navn: string; ord: string; farve: string; opacity: number }

async function stream(page: import('playwright').Page, ord: number, afstandMs: number) {
  for (let i = 1; i <= ord; i++) {
    await page.evaluate((t) => (window as any).__saetTekst(t), ordTekst(i))
    await page.waitForTimeout(afstandMs)
  }
  await page.waitForTimeout(900)
}
const hent = async (page: import('playwright').Page) => ({
  ev: (await page.evaluate(() => (window as any).__ev)) as Ev[],
  prover: (await page.evaluate(() => (window as any).__prover)) as Prove[],
})

describe.skipIf(!KOERT)('ordhalens farve — slutter i brødtekstens farve uden spring', () => {
  for (const theme of ['dark', 'light'] as const) {
    it(`${theme}: før/under/efter, ved halens udgang og ved rerender`, async () => {
      const b = await aabnBaenk({ theme })
      try {
        const { page } = b
        const fg = await page.evaluate(() => getComputedStyle(document.getElementById('krop')!).color)
        await installerMaaler(page)
        await stream(page, 10, 400)
        const { ev, prover } = await hent(page)
        expect(b.fejl).toEqual([])

        for (let n = 1; n <= 10; n++) {
          const ord = `ord${n}`
          const mine = prover.filter((p) => p.ord === ord)
          const sidste = mine[mine.length - 1]!
          // EFTER: præcis brødtekstens farve — ikke «næsten».
          expect(sidste.color, `${theme} ${ord} slutfarve`).toBe(fg)
          // FØR: ordet starter i accentblå (ikke i slutfarven), så overgangen er reel.
          expect(mine[0]!.color, `${theme} ${ord} startfarve`).not.toBe(fg)
          // Farven må kun bevæge sig ÉN vej: når ordet først har ramt fg, forlader det den aldrig igen.
          const foersteFg = mine.findIndex((p) => p.color === fg)
          expect(foersteFg, `${theme} ${ord} når fg`).toBeGreaterThanOrEqual(0)
          expect(mine.slice(foersteFg).every((p) => p.color === fg), `${theme} ${ord} farvespring efter landing`).toBe(true)
        }
        // IDET ordet forlader halen (animationend → klassen slippes): farven i capture
        // er allerede fg, og den efterfølgende prøve er identisk. Intet spring.
        const slut = ev.filter((e) => e.type === 'end' && e.navn === 'color')
        expect(slut.length).toBe(10)
        for (const e of slut) expect(e.farve, `${theme} ${e.ord} ved udgang`).toBe(fg)
        // RERENDER: samme tekst igen + ét nyt ord må hverken starte animationer forfra
        // eller flytte farven på de færdige ord.
        const foer = (await hent(page)).ev.filter((e) => e.type === 'start').length
        await page.evaluate((t) => (window as any).__saetTekst(t), ordTekst(10))
        await page.waitForTimeout(300)
        const efter = (await hent(page)).ev.filter((e) => e.type === 'start').length
        expect(efter).toBe(foer)
        console.info('[FARVE-MÅLING]', { theme, fg, startFarve: prover.find((p) => p.ord === 'ord3')?.color, slutFarve: fg })
      } finally { await b.luk() }
    }, 60_000)
  }
})

describe.skipIf(!KOERT)('ordhalens genstarter og dobbeltanimation', () => {
  it('hvert ord starter præcis én opacity- og én color-animation, alle CSS-drevne, ingen cancel', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      await installerMaaler(page)
      const N = 14
      await stream(page, N, 150)
      const { ev } = await hent(page)
      for (let n = 1; n <= N; n++) {
        const mine = ev.filter((e) => e.ord === `ord${n}`)
        expect(mine.filter((e) => e.type === 'start' && e.navn === 'opacity').length, `ord${n} opacity-starter`).toBe(1)
        expect(mine.filter((e) => e.type === 'start' && e.navn === 'color').length, `ord${n} color-starter`).toBe(1)
      }
      expect(ev.filter((e) => e.type === 'cancel')).toEqual([])
      // Dobbeltanimation CSS+JS: under en kørende animation er ALLE animationer på ordet CSSAnimation.
      await page.evaluate((t) => (window as any).__saetTekst(t), ordTekst(N + 1))
      await page.waitForTimeout(60)
      const kilder = await page.evaluate(() =>
        [...document.querySelectorAll('.streaming-word-tail')].flatMap((el) =>
          el.getAnimations().map((a) => (a instanceof CSSAnimation ? 'css' : 'js'))))
      expect(kilder.length).toBeGreaterThan(0)
      expect(new Set(kilder)).toEqual(new Set(['css']))
      expect(kilder.length).toBeLessThanOrEqual(2)
    } finally { await b.luk() }
  }, 60_000)

  it('et ord der forlader «de sidste tre» midt i sin animation kappes ikke (hurtig streaming, 40 ms/ord)', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      await installerMaaler(page)
      await stream(page, 12, 40)
      const { ev, prover } = await hent(page)
      expect(ev.filter((e) => e.type === 'cancel')).toEqual([])
      for (let n = 1; n <= 12; n++) {
        const o = prover.filter((p) => p.ord === `ord${n}`).map((p) => p.opacity)
        for (let i = 1; i < o.length; i++) expect(o[i]!, `ord${n} opacity må ikke falde/hoppe tilbage`).toBeGreaterThanOrEqual(o[i - 1]! - 1e-6)
      }
      // Hvert ord når en afslutning på sin color-animation (ingen afbrudt hale).
      expect(ev.filter((e) => e.type === 'end' && e.navn === 'color').length).toBe(12)
    } finally { await b.luk() }
  }, 60_000)
})

describe.skipIf(!KOERT)('ordhalens layout og reduced-motion', () => {
  it('ordets boks (x, y, bredde, højde) er uændret gennem animationen', async () => {
    const b = await aabnBaenk({ theme: 'dark' })
    try {
      const { page } = b
      await installerMaaler(page)
      await stream(page, 8, 300)
      const { prover } = await hent(page)
      for (let n = 1; n <= 8; n++) {
        const mine = prover.filter((p) => p.ord === `ord${n}`)
        const ref = mine[mine.length - 1]!
        for (const p of mine) {
          expect(Math.abs(p.x - ref.x), `ord${n} x`).toBeLessThan(0.01)
          expect(Math.abs(p.y - ref.y), `ord${n} y`).toBeLessThan(0.01)
          // Bredden regnes først når næste ord er ankommet: et efterstillet mellemrum
          // kollapser, så bredden vokser med TEKSTEN (ikke med animationen).
          const naeste = prover.find((q) => q.ord === `ord${n + 1}`)
          if (naeste && p.t >= naeste.t) expect(Math.abs(p.w - ref.w), `ord${n} bredde`).toBeLessThan(0.01)
          expect(Math.abs(p.h - ref.h), `ord${n} højde`).toBeLessThan(0.01)
        }
      }
    } finally { await b.luk() }
  }, 60_000)

  it('prefers-reduced-motion: ingen animationer, fuld opacity, brødtekstens farve', async () => {
    const b = await aabnBaenk({ theme: 'dark', reducedMotion: true })
    try {
      const { page } = b
      await installerMaaler(page)
      await stream(page, 5, 150)
      const { ev, prover } = await hent(page)
      const fg = await page.evaluate(() => getComputedStyle(document.getElementById('krop')!).color)
      expect(ev.filter((e) => e.type === 'start')).toEqual([])
      expect(prover.length).toBeGreaterThan(0)
      for (const p of prover) { expect(p.opacity).toBe(1); expect(p.color).toBe(fg) }
    } finally { await b.luk() }
  }, 60_000)
})
