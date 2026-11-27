import { chromium } from 'playwright'

export const BASE = process.env.RL_URL ?? 'http://localhost:5299/src/harness/rundelivscyklus.html'

/** Starter browseren og åbner harnessen i den ønskede tilstand. */
export async function aabn(mode) {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 900, height: 1400 } })
  const fejl = []
  page.on('pageerror', (e) => fejl.push(String(e).slice(0, 300)))
  await page.goto(`${BASE}?mode=${mode}&len=${process.env.RL_LEN ?? 4}`, { waitUntil: 'networkidle' })
  await page.waitForSelector('#root > div')
  await page.evaluate(() => {
    // Rå frame-optager: kører inde i siden, så målingen ikke selv forstyrrer timing.
    window.__rec = null
    window.__snap = () => {
      // Geometri måles ALTID (også ved opacity 0) — et usynligt men plads-optagende
      // element er netop det tomrum der skal opdages. `o` er den akkumulerede opacity.
      const vis = (el, geo) => {
        let o = 1
        let skjult = false
        for (let n = el; n && n !== document.body; n = n.parentElement) {
          const cs = getComputedStyle(n)
          o *= parseFloat(cs.opacity)
          if (cs.display === 'none') skjult = true
          // Et klippet barn i en 0-høj overflow-boks (den lukkede fold) er ikke synligt.
          if (n !== el && cs.overflow !== 'visible' && n.getBoundingClientRect().height < 1) skjult = true
        }
        // Opacity måles på selve linjen (`el`), pladsen (højde/top) på den plads den OPTAGER
        // (`geo`) — en usynlig linje i en synlig, høj plads er netop tomrummet.
        const r = (geo ?? el).getBoundingClientRect()
        return { o: skjult ? 0 : Math.round(o * 1000) / 1000, h: skjult ? 0 : Math.round(r.height * 10) / 10, y: Math.round(r.top * 10) / 10 }
      }
      const head = document.querySelector('.rv-tur')
      const tekstEl = '.rv-svar-tekst, .chat-flow-answer-text, .rv-mellem, .chat-flow-segmenter > [data-segment="besvarelse"]'
      const rundeEl = '.rv-arbejdsrunde, .chat-flow-runde'
      const dele = [...document.querySelectorAll(`${tekstEl}, ${rundeEl}`)]
        // en runde-wrapper (.chat-flow-runde/.rv-sen-runde) indeholder .rv-arbejdsrunde — tæl kun yderste
        .filter((el) => !(el.matches('.rv-arbejdsrunde') && el.parentElement.closest('.chat-flow-runde')))
      const items = dele.map((el) => {
        const erRunde = el.matches(rundeEl)
        const label = (el.textContent || '').replace(/\s+/g, ' ').trim()
        const id = erRunde ? (label.match(/R\d|r\d/)?.[0] ?? label.slice(0, 20)) : (label.match(/SYNTESE-[ABC]/)?.[0] ?? label.slice(0, 20))
        const iFold = !!el.closest('.rv-gruppe-ydre, .chat-flow-gruppe-ydre')
        const aktiv = erRunde && !!(el.matches('[data-aktiv-runde]') || el.querySelector('[data-aktiv-runde]'))
        const fader = erRunde && !!(el.matches('[data-pacing-skjult]') || el.querySelector('[data-pacing-skjult]'))
        const maalEl = erRunde ? (el.closest('.rv-sen-runde, .chat-flow-runde') ?? el) : el
        return { slags: erRunde ? 'runde' : 'syntese', id, iFold, aktiv, fader, ...vis(el, maalEl), len: erRunde ? 0 : label.length }
      })
      const pace = items.filter((i) => i.slags === 'syntese').reduce((s, i) => s + i.len, 0)
      return {
        t: Math.round(performance.now()),
        hoved: head ? { aaben: head.getAttribute('aria-expanded'), ...vis(head) } : null,
        items, pace,
      }
    }
    window.__start = () => {
      window.__rec = []
      const tick = () => { if (!window.__rec) return; window.__rec.push(window.__snap()); requestAnimationFrame(tick) }
      requestAnimationFrame(tick)
    }
    window.__stop = () => { const r = window.__rec; window.__rec = null; return r }
  })
  return { browser, page, fejl }
}

export const snap = (page) => page.evaluate(() => window.__snap())

/** Kort tekstlinje af et snapshot: rækkefølge, synlighed og placering. */
export function linje(s) {
  const h = s.hoved ? `hoved[${s.hoved.aaben === 'true' ? 'åben' : 'lukket'} h=${s.hoved.h}]` : 'hoved[-]'
  const its = s.items.map((i) => `${i.id}${i.slags === 'runde' ? (i.iFold ? '~fold' : '') + (i.aktiv ? '*' : '') + (i.fader ? '~' : '') : ''}:${i.o > 0.02 && i.h > 1 ? `y${i.y}/h${i.h}/o${i.o}` : 'skjult'}`).join(' | ')
  return `${h}  pace=${s.pace}  ${its}`
}

/** Rækkefølge af SYNLIGE dele, sorteret efter y. */
export const synlig = (s) => s.items.filter((i) => i.o > 0.02 && i.h > 1).sort((a, b) => a.y - b.y).map((i) => i.id)
