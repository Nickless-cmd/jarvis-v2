/**
 * FLADENS ANKOMST — placeholder uden for paceren, og en fade der kun fyrer én gang.
 *
 * To krav, begge bindende (Bjørn 29/10-2026):
 *
 *   1. `MarkdownRenderer.pre` skal have en gren for en `jarvis-ui`-fence UDEN
 *      gyldig spec. Persisterede beskeder, replay og genindlæsning går ALDRIG
 *      gennem paceren — så de rammer aldrig springet, og uden denne gren ville
 *      de vise rå JSON i en kodeboks.
 *
 *   2. Fade-animationen skal være bundet til en `key` der kun skifter når
 *      fladen er NY. Skete det ved hver re-render, ville fladen danse hver gang
 *      paceren rykker ét tegn i prosaen ovenover — værre end kodeboksen.
 *
 * Testen måler mekanismen der bærer animationen (remount ved ny key), ikke
 * CSS'en: jsdom kører ingen animationer, så en test der spurgte «kørte
 * animationen?» ville svare nej uanset hvad og bevise intet.
 */
import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'

// Klientloggen skriver til disk/IPC. Den er ikke emnet her, og et kald pr.
// render ville gøre testen afhængig af et miljø den ikke har.
vi.mock('../../lib/fladeLog', () => ({ logFlade: () => undefined }))

import { MarkdownRenderer } from './MarkdownRenderer'
import { NativeRichBlock } from './NativeRichBlock'

const SPEC = JSON.stringify({ type: 'callout', tone: 'info', title: 'T', body: 'B' })
const SPEC2 = JSON.stringify({ type: 'callout', tone: 'warning', title: 'U', body: 'C' })

describe('fladens ankomst', () => {
  it('en jarvis-ui-fence uden gyldig spec viser placeholder — ALDRIG en kodeboks med rå JSON', () => {
    // Uafsluttet/afkortet JSON, præcis som den ser ud midt i en stream.
    const md = 'Her er den:\n\n```jarvis-ui\n{"type":"callout","tit\n```\n\nEfter.'
    const view = render(<MarkdownRenderer text={md} streaming />)

    expect(view.container.querySelector('pre')).toBeNull()
    expect(view.container.querySelector('.flade-pending')).not.toBeNull()
    // Den rå JSON må ikke lække ud i teksten.
    expect(view.container.textContent).not.toContain('"type"')
  })

  it('ankomst-laget er bundet til fladens INDHOLD — ikke til re-render', () => {
    const view = render(<NativeRichBlock code={SPEC} />)
    const foerste = view.container.querySelector('.flade-ankomst')
    expect(foerste).not.toBeNull()

    // Samme flade igen (fx paceren rykker et tegn i prosaen ovenover):
    // noden skal være DEN SAMME, ellers fyrer animationen på ny.
    view.rerender(<NativeRichBlock code={SPEC} />)
    expect(view.container.querySelector('.flade-ankomst')).toBe(foerste)

    // En NY flade skal derimod give en ny node — og dermed én ny fade.
    view.rerender(<NativeRichBlock code={SPEC2} />)
    expect(view.container.querySelector('.flade-ankomst')).not.toBe(foerste)
  })

  it('REGRESSION: en gyldig flade rendres stadig som flade, ikke som placeholder', () => {
    const md = `Her:\n\n\`\`\`jarvis-ui\n${SPEC}\n\`\`\`\n\nEfter.`
    const view = render(<MarkdownRenderer text={md} streaming={false} />)
    expect(view.container.querySelector('.flade-pending')).toBeNull()
    expect(view.container.textContent).toContain('B')
  })
})
