import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatCodeBlock } from './ChatCodeBlock'

/** Vagt mod at chat-kodeblokken mister sprog-tag eller kopiér-knap igen.
 *  1/10-2026: begge manglede, fordi chatten fik sin egen streaming-variant
 *  (1e0de8517) uden at arve dem fra panelernes CodeBlock. */
describe('ChatCodeBlock', () => {
  beforeEach(() => {
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('viser sproget i baren', () => {
    render(<ChatCodeBlock code={'echo hej'} lang="bash" />)
    expect(screen.getByText('bash')).toBeInTheDocument()
  })

  it('falder tilbage til "text" naar sproget er tomt', () => {
    render(<ChatCodeBlock code={'los tekst'} lang="" />)
    expect(screen.getByText('text')).toBeInTheDocument()
  })

  it('farver kode UDEN sprog-tag — tom fence er ikke rå tekst', async () => {
    // 24/10-2026 (Bjørn: «uden sprog tag er den vi har nu og det er lort»):
    // `if (!lang || !code) return` sendte 41 % af alle kodeblokke til rå tekst.
    // Denne vagt kræver FARVEDE spans, ikke bare at etiketten siger «text».
    const { container } = render(<ChatCodeBlock code={'const x = 1 // note'} lang="" />)
    await waitFor(
      () => expect(container.querySelector('pre.chat-shiki')).not.toBeNull(),
      { timeout: 5000 },
    )
    const spans = Array.from(container.querySelectorAll('pre.chat-shiki span span'))
    const farver = new Set(
      spans.map((s) => (s as HTMLElement).style.getPropertyValue('--shiki-dark')).filter(Boolean),
    )
    expect(spans.length).toBeGreaterThan(1)
    expect(farver.size).toBeGreaterThan(1)
  })

  it('viser koden uanset highlight-status', () => {
    render(<ChatCodeBlock code={'const x = 1'} lang="js" />)
    expect(screen.getByText(/const x = 1/)).toBeInTheDocument()
  })

  it('kopiér-knappen kopierer RAÅ kode (ingen sprog-tag, ingen linjenumre)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<ChatCodeBlock code={'line1\nline2'} lang="txt" />)
    const copy = screen.getByRole('button', { name: 'Kopiér kode' })
    expect(copy.querySelector('svg')).toBeInTheDocument()
    await userEvent.click(copy)
    expect(writeText).toHaveBeenCalledWith('line1\nline2')
  })

  it('kvitterer foerst naar teksten naaede udklipsholderen', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    render(<ChatCodeBlock code={'echo hej'} lang="bash" />)
    await userEvent.click(screen.getByRole('button', { name: 'Kopiér kode' }))
    expect(await screen.findByRole('button', { name: 'Kopieret' })).toBeInTheDocument()
  })

  it('siger det hoejt naar kopiering fejler — den kvitterer ikke falsk', async () => {
    // jsdom har hverken en fungerende clipboard eller `execCommand` → begge
    // veje i skrivTilUdklipsholder fejler, og det er netop den ærlige
    // kvittering der testes. Ingen document-stub: den brød render.
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('afvist')) } })
    render(<ChatCodeBlock code={'echo hej'} lang="bash" />)
    await userEvent.click(screen.getByRole('button', { name: /kopiér/i }))
    expect(await screen.findByText('Kunne ikke kopiere')).toBeInTheDocument()
  })
})
