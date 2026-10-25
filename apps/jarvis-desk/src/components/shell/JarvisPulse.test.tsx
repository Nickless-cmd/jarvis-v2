/**
 * Header-mærket skal følge brugerens farvepalette.
 *
 * Bjørn 25/10-2026: «animationen i header bør skifte farve til den valgte
 * farve-palette brugeren har valgt … det gør alt andet».
 *
 * Målt før rettelsen: `.jarvis-pulse` havde `color: #49c9b8` hardkodet, mens
 * resten af fladen læser `--accent` fra tokens.css' seks accentfamilier
 * (gron, teal, lilla, rav, bla, rose). Mærket var altså det ENESTE i headeren
 * der ikke flyttede sig når man skiftede palette.
 *
 * Testen læser CSS-filen direkte. Det er den ærlige måling her: jsdom anvender
 * ikke eksterne stylesheets, så en render-test ville måle intet — den ville
 * være grøn uanset hvilken farve der stod i filen.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const css = readFileSync(join(__dirname, 'JarvisPulse.css'), 'utf8')

describe('header-mærkets farve', () => {
  it('binder farven til --accent i stedet for en hardkodet teal', () => {
    expect(css).toMatch(/\.jarvis-pulse \{[^}]*color: var\(--accent, #49c9b8\)/)
  })

  it('falder ikke tilbage til den rene teal-tildeling', () => {
    // Den gamle form bandt mærket til teal uanset palette. Kommer den igen,
    // står headeren og resten af fladen i to forskellige farver.
    expect(css).not.toMatch(/\.jarvis-pulse \{[^}]*color: #49c9b8/)
  })

  it('beholder fejlfarven som sit eget semantiske signal', () => {
    // Fejl er ikke en palette-ting — den skal blive rød uanset accentvalg.
    expect(css).toMatch(/\.jarvis-pulse\.is-error \{ color: var\(--error-fg/)
  })
})
