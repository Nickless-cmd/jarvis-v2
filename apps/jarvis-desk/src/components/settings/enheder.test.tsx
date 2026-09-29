import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import * as enh from '../../lib/enheder'
import { EnhederSection } from './EnhederSection'
import { startStream } from '../../lib/streamClient'

/** Enheder efter Codex' fjernstyring (19/9-2026). */
const config = { apiBaseUrl: 'http://x', authToken: 't' }
const overblik = (over: Partial<enh.EnhedsOverblik> = {}): enh.EnhedsOverblik => ({
  enheder: [{ id: 'e1', type: 'telefon', navn: 'Bjørns Pixel', platform: 'android', oprettet: 1, sidst_set: 0 }],
  kraev_aktivt: false,
  denne: { type: 'computer', tilfoejet: true, kode_tilladt: true },
  ...over,
})

beforeEach(() => { vi.restoreAllMocks() })

describe('EnhederSection', () => {
  it('sikkerhedsmeddelelsen og «Tillad» kommer FØR QR — og kræver totrinskoden', async () => {
    vi.spyOn(enh, 'hentEnheder').mockResolvedValue({ ok: true, data: overblik() })
    const opret = vi.spyOn(enh, 'opretParring').mockResolvedValue({ ok: false, fejl: 'Forkert totrinskode.' })
    render(<EnhederSection config={config} ejer />)
    fireEvent.click(await screen.findByRole('button', { name: 'Tilføj telefon' }))
    expect(screen.getByText(/Tilføj kun telefoner du selv ejer/)).toBeInTheDocument()
    const knap = screen.getByRole('button', { name: 'Tillad og vis kode' })
    expect(knap).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Totrinskode'), { target: { value: '123456' } })
    fireEvent.click(knap)
    await waitFor(() => expect(opret).toHaveBeenCalledWith(config, '123456'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Forkert totrinskode.')
    expect(screen.queryByAltText('QR-kode til parring')).toBeNull()
  })

  it('fjern kræver et ekstra klik og siger hvad der sker', async () => {
    vi.spyOn(enh, 'hentEnheder').mockResolvedValue({ ok: true, data: overblik() })
    const fjern = vi.spyOn(enh, 'fjernEnhed').mockResolvedValue({ ok: true, data: { ok: true } })
    render(<EnhederSection config={config} ejer={false} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Fjern Bjørns Pixel' }))
    expect(screen.getByText(/mister al adgang med det samme/)).toBeInTheDocument()
    expect(fjern).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Fjern' }))
    await waitFor(() => expect(fjern).toHaveBeenCalledWith(config, 'e1'))
  })

  it('reglen vises kun for ejeren', async () => {
    vi.spyOn(enh, 'hentEnheder').mockResolvedValue({ ok: true, data: overblik() })
    const { unmount } = render(<EnhederSection config={config} ejer={false} />)
    await screen.findByText('Bjørns Pixel')
    expect(screen.queryByText(/Code mode kræver en tilføjet enhed/)).toBeNull()
    unmount()
    render(<EnhederSection config={config} ejer />)
    expect(await screen.findByText(/Code mode kræver en tilføjet enhed/)).toBeInTheDocument()
  })

  it('en computer der ikke er tilføjet, kan tilføjes her', async () => {
    vi.spyOn(enh, 'hentEnheder').mockResolvedValue({ ok: true, data: overblik({ kraev_aktivt: true, denne: { type: 'computer', tilfoejet: false, kode_tilladt: false } }) })
    render(<EnhederSection config={config} ejer />)
    expect(await screen.findByText(/code mode er lukket her/)).toBeInTheDocument()
  })
})

describe('streamen og en 403 med forklaring', () => {
  it('bliver serverens forklaring — ikke «log ind igen»', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Code mode kræver at denne enhed er tilføjet i desk.' }), { status: 403 },
    )))
    const fejl = await new Promise<{ category: string; message: string }>((resolve) => {
      startStream(
        { apiBaseUrl: 'http://t', authToken: 't', sessionId: 's', message: 'hi' },
        { onEvent: () => {}, onError: (e) => resolve(e as never), onComplete: () => resolve({ category: 'ingen', message: '' }) },
      )
    })
    expect(fejl.category).toBe('forbidden')
    expect(fejl.message).toMatch(/tilføjet i desk/)
  })
})

// ── Knappen skal findes for den klient der har brug for den (29/9-2026) ─────
//
// Blokken stod bag `denne.type === 'computer'`, og serveren udleder typen af
// `app_id`-claim'et. Et token uden claim giver «ukendt» — altsaa forsvandt
// knappen praecis for den klient der ikke maatte bruge code mode.
//
// Samtidig stod computeren i LISTEN som tilfoejet, for den kommer fra
// registret og ikke fra tokenet. Panelet sagde ét, serveren et andet.
//
// Bjoern: «i appen stod den stadig tilfoejet, saa jeg slog reglen fra og saa
// svarede han». Reglen blev slukket fordi der ikke var nogen vej ind.

describe('registrering tilbydes naar klienten ikke maa bruge code mode', () => {
  const vis = async (denne: enh.EnhedsOverblik['denne'], kraev = true) => {
    vi.spyOn(enh, 'hentEnheder').mockResolvedValue({
      ok: true, data: overblik({ denne, kraev_aktivt: kraev }),
    })
    render(<EnhederSection config={config} ejer />)
    await waitFor(() => expect(enh.hentEnheder).toHaveBeenCalled())
  }
  const knap = () => screen.queryByRole('button', { name: /Tilføj denne computer/i })

  it('en UKENDT klient faar knappen — det var hans sag', async () => {
    await vis({ type: 'ukendt', tilfoejet: false, kode_tilladt: false })
    expect(knap()).not.toBeNull()
  })

  it('og en forklaring paa hvorfor den staar der selvom computeren er i listen', async () => {
    await vis({ type: 'ukendt', tilfoejet: false, kode_tilladt: false })
    expect(screen.getByText(/tilfoej den igen/i)).toBeInTheDocument()
  })

  it('en genkendt men ikke-tilfoejet computer faar den stadig', async () => {
    await vis({ type: 'computer', tilfoejet: false, kode_tilladt: false })
    expect(knap()).not.toBeNull()
  })

  it('en TILFOEJET computer faar den ikke — intet at gentage', async () => {
    await vis({ type: 'computer', tilfoejet: true, kode_tilladt: true })
    expect(knap()).toBeNull()
  })

  it('en TELEFON faar den aldrig — den har sin egen vej (parring)', async () => {
    await vis({ type: 'telefon', tilfoejet: false, kode_tilladt: false })
    expect(knap()).toBeNull()
  })
})
