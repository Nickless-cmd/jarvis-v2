import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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
