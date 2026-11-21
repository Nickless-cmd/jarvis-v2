/**
 * Ordhalen skal leve saa laenge TEKSTEN ruller — ikke saa laenge SSE-socket'en
 * er aaben.
 *
 * MÅLT 20/11-2026 (Bjørn: «Kan det passe farven forsvinder fra ord animationen
 * efter hoveds fold?»): `MarkdownRenderer` fik kun `streaming`, som bliver falsk
 * ved `message_stop`. Paceren fortsætter bagefter (`usePacedBlocks`:
 * `active = live || harVaeretLive`), saa de sidste ord landede EFTER halen var
 * død — uden ankomstfarve. `svarRuller` i `MessageRow` vidste det allerede, men
 * signalet blev aldrig foert ned til tekst-rendereren.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

const TEKST = 'et par ord der lige er landet paa skaermen'

describe('ordhalen foelger teksten, ikke socketen', () => {
  it('farver ordene naar streamen er slut men pacingen ikke er', () => {
    const view = render(<MarkdownRenderer text={TEKST} streaming={false} hale />)
    const ord = view.container.querySelectorAll('.streaming-word-tail')
    expect(ord.length).toBeGreaterThan(0)
  })

  it('farver intet naar baade stream og pacing er faerdige', () => {
    const view = render(<MarkdownRenderer text={TEKST} streaming={false} />)
    expect(view.container.querySelectorAll('.streaming-word-tail')).toHaveLength(0)
  })

  it('halen doer HALE_AFVIKLING_MS efter at pacingen er faerdig', async () => {
    const view = render(<MarkdownRenderer text={TEKST} streaming hale />)
    expect(view.container.querySelectorAll('.streaming-word-tail').length).toBeGreaterThan(0)
    view.rerender(<MarkdownRenderer text={TEKST} streaming={false} hale={false} />)
    // Afviklingen holder den i live et halvt sekund — derefter er den væk.
    expect(view.container.querySelectorAll('.streaming-word-tail').length).toBeGreaterThan(0)
    await new Promise((resolve) => setTimeout(resolve, 600))
    expect(view.container.querySelectorAll('.streaming-word-tail')).toHaveLength(0)
  })
})
