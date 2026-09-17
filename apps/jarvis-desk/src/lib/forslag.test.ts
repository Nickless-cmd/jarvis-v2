import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  MAKS_UDKAST, MIN_TEGN, boerSpoerge, hentForslag, saetSammen,
} from './forslag'
import type { ApiConfig } from './api'

const CFG: ApiConfig = { apiBaseUrl: 'http://x', authToken: 'tok' }

afterEach(() => { vi.unstubAllGlobals() })

describe('boerSpoerge', () => {
  it('afviser et udkast under minimumslængden', () => {
    expect(boerSpoerge('kort')).toBe(false)
    expect(boerSpoerge('a'.repeat(MIN_TEGN - 1))).toBe(false)
  })

  it('spørger ved præcis minimumslængden', () => {
    expect(boerSpoerge('a'.repeat(MIN_TEGN))).toBe(true)
  })

  it('afviser når sætningen er færdig — at foreslå videre er at tale i munden', () => {
    expect(boerSpoerge('det her er færdigt.')).toBe(false)
    expect(boerSpoerge('er det her færdigt?')).toBe(false)
    expect(boerSpoerge('her er noget:')).toBe(false)
    expect(boerSpoerge('færdig.  ')).toBe(false)  // luft efter tegnet tæller ikke
  })

  it('afviser et helt afsnit — dér ved man hvad man vil', () => {
    expect(boerSpoerge('a'.repeat(MAKS_UDKAST + 1))).toBe(false)
  })

  it('spørger på en åben sætning midt i skrivningen', () => {
    expect(boerSpoerge('hvordan virker den')).toBe(true)
  })

  it('tåler tom og manglende tekst', () => {
    expect(boerSpoerge('')).toBe(false)
    expect(boerSpoerge('   ')).toBe(false)
  })
})

describe('saetSammen', () => {
  it('hæfter forslaget på udkastet', () => {
    expect(saetSammen('hvordan virker', ' den her')).toBe('hvordan virker den her')
  })

  it('giver ikke to mellemrum når udkastet selv slutter med et', () => {
    expect(saetSammen('hvordan virker ', ' den her')).toBe('hvordan virker den her')
  })

  it('returnerer udkastet uændret ved et tomt forslag', () => {
    expect(saetSammen('hvordan virker', '')).toBe('hvordan virker')
  })
})

describe('hentForslag', () => {
  it('returnerer forslaget fra serveren', async () => {
    const f = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ forslag: ' den her' }),
    })
    vi.stubGlobal('fetch', f)
    expect(await hentForslag(CFG, 'hvordan virker')).toBe(' den her')
    expect(f.mock.calls[0]?.[0]).toBe('http://x/composer/suggest')
  })

  it('spørger slet ikke når udkastet ikke indbyder til det', async () => {
    const f = vi.fn()
    vi.stubGlobal('fetch', f)
    expect(await hentForslag(CFG, 'kort')).toBe('')
    expect(f).not.toHaveBeenCalled()
  })

  it('giver tom streng ved en fejlkode — komponisten skal kunne skrives i', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) }))
    expect(await hentForslag(CFG, 'hvordan virker')).toBe('')
  })

  it('giver tom streng når kaldet fejler', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('nede')))
    expect(await hentForslag(CFG, 'hvordan virker')).toBe('')
  })

  it('giver tom streng hvis serveren svarer med noget andet end en streng', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ forslag: 42 }),
    }))
    expect(await hentForslag(CFG, 'hvordan virker')).toBe('')
  })

  it('sender udkastet med — og uden Authorization når der ikke er noget token', async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ forslag: '' }) })
    vi.stubGlobal('fetch', f)
    await hentForslag({ apiBaseUrl: 'http://x', authToken: null }, 'hvordan virker')
    const init = (f.mock.calls[0]?.[1] ?? {}) as RequestInit
    expect(JSON.parse(String(init.body))).toEqual({ udkast: 'hvordan virker' })
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined()
  })
})
