/**
 * Takten i Puls-mærket. Bjørn 20/9-2026: «animationen i systray, header og
 * livenessindikatoren bevæger sig meget langsomt… skru lidt op».
 *
 * Det der kan rådne her, er ikke tallet i sig selv — det er at de TO steder
 * glider fra hinanden. Mærket på skærmen animeres af CSS, bakkens af en timer
 * i hovedprocessen, og bruger man forskellige takter, pulser de to udgaver af
 * det samme mærke i utakt på samme skærm.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const css = readFileSync(join(__dirname, '..', 'components', 'shell', 'JarvisPulse.css'), 'utf8')
const main = readFileSync(join(__dirname, '..', '..', 'electron', 'main.ts'), 'utf8')

const sekunder = (s: string) => Number(/jarvis-puls\s+([\d.]+)s/.exec(s)?.[1])
const bakkeMs = () => Number(/traySpinFrame \+ 1\) % TRAY_ROT_FRAMES; applyTrayImage\(\) }, (\d+)\)/.exec(main)?.[1])
const billeder = () => Number(/TRAY_ROT_FRAMES = (\d+)/.exec(main)?.[1])

describe('Puls-takten', () => {
  it('skærmen pulser hurtigere end de oprindelige fire sekunder', () => {
    expect(sekunder(css)).toBeLessThanOrEqual(2)
    expect(sekunder(css)).toBeGreaterThan(0.5)  // et blink er ikke en puls
  })

  it('bakken og skærmen har SAMME omløbstid', () => {
    const bakke = bakkeMs() * billeder() / 1000
    expect(bakke).toBeCloseTo(sekunder(css), 1)
  })

  it('de tre bjælker er stadig forskudt — ellers er det et blink, ikke en bølge', () => {
    const forskydninger = [...css.matchAll(/animation-delay: -([\d.]+)s/g)].map((m) => Number(m[1]))
    expect(forskydninger).toHaveLength(2)
    const [en, to] = forskydninger as [number, number]
    expect(to).toBeGreaterThan(en)
    // Forskydningen skal følge med takten, ikke stå fast i sekunder.
    expect(to / sekunder(css)).toBeLessThan(0.5)
  })

  it('stille for den der har bedt om mindre bevægelse', () => {
    expect(css).toMatch(/prefers-reduced-motion/)
  })
})
