/**
 * Tool-linjens bevægelse, 1:1 med Claude Desktop (19/9-2026).
 *
 * Kilde: claude-desktop-unofficial v2.110.0 (`GS`, `BS`, `zS=5` i
 * c3e2391e3-CyTSz9uV.js; keyframes i c7e6c37f6-DBAD18hv.css). Spec:
 * ~/cc-tool-linje-prompt-til-claude.md. Tallene pinnes her fordi «1:1» betyder
 * 1:1 — en «forbedring» af forlægget er fejlen (memory maal_forlaegget).
 */
import { describe, expect, it, vi, afterEach } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { LabelSkift, formatTid } from './LabelSkift'
import { ToolGroupCard } from './ToolGroupCard'

afterEach(() => { vi.useRealTimers() })

describe('klokken i kildens format (BS)', () => {
  it('sekunder, minutter, timer', () => {
    expect(formatTid(12)).toBe('12s')
    expect(formatTid(65)).toBe('1m 5s')
    expect(formatTid(3723)).toBe('1h 2m 3s')
    expect(formatTid(0)).toBe('0s')
  })
})

describe('label-skiftet (GS)', () => {
  const lag = (c: HTMLElement) => ({
    gammel: c.querySelector('[data-testid="ls-gammel"]'),
    spark: c.querySelector('[data-testid="ls-spark"]'),
    ny: c.querySelector('.linje-titel')!,
  })

  it('første tegning animerer intet — en genindlæst tråd skal ikke skifte', () => {
    const { container } = render(<LabelSkift tekst="Læste 3 filer" arbejder={false} />)
    const l = lag(container)
    expect(l.gammel).toBeNull()
    expect(l.spark).toBeNull()
    expect(l.ny.className).not.toMatch(/ls-ind/)
  })

  it('kun tekstskift: gammelt label ud, nyt ind — uden spark', () => {
    const { container, rerender } = render(<LabelSkift tekst="Læser 2 filer" arbejder />)
    rerender(<LabelSkift tekst="Læser 3 filer" arbejder />)
    const l = lag(container)
    expect(l.gammel?.textContent).toBe('Læser 2 filer')
    expect(l.gammel?.className).toMatch(/ls-ud/)
    expect(l.spark).toBeNull()
    expect(l.ny.textContent).toBe('Læser 3 filer')
    expect(l.ny.className).toMatch(/\bls-ind\b/)
  })

  it('arbejdet SLUTTER: sparken, det gamle skubbes 30 px, det nye venter .21 s', () => {
    const { container, rerender } = render(<LabelSkift tekst="Læser 3 filer" arbejder />)
    rerender(<LabelSkift tekst="Læste 3 filer" arbejder={false} />)
    const l = lag(container)
    expect(l.spark).not.toBeNull()
    expect(l.gammel?.className).toMatch(/ls-plads-til-spark/)
    expect(l.ny.className).toMatch(/ls-ind-efter-spark/)
  })

  it('arbejdet STARTER: intet spark og ingen exit — det nye toner bare ind', () => {
    const { container, rerender } = render(<LabelSkift tekst="Klar" arbejder={false} />)
    rerender(<LabelSkift tekst="Læser 1 fil" arbejder />)
    const l = lag(container)
    expect(l.gammel).toBeNull()
    expect(l.spark).toBeNull()
    expect(l.ny.className).toMatch(/\bls-ind\b/)
  })

  it('oprydning på animationens EGET event', () => {
    const { container, rerender } = render(<LabelSkift tekst="a" arbejder />)
    rerender(<LabelSkift tekst="b" arbejder />)
    const g = container.querySelector('[data-testid="ls-gammel"]')!
    // jsdom har ingen AnimationEvent, saa `animationName` kommer ikke med via
    // fireEvent. Eventet bygges her med feltet sat, som browseren goer det.
    const ev = new Event('animationend', { bubbles: true })
    Object.defineProperty(ev, 'animationName', { value: 'ls-fade-ud' })
    act(() => { g.dispatchEvent(ev) })
    expect(container.querySelector('[data-testid="ls-gammel"]')).toBeNull()
  })

  it('og et sikkerhedsnet på 600 ms hvis eventet aldrig kommer', () => {
    vi.useFakeTimers()
    const { container, rerender } = render(<LabelSkift tekst="a" arbejder />)
    rerender(<LabelSkift tekst="b" arbejder={false} />)
    act(() => { vi.advanceTimersByTime(599) })
    expect(container.querySelector('[data-testid="ls-gammel"]')).not.toBeNull()
    act(() => { vi.advanceTimersByTime(2) })
    expect(container.querySelector('[data-testid="ls-gammel"]')).toBeNull()
    expect(container.querySelector('[data-testid="ls-spark"]')).toBeNull()
  })
})

describe('runde-linjen', () => {
  const blok = (status: 'running' | 'done') => ({
    type: 'tool_group' as const, kind: 'round' as const, count: 1,
    tools: [{ type: 'tool_use' as const, id: 't', name: 'bash', input: { command: 'npm test' }, status }],
  })

  it('prikker og caret deler ÉN celle, og careten er én glyf der drejes', () => {
    const { container } = render(<ToolGroupCard density="compact" block={blok('running')} />)
    const celle = screen.getByTestId('tool-status-caret')
    expect(celle.querySelectorAll('.prikker > span')).toHaveLength(3)
    expect(celle.querySelectorAll('.toolgroup-chevron')).toHaveLength(1)
    // Åbn/luk er en drejning (klasse på linjen), ikke et ikon-bytte.
    expect(container.querySelector('.toolgroup')!.className).not.toMatch(/er-aaben/)
    fireEvent.click(container.querySelector('.toolgroup-head')!)
    expect(container.querySelector('.toolgroup')!.className).toMatch(/er-aaben/)
  })

  it('labelen glitrer mens runden arbejder — ikke bagefter', () => {
    const { container, rerender } = render(<ToolGroupCard density="compact" block={blok('running')} />)
    expect(container.querySelector('.linje-titel')!.className).toMatch(/shimmer/)
    rerender(<ToolGroupCard density="compact" block={blok('done')} />)
    expect(container.querySelector('.linje-titel')!.className).not.toMatch(/shimmer/)
  })

  // Bjørn 19/9-2026: «</> i starten af tool result, må gerne komme tilbage».
  // Glyfen står fast, så der er ingen spark at overlevere til.
  it('</> står fast — også når runden er færdig, og uden spark-afgang', () => {
    const { container, rerender } = render(<ToolGroupCard density="compact" block={blok('running')} />)
    rerender(<ToolGroupCard density="compact" block={blok('done')} />)
    expect(container.querySelector('.toolgroup-spark .toolgroup-icon')).not.toBeNull()
    expect(container.querySelector('[data-testid="ls-spark"]')).toBeNull()
  })

  it('uden fast ikon spiller sparken stadig sin afgang', () => {
    const { container, rerender } = render(<LabelSkift tekst="Læser a" arbejder />)
    rerender(<LabelSkift tekst="Læste a" arbejder={false} />)
    expect(container.querySelector('[data-testid="ls-spark"]')).not.toBeNull()
  })
})

// Kildens tal, pinnet mod den CSS der faktisk leveres.
describe('værdierne i app.css er Claude Desktops', () => {
  const css = readFileSync(join(__dirname, '../../styles/app.css'), 'utf8')

  it('entréen: 430 ms backwards, to-faset med 30 %-stop og kurver pr. fase', () => {
    expect(css).toMatch(/\.toolgroup\.er-koerende \{ animation: toolgroup-ind 430ms backwards;/)
    expect(css).toMatch(/30% \{ opacity: 0; filter: blur\(4px\); transform: none; animation-timing-function: ease-out; \}/)
    expect(css).toMatch(/cubic-bezier\(\.22, 1, \.36, 1\)/)
  })

  it('prikkerne: 3,5 px, .26em, 1,9 s cubic-bezier(.4,0,.2,1), 0-8 % usynlige', () => {
    expect(css).toMatch(/\.prikker \{ display: inline-flex; gap: 3\.5px; position: relative; top: \.26em;/)
    expect(css).toMatch(/1\.9s cubic-bezier\(\.4, 0, \.2, 1\) infinite prikke-boelge/)
    expect(css).toMatch(/0%, 8% {3}\{ opacity: 0; transform: translateY\(2px\); \}/)
  })

  it('label-skiftet: .25 s ind, .15 s ud, .21 s efter sparken, .42 s spark', () => {
    expect(css).toMatch(/\.ls-ind \{ animation: \.25s ease-in-out ls-fade-ind; \}/)
    expect(css).toMatch(/\.ls-ud {2}\{ animation: \.15s ease-out forwards ls-fade-ud; \}/)
    expect(css).toMatch(/\.ls-ind-efter-spark \{ animation: \.25s ease-in-out \.21s both ls-fade-ind; \}/)
    expect(css).toMatch(/\.ls-spark-afgang \{ animation: \.42s linear forwards ls-spark-afgang; \}/)
    expect(css).toMatch(/@keyframes ls-spark-afgang \{ 0%, 50% \{ opacity: 1 \} to \{ opacity: 0 \} \}/)
  })

  it('folden: .2 s cubic-bezier(.19,1,.22,1), og indholdet højst 200 px', () => {
    expect(css).toMatch(/grid-template-rows \.2s cubic-bezier\(\.19, 1, \.22, 1\)/)
    expect(css).toMatch(/max-height: 200px; overflow-y: auto;/)
  })

  it('careten er altid synlig hvor hover ikke findes', () => {
    expect(css).toMatch(/@media \(hover: none\) \{\s*\.toolgroup:not\(\.er-koerende\) \.toolgroup-chevron \{ opacity: 1; \}/)
  })

  it('glitteret kører på kildens 2,25 s', () => {
    expect(css).toMatch(/shimmer-sweep 2\.25s linear infinite/)
  })

  it('og linjen «ånder» ikke længere — det gør Claude Desktop ikke', () => {
    expect(css).not.toMatch(/toolgroup-aande/)
  })
})
