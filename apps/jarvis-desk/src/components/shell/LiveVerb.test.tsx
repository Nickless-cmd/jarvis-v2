/**
 * Husets eget liveness-mærke: tre streger der ånder (9/11-2026).
 *
 * Bjørn: «vores er 3 levende bouncing streger… husets ikon», efter at have peget
 * på Claude Codes fire bolde som det der faktisk føles levende. Forskellen der
 * beskyttes her er ikke antallet — den er at vores gamle prikker gik til
 * opacity 0 i hver cyklus og derfor BLINKEDE, mens CC's aldrig slukkes.
 * Sætter nogen gulvet tilbage til nul, eller fjerner den strukturelle
 * bevægelse, fejler testen: så er vi tilbage ved det han klagede over.
 */
import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { LiveVerb } from './LiveVerb'

const css = readFileSync(join(__dirname, '../../styles/app.css'), 'utf8')
const keyframes = css.match(/@keyframes streg-aande \{([\s\S]*?)\n\}/)?.[1] ?? ''

describe('LiveVerb — husets mærke, tre streger', () => {
  it('rendrer præcis tre streger og ingen prikker', () => {
    const { container } = render(<LiveVerb text="læser" />)
    expect(container.querySelectorAll('.live-streger > span')).toHaveLength(3)
    expect(container.querySelector('.live-dots')).toBeNull()
  })

  it('slukker aldrig: opacity-gulvet er over nul i hver keyframe', () => {
    expect(keyframes).not.toBe('')
    const vaerdier = [...keyframes.matchAll(/opacity: ([\d.]+)/g)].map((m) => Number(m[1]))
    expect(vaerdier.length).toBeGreaterThan(0)
    expect(Math.min(...vaerdier)).toBeGreaterThan(0)
  })

  it('bevæger sig strukturelt — scaleY, ikke kun lysstyrke', () => {
    expect(keyframes).toMatch(/transform: scaleY\(/)
  })

  it('ruller allerede ved første frame: negativ delay på begge følgende streger', () => {
    expect(css).toMatch(/\.live-streger span:nth-child\(2\) \{ animation-delay: -\.16s; \}/)
    expect(css).toMatch(/\.live-streger span:nth-child\(3\) \{ animation-delay: -\.32s; \}/)
  })

  it('respekterer reduced motion', () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\) \{\n  \.live-streger span \{ animation: none;/)
  })

  it('lader tool-result-prikkerne være: prikke-boelge er urørt', () => {
    expect(css).toMatch(/1\.9s cubic-bezier\(\.4, 0, \.2, 1\) infinite prikke-boelge/)
  })
})
