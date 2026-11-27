import { chromium } from 'playwright'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 900, height: 900 } })
await p.goto('http://localhost:5199/src/harness/turhoved.html', { waitUntil: 'networkidle' })
await p.evaluate(() => window.__sætBlokke('med-runde'))
await p.waitForTimeout(800)
console.log(await p.evaluate(() => {
  const r = document.querySelector('.chat-flow-runde')
  if (!r) return { runde: 'findes ikke', html: document.querySelector('.chat-flow')?.className }
  const cs = getComputedStyle(r)
  return {
    levetid: r.getAttribute('data-levetid'),
    hoejde: r.getBoundingClientRect().height,
    maxHeight: cs.maxHeight,
    opacity: cs.opacity,
    display: cs.display,
    tekst: (r.textContent || '').slice(0, 40),
  }
}))
await b.close()
