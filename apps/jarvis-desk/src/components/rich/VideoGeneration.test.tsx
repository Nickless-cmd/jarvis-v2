import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { erVideoVaerktoej, levendeBilledArbejde, BilledArbejdeAnimation } from './ImageGeneration'

/**
 * Animationen mens en video bliver til.
 *
 * ## Hvorfor den er vigtigere end billedernes
 *
 * `pollinations_image` er målt til ~8 s. `pollinations_video` bruger 39 s på
 * pipelinen og har op til **600 s** timeout. Uden et tegn på liv står turen
 * død i op til ti minutter — og det er dér man tror den er hængt og afbryder.
 *
 * Uret er derfor ikke pynt. Det er den eneste oplysning der ændrer sig, og
 * den eneste måde at skelne «arbejder stadig» fra «hængt». Derfor måler
 * testene at det faktisk TÆLLER, ikke bare at det står der.
 */

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('hvornaar den taender', () => {
  it('video-vaerktoejerne kendes', () => {
    expect(erVideoVaerktoej('pollinations_video')).toBe(true)
    expect(erVideoVaerktoej('pollinations_video_edit')).toBe(true)
  })

  it('billed-vaerktoejer er IKKE video', () => {
    for (const n of ['pollinations_image', 'openrouter_image', 'analyze_image', 'remember_this']) {
      expect(erVideoVaerktoej(n)).toBe(false)
    }
  })

  it('et koerende video-kald giver video-arbejde', () => {
    expect(levendeBilledArbejde([{ name: 'pollinations_video', status: 'running' }]))
      .toEqual({ slags: 'video' })
  })

  it('et FAERDIGT kald animerer ikke', () => {
    expect(levendeBilledArbejde([{ name: 'pollinations_video', status: 'done' }])).toBeNull()
  })

  it('video og billede giver hver sit arbejde — ikke det samme', () => {
    const video = levendeBilledArbejde([{ name: 'pollinations_video', status: 'running' }])
    const billede = levendeBilledArbejde([{ name: 'pollinations_image', status: 'running' }])
    expect(video).not.toEqual(billede)
  })
})

describe('selve animationen', () => {
  it('siger hvad der sker', () => {
    render(<BilledArbejdeAnimation arbejde={{ slags: 'video' }} />)
    expect(screen.getByRole('progressbar', { name: /video/i })).toBeInTheDocument()
    expect(screen.getByText(/Genererer video/)).toBeInTheDocument()
  })

  it('uret TAELLER — ellers kan man ikke se forskel paa arbejde og haeng', () => {
    render(<BilledArbejdeAnimation arbejde={{ slags: 'video' }} />)
    expect(screen.getByText('0 s')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(5000) })
    expect(screen.getByText('5 s')).toBeInTheDocument()
  })

  it('over et minut staar der minutter og sekunder', () => {
    render(<BilledArbejdeAnimation arbejde={{ slags: 'video' }} />)
    act(() => { vi.advanceTimersByTime(95_000) })
    expect(screen.getByText('1:35')).toBeInTheDocument()
  })

  it('billed-animationen er UROERT', () => {
    render(<BilledArbejdeAnimation arbejde={{ slags: 'generering' }} />)
    expect(screen.getByRole('progressbar', { name: /billede/i })).toBeInTheDocument()
  })
})
