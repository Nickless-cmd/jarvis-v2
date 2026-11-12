import { describe, it, expect, vi, afterEach } from 'vitest'
import { laasLydOpVedFoersteGestus } from './toastLyd'

describe('toastLyd: AudioContext låses op ved første gestus (web/PWA)', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('opretter og resume()r en suspended kontekst ved første klik — kun én gang', () => {
    const resume = vi.fn().mockResolvedValue(undefined)
    const ctor = vi.fn(function (this: { state: string; resume: typeof resume }) {
      this.state = 'suspended'; this.resume = resume
    })
    vi.stubGlobal('AudioContext', ctor)
    ;(window as unknown as { AudioContext: unknown }).AudioContext = ctor
    const fjern = laasLydOpVedFoersteGestus()
    window.dispatchEvent(new Event('pointerdown'))
    window.dispatchEvent(new Event('click'))
    expect(ctor).toHaveBeenCalledTimes(1)
    // modulets egen lytter + denne: begge deler ctx (én instans), resume mindst 1 gang
    expect(resume).toHaveBeenCalled()
    const n = resume.mock.calls.length
    window.dispatchEvent(new Event('click'))
    expect(resume.mock.calls.length).toBe(n) // lytterne er fjernet efter første gestus
    fjern()
  })
})
