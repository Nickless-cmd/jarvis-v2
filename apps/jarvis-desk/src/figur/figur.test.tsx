import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { boble, boblensNoegle, HANDLING_FOR, UDTRYK_FOR, udtryk } from './figurLogik'
import type { Opmaerksomhed } from '../lib/opmaerksomhed'

const apiFetch = vi.fn()
vi.mock('../lib/api', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { FigurApp } from './FigurApp'

// jsdom har ingen PointerEvent: uden den bliver pointerDown et nøgent Event
// uden `button` og `screenX`, og testen måler så ingenting. MouseEvent bærer
// begge felter — nok til at se klik og træk skilt ad.
if (typeof window.PointerEvent === 'undefined') {
  ;(window as unknown as { PointerEvent: typeof MouseEvent }).PointerEvent = class extends MouseEvent {
    pointerId: number
    constructor(type: string, init: MouseEventInit & { pointerId?: number } = {}) { super(type, init); this.pointerId = init.pointerId ?? 1 }
  } as unknown as typeof MouseEvent
}

const tom = { waiting: 0, failed: 0, review: 0, running: 0 }
const o = (tilstand: Opmaerksomhed['tilstand'], fokus: Partial<Opmaerksomhed['punkter'][0]> | null, antal = tom): Opmaerksomhed => ({
  tilstand, etiket: { idle: 'Intet kræver dig', running: 'Arbejder', waiting: 'Venter på dig', failed: 'Noget gik galt', review: 'Færdig — se svaret' }[tilstand],
  antal, baggrund: 0, indbakke: 0,
  fokus: fokus ? { session_id: 's-1', run_id: 'r-1', tilstand, titel: 'Kæledyret', tekst: '', tid: 1, ...fokus } : null,
  punkter: [],
})

describe('figurens regler', () => {
  it('hver tilstand har en handling — Codex-kortlaegningen', () => {
    expect(HANDLING_FOR).toEqual({ idle: 'hvile', running: 'arbejder', waiting: 'venter', failed: 'fejlede', review: 'faerdig' })
  })

  it('hver handling har et ansigtsudtryk — tilstanden er ikke kun en farve', () => {
    // Fejler hvis nogen tilfoejer en handling uden at give den et ansigt.
    expect(Object.keys(UDTRYK_FOR).sort()).toEqual(
      ['arbejder', 'faerdig', 'fejlede', 'hopper', 'hvile', 'venter', 'vinker'])
    expect(UDTRYK_FOR.hvile).toBe('rolig')
    expect(UDTRYK_FOR.arbejder).toBe('fokus')
    expect(UDTRYK_FOR.venter).toBe('venter')
    expect(UDTRYK_FOR.fejlede).toBe('noed')
    expect(UDTRYK_FOR.faerdig).toBe('glad')
  })

  it('udtryk() svarer til tabellen', () => {
    for (const h of Object.keys(UDTRYK_FOR) as (keyof typeof UDTRYK_FOR)[]) {
      expect(udtryk(h)).toBe(UDTRYK_FOR[h])
    }
  })

  it('ingen boble naar intet kraever dig', () => {
    expect(boble(o('idle', null), null)).toBeNull()
    expect(boble(null, null)).toBeNull()
  })

  it('boblen bærer etiket med antal, titel og hvad han laver', () => {
    const b = boble(o('running', { tekst: 'Tjekker om træet er rent' }, { ...tom, running: 2 }), null)!
    expect(b).toMatchObject({ etiket: 'Arbejder · 2', titel: 'Kæledyret', tekst: 'Tjekker om træet er rent', sessionId: 's-1' })
  })

  it('en afvist boble kommer igen naar der sker noget NYT', () => {
    const f = o('review', { tekst: 'svar' })
    expect(boble(f, boblensNoegle(f))).toBeNull()
    expect(boble(o('review', { run_id: 'r-2' }), boblensNoegle(f))).not.toBeNull()
    expect(boble(o('failed', {}), boblensNoegle(f))).not.toBeNull()
  })
})

describe('FigurApp', () => {
  const bro = {
    config: { get: vi.fn().mockResolvedValue({ apiBaseUrl: 'http://x', authToken: 't' }) },
    figur: {
      traekStart: vi.fn().mockResolvedValue(undefined), traek: vi.fn().mockResolvedValue(undefined),
      traekSlut: vi.fn().mockResolvedValue(undefined), hoejde: vi.fn().mockResolvedValue(undefined),
      aabnSamtale: vi.fn().mockResolvedValue(undefined),
    },
  }
  beforeEach(() => {
    apiFetch.mockReset()
    Object.values(bro.figur).forEach((f) => f.mockClear())
    ;(window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro
  })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('viser hvad han laver, og et klik paa boblen aabner samtalen', async () => {
    apiFetch.mockResolvedValue(o('running', { tekst: 'Tjekker om træet er rent' }))
    render(<FigurApp />)
    expect(await screen.findByText('Tjekker om træet er rent')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Arbejder'))
    expect(bro.figur.aabnSamtale).toHaveBeenCalledWith('s-1')
  })

  it('klik paa figuren faar den til at hoppe — traek flytter den i stedet', async () => {
    apiFetch.mockResolvedValue(o('idle', null))
    render(<FigurApp />)
    const greb = screen.getByTestId('figur')
    fireEvent.pointerDown(greb, { button: 0, screenX: 100, screenY: 100, pointerId: 1 })
    fireEvent.pointerUp(greb, { screenX: 100, screenY: 100, pointerId: 1 })
    expect(greb.querySelector('.h-hopper')).not.toBeNull()
    expect(bro.figur.traekStart).not.toHaveBeenCalled()

    fireEvent.pointerDown(greb, { button: 0, screenX: 100, screenY: 100, pointerId: 1 })
    fireEvent.pointerMove(greb, { screenX: 140, screenY: 100, pointerId: 1 })
    expect(bro.figur.traekStart).toHaveBeenCalledWith(100, 100)
    expect(bro.figur.traek).toHaveBeenCalledWith(140, 100)
    expect(greb.querySelector('.laener-hoejre')).not.toBeNull()
    fireEvent.pointerUp(greb, { screenX: 140, screenY: 100, pointerId: 1 })
    expect(bro.figur.traekSlut).toHaveBeenCalled()
  })

  it('x skjuler boblen til der sker noget nyt', async () => {
    apiFetch.mockResolvedValue(o('review', { tekst: 'Svaret er klar' }))
    render(<FigurApp />)
    await screen.findByText('Svaret er klar')
    fireEvent.click(screen.getByLabelText('Skjul boblen'))
    await waitFor(() => expect(screen.queryByText('Svaret er klar')).toBeNull())
  })

  it('hilser naar den vaagner (Codex: first-awake → waving)', async () => {
    apiFetch.mockResolvedValue(o('idle', null))
    render(<FigurApp />)
    expect(screen.getByText('Her er jeg')).toBeInTheDocument()
    expect(screen.getByTestId('figur').querySelector('.h-vinker')).not.toBeNull()
    await act(async () => {})
  })
})

describe('figurens tre ikoner (Codex)', () => {
  const bro = {
    config: { get: vi.fn().mockResolvedValue({ apiBaseUrl: 'http://x', authToken: 't' }) },
    figur: {
      traekStart: vi.fn(), traek: vi.fn(), traekSlut: vi.fn(), hoejde: vi.fn(),
      aabnSamtale: vi.fn(), stemme: vi.fn().mockResolvedValue(undefined),
    },
  }
  beforeEach(() => { apiFetch.mockReset(); bro.figur.stemme.mockClear(); (window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('stemme-ikonet beder hovedvinduet om samtale-mode', async () => {
    apiFetch.mockResolvedValue(o('running', { tekst: 'x' }))
    render(<FigurApp />)
    fireEvent.click(screen.getByLabelText('Tal med Jarvis'))
    expect(bro.figur.stemme).toHaveBeenCalled()
  })

  it('pak-ikonet skjuler boblen og viser den igen', async () => {
    apiFetch.mockResolvedValue(o('review', { tekst: 'Svaret er klar' }))
    render(<FigurApp />)
    await screen.findByText('Svaret er klar')
    fireEvent.click(screen.getByLabelText('Pak taleboblen væk'))
    expect(screen.queryByText('Svaret er klar')).toBeNull()
    fireEvent.click(screen.getByLabelText('Vis taleboblen'))
    expect(screen.getByText('Svaret er klar')).toBeInTheDocument()
  })

  it('ny-chat-ikonet aabner «Start ny chat»; Escape lukker', async () => {
    apiFetch.mockResolvedValue(o('idle', null))
    render(<FigurApp />)
    fireEvent.click(screen.getByRole('button', { name: 'Start ny chat' }))
    const felt = screen.getByPlaceholderText('Start ny chat')
    fireEvent.change(felt, { target: { value: 'hej' } })
    expect(screen.getByRole('button', { name: 'Send' })).not.toBeDisabled()
    fireEvent.keyDown(felt, { key: 'Escape' })
    expect(screen.queryByPlaceholderText('Start ny chat')).toBeNull()
  })
})

describe('vinduets højde i faste trin (glitch 19/9-2026)', () => {
  it('med boble reserveres plads til dens maksimum — teksten kan skifte uden at vinduet gør', async () => {
    const { maalHoejde, HOEJDE_MED_BOBLE, HOEJDE_HURTIGCHAT } = await import('./figurLogik')
    // 237, 256 og 290 px (målt) giver alle SAMME vindue.
    expect(new Set([237, 256, 290].map((h) => maalHoejde(h, true, false)))).toEqual(new Set([HOEJDE_MED_BOBLE]))
    expect(maalHoejde(174, false, false)).toBe(174)
    expect(maalHoejde(200, true, true)).toBe(HOEJDE_MED_BOBLE + HOEJDE_HURTIGCHAT)
    // Et indhold der ER højere end reserven, får sin højde — intet klippes.
    expect(maalHoejde(333.2, true, false)).toBe(334)
  })
})
