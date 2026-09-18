/**
 * Handlingsrækken under en besked (Bjørn 18/9-2026: «kopi ikon under hans
 * beskeder virker ikke.. og læs op virker heller ikk»).
 *
 * Begge fejl var TAVSE, og det er det testene her holder fast i. Kopiér satte
 * sit flueben uden at vente på løftet, så knappen kvitterede for en kopiering
 * Electron havde afvist. Læs op kaldte `speak()` på en stemmeliste der var tom
 * og lyste op som om den talte.
 *
 * En knap må gerne fejle. Den må ikke lade som om den lykkedes.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MessageActions } from './MessageActions'

const skriv = vi.fn()
vi.mock('../../lib/udklipsholder', () => ({
  skrivTilUdklipsholder: (...a: unknown[]) => skriv(...a),
}))

const talte: string[] = []
function sætStemmer(antal: number) {
  const synth = {
    getVoices: () => Array.from({ length: antal }, (_, i) => ({ name: `v${i}` })),
    speak: (u: { text: string; onend?: () => void }) => { talte.push(u.text) },
    cancel: () => {},
  }
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true })
  // jsdom har ingen SpeechSynthesisUtterance.
  ;(globalThis as Record<string, unknown>).SpeechSynthesisUtterance =
    class { text: string; lang = ''; constructor(t: string) { this.text = t } }
}

describe('handlingsrækken under en besked', () => {
  beforeEach(() => {
    skriv.mockReset().mockResolvedValue(true)
    talte.length = 0
    sætStemmer(3)
  })
  afterEach(() => vi.useRealTimers())

  it('kopierer beskedens tekst', async () => {
    render(<MessageActions text="hej med dig" />)
    fireEvent.click(screen.getByTitle('Kopiér'))

    await waitFor(() => expect(skriv).toHaveBeenCalledWith('hej med dig'))
  })

  // DET her var fejlen: fluebenet sad uanset hvad udklipsholderen svarede.
  it('kvitterer IKKE når kopieringen blev afvist', async () => {
    skriv.mockResolvedValue(false)
    const { container } = render(<MessageActions text="hej" />)
    fireEvent.click(screen.getByTitle('Kopiér'))

    expect(await screen.findByText('Kunne ikke kopiere')).toBeTruthy()
    expect(container.querySelector('.lucide-check')).toBeNull()
  })

  it('læser op når der ER stemmer', async () => {
    render(<MessageActions text="læs mig" />)
    fireEvent.click(screen.getByTitle('Læs op'))

    await waitFor(() => expect(talte).toEqual(['læs mig']))
  })

  // Uden broen til speech-dispatcher er listen tom. Før lyste knappen op og
  // der skete ingenting — man kunne ikke se forskel på stille og i stykker.
  it('siger til når der ingen stemmer er — i stedet for at tie', async () => {
    sætStemmer(0)
    render(<MessageActions text="læs mig" />)
    fireEvent.click(screen.getByTitle('Læs op'))

    expect(await screen.findByText('Ingen stemmer installeret')).toBeTruthy()
    expect(talte).toEqual([])
  })

  // Pin var ren `useState`: den farvede sig selv og glemte det. Nu kommer
  // sandheden udefra, og knappen findes kun når der ER et sted at gemme.
  it('ingen pin-knap uden et sted at gemme', () => {
    render(<MessageActions text="x" />)
    expect(screen.queryByTitle('Fastgør besked')).toBeNull()
    expect(screen.queryByTitle('Fjern fastgørelse')).toBeNull()
  })

  it('pin-knappen viser den tilstand den FÅR, ikke sin egen', () => {
    const skift = vi.fn()
    const { rerender } = render(<MessageActions text="x" onTogglePin={skift} />)
    fireEvent.click(screen.getByTitle('Fastgør besked'))
    expect(skift).toHaveBeenCalledTimes(1)
    // Knappen skifter IKKE af sig selv — først når ejeren siger den er fastgjort.
    expect(screen.getByTitle('Fastgør besked')).toBeTruthy()

    rerender(<MessageActions text="x" pinned onTogglePin={skift} />)
    expect(screen.getByTitle('Fjern fastgørelse').getAttribute('aria-pressed')).toBe('true')
  })

  it('gensend vises kun når den er givet', () => {
    const { rerender } = render(<MessageActions text="x" />)
    expect(screen.queryByTitle('Send igen')).toBeNull()

    rerender(<MessageActions text="x" onResend={() => {}} />)
    expect(screen.getByTitle('Send igen')).toBeTruthy()
  })
})
