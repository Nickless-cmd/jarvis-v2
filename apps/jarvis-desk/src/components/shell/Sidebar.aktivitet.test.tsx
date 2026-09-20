import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// Bjørn 20/9-2026: «er det for meget at erstatte de 3 prikker med dit animeret
// ikon?» Svaret blev variant E: typen staar FAST til venstre, aktiviteten
// flytter til HOEJRE.
//
// Grunden til at flytte den er maalt, ikke smagt: i prikkernes gamle plads
// (12px) er Puls-maerkets tre bjaelker 2,3px brede med 0,84px luft — under én
// pixel — og smelter sammen til én klat. Ved 14px kan de laeses.
const state = vi.hoisted(() => ({ workingId: null as string | null }))

const SESSIONER = [
  { id: 'chat-aaa', title: 'kan du kigge på gaten', updated_at: 'x', workspace_kind: null },
  { id: 'chat-ccc', title: 'ret lige den fil', updated_at: 'x', workspace_kind: 'code',
    workspace_root: '/media/projects/jarvis-v2' },
]

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../hooks/useStream', () => ({ useStream: () => ({ workingSessionId: state.workingId }) }))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

const vis = (surface: 'chat' | 'code' = 'chat') =>
  render(<Sidebar surface={surface} onSurface={() => {}} userName="Bjørn" />)

const raekke = (titel: string) => screen.getByText(titel).closest('.session-item') as HTMLElement
const label = (titel: string) =>
  screen.getByText(titel).closest('.session-item-label') as HTMLElement

beforeEach(() => { state.workingId = null })

describe('session-raekkens aktivitets-markoer', () => {
  it('en arbejdende session baerer Puls-maerket — ikke de gamle prikker', () => {
    state.workingId = 'chat-aaa'
    vis('chat')
    expect(raekke('kan du kigge på gaten').querySelector('.jarvis-pulse')).toBeTruthy()
    // Prikkerne er helt væk: ingen regel, ingen markup, ingen keyframes.
    expect(document.querySelector('.session-working')).toBeNull()
  })

  it('en hvilende session baerer intet maerke', () => {
    vis('chat')
    expect(raekke('kan du kigge på gaten').querySelector('.jarvis-pulse')).toBeNull()
  })

  it('maerket staar til HOEJRE for titlen — saa titlen ikke rykker', () => {
    // Det var selve klagen: prikkerne kom og gik FORAN titlen, saa den flyttede
    // sig. Nu har aktiviteten sin egen plads i den anden ende.
    state.workingId = 'chat-aaa'
    vis('chat')
    const born = Array.from(label('kan du kigge på gaten').children).map((b) => b.className)
    expect(born.indexOf('session-titel')).toBeGreaterThanOrEqual(0)
    expect(born.indexOf('session-aktiv')).toBeGreaterThan(born.indexOf('session-titel'))
  })

  it('typen staar FAST — ogsaa naar sessionen hviler', () => {
    vis('code')
    expect(raekke('ret lige den fil').querySelector('.session-mode-icon')).toBeTruthy()
  })

  it('chat og kode har hver sit type-ikon', () => {
    // Foer havde chat intet tag, saa raekken saa tom ud. Nu kan begge kendes.
    const kode = vis('code')
    const kodeIkon = kode.container.querySelector('.session-mode-icon')?.innerHTML
    kode.unmount()
    const chat = vis('chat')
    const chatIkon = chat.container.querySelector('.session-mode-icon')?.innerHTML
    expect(kodeIkon).toBeTruthy()
    expect(chatIkon).toBeTruthy()
    expect(chatIkon).not.toBe(kodeIkon)
  })
})
