// @vitest-environment node
import { readFile } from 'node:fs/promises'
import { chromium } from 'playwright'
import { describe, expect, it } from 'vitest'

describe.skipIf(process.env.RUN_BROWSER_LAYOUT_MEASUREMENT !== '1')(
  'ordhalens layout-stabilitet i Chromium',
  () => {
    it('holder elementet under teksten på samme position gennem animationen', async () => {
      const css = await readFile(new URL('../styles/chat-reading.css', import.meta.url), 'utf8')
      const executablePath = chromium.executablePath().replace(
        /chromium_headless_shell-([^/]+)\/chrome-headless-shell-linux64\/chrome-headless-shell$/,
        'chromium-$1/chrome-linux64/chrome',
      )
      const browser = await chromium.launch({ headless: true, executablePath })
      try {
        const page = await browser.newPage({ viewport: { width: 640, height: 480 } })
        await page.setContent(`
        <style>${css}</style>
        <main style="width:360px;font:16px/1.5 sans-serif">
          <p id="text">Rolig tekst med <span class="streaming-word-tail" style="--streaming-tail-order:0">animeret </span><span class="streaming-word-tail" style="--streaming-tail-order:1">hale</span></p>
          <section id="under" style="height:48px">Fladen under teksten</section>
        </main>
      `)

        const animationProperties = await page.locator('.streaming-word-tail').first().evaluate((node) => {
          const animations = node.getAnimations()
          return animations.flatMap((animation) => {
            const effect = animation.effect as KeyframeEffect | null
            return (effect?.getKeyframes() ?? []).flatMap((frame) =>
              Object.keys(frame).filter((key) => !['offset', 'easing', 'composite', 'computedOffset'].includes(key)),
            )
          })
        })
        expect(animationProperties.length).toBeGreaterThan(0)
        expect(new Set(animationProperties)).toEqual(new Set(['opacity', 'color', 'transform']))

        const rect = async () => page.locator('#under').evaluate((node) => {
          const { x, y, width, height } = node.getBoundingClientRect()
          return { x, y, width, height }
        })
        const frame0 = await rect()
        await page.waitForTimeout(80)
        const frameN = await rect()
        await page.waitForTimeout(320)
        const after = await rect()

        console.info('[LAYOUT-MÅLING]', { frame0, frameN, after })
        expect(frameN).toEqual(frame0)
        expect(after).toEqual(frame0)
      } finally {
        await browser.close()
      }
    }, 15_000)
  },
)
