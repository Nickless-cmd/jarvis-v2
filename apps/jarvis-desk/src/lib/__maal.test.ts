import { it } from 'vitest'
import { delIBlokke } from './markdownBlokke'

const dokument = (antal: number) => Array.from({ length: antal }, (_, i) =>
  `## Del ${i}\n${Array.from({ length: 15 }, (_, j) => `linje ${i}-${j}`).join('\n')}\n\n`,
).join('') + 'slut'

it('maal', () => {
  const stats: Record<number, { min: number; p50: number; p90: number; max: number }> = {}
  for (const n of [300, 600, 1200, 2400, 4800]) {
    const tekst = dokument(n)
    for (let i = 0; i < 8; i++) delIBlokke(tekst)
    const tider: number[] = []
    for (let i = 0; i < 80; i++) {
      const s = performance.now()
      delIBlokke(tekst)
      tider.push(performance.now() - s)
    }
    tider.sort((a, b) => a - b)
    stats[n] = { min: tider[0]!, p50: tider[40]!, p90: tider[72]!, max: tider[79]! }
  }
  for (const n of [300, 600, 1200, 2400, 4800]) {
    const s = stats[n]!
    console.log(`n=${n} min=${s.min.toFixed(4)} p50=${s.p50.toFixed(4)} p90=${s.p90.toFixed(4)} max=${s.max.toFixed(4)}`)
  }
  console.log('--- ratioer (min) ---')
  const b = stats[300]!
  for (const n of [600, 1200, 2400, 4800]) {
    const s = stats[n]!
    console.log(`n=${n}/300: min=${(s.min / b.min).toFixed(3)} p50=${(s.p50 / b.p50).toFixed(3)}`)
  }
  console.log('--- ratioer 1200/300 ---')
  console.log(`min=${(stats[1200]!.min / stats[300]!.min).toFixed(3)} p50=${(stats[1200]!.p50 / stats[300]!.p50).toFixed(3)}`)
  console.log('--- ratioer 4800/300 (16x input) ---')
  console.log(`min=${(stats[4800]!.min / stats[300]!.min).toFixed(3)} p50=${(stats[4800]!.p50 / stats[300]!.p50).toFixed(3)}`)
})
