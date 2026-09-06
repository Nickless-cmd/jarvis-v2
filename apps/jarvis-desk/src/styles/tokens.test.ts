import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const læs = (n: string) => readFileSync(join(__dirname, n), 'utf8')
const tokens = læs('tokens.css')
const app = læs('app.css')

const brugte = (css: string) =>
  new Set([...css.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]))
const definerede = (css: string) =>
  new Set([...css.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)].map((m) => m[1]))

describe('design-tokens', () => {
  // Et var(--x) uden definition er ikke en skønhedsfejl: uden fallback
  // bliver `background: var(--bg)` gennemsigtig og `color: var(--fg)` arvet.
  // Med fallback brænder den en literal ind, som ikke følger temaskift.
  it('bruger ingen tokens der ikke er defineret', () => {
    const def = new Set([...definerede(tokens), ...definerede(app)])
    const manglende = [...brugte(app), ...brugte(tokens)].filter((t) => !def.has(t))
    expect([...new Set(manglende)].sort()).toEqual([])
  })

  // Hvert tema skal kunne stå alene: arver et tema en farve fra det mørke
  // :root, ender fx gul #ffd166 som tekst på hvid baggrund.
  it('definerer de semantiske farver i alle tre temaer', () => {
    const semantiske = ['--accent', '--error-fg', '--warn-fg', '--ok', '--tint', '--fg-0']
    for (const tema of ['light', 'contrast']) {
      const blok = tokens.match(
        new RegExp(`:root\\[data-theme="${tema}"\\]\\s*\\{([\\s\\S]*?)\\n\\}`),
      )
      expect(blok, `tema ${tema} mangler`).toBeTruthy()
      const har = definerede(blok?.[1] ?? "")
      expect(semantiske.filter((t) => !har.has(t)), `tema ${tema}`).toEqual([])
    }
  })

  // Lyst tema arvede før de mørke semantiske farver fra :root — gul #ffd166
  // på hvid gav 1,44:1. Kontrast er målbar, så den måles.
  it('holder de semantiske farver læsbare i lyst tema', () => {
    const m = tokens.match(/:root\[data-theme="light"\]\s*\{([\s\S]*?)\n\}/)
    expect(m).toBeTruthy()
    const blok = m?.[1] ?? ''
    const vaerdi = (navn: string) => {
      const t = blok.match(new RegExp(`${navn}:\\s*(#[0-9a-f]{6})`, 'i'))
      expect(t, `${navn} mangler i lyst tema`).toBeTruthy()
      return t?.[1] ?? '#000000'
    }
    const lum = (h: string) =>
      [1, 3, 5]
        .map((i) => parseInt(h.substr(i, 2), 16) / 255)
        .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
        .reduce((a, c, i) => a + [0.2126, 0.7152, 0.0722][i]! * c, 0)
    const kontrast = (a: string, b: string) => {
      const par = [lum(a), lum(b)].sort((p, q) => q - p)
      return ((par[0] ?? 0) + 0.05) / ((par[1] ?? 0) + 0.05)
    }
    const grund = vaerdi('--bg-0')
    for (const navn of ['--ok', '--error-fg', '--warn-fg']) {
      const forhold = kontrast(vaerdi(navn), grund)
      expect(forhold, `${navn} mod ${grund} gav ${forhold.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5)
    }
  })
})
