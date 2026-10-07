/**
 * MÅLING, ikke en vagt: hvad koster sidepanelet per stream-opdatering?
 *
 * Bjørn 4/10-2026: «den har svært ved rendering… det flyder ikke… især når
 * jeg har flere sidepaneler åben.»
 *
 * ## Hvad der måles, og hvorfor det måtte skrives om
 *
 * Første udgave drev `rerender()` udefra. Den målte derfor «hvad koster ÉN
 * Sidebar-render» (30 ms — rigtigt nok), men den kunne aldrig se hypotesen:
 * forælderen tvang renderen frem uanset hvad hooket gjorde, så både før og
 * efter rettelsen stod der 21 renders. En test hvor det rigtige og det
 * forkerte svar er identiske måler ingenting — anden gang i dag.
 *
 * Nu drives det RIGTIGE lager (`lavVaerdiLager.saet`) under en rigtig
 * `StreamContext.Provider`, med de ÆGTE hooks. Det er den vej en stream-chunk
 * faktisk går, og det er den eneste opstilling hvor et udsnits-abonnement kan
 * skelnes fra et fuldt.
 *
 * Hans tal, målt i runtime: 566 sessioner i listen, ét svar ~405 frames
 * (62.283 tegn).
 *
 * Rendertiden i jsdom er IKKE Electrons. Den maskin-uafhængige del er
 * ANTALLET af renders; millisekunderne står som størrelsesorden.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, act } from '@testing-library/react'
import { Profiler, type ReactNode } from 'react'
import { lavVaerdiLager } from '../../lib/vaerdiLager'
import { StreamContext, type StreamContextValue } from '../../contexts/StreamContext'

const ANTAL_SESSIONER = 566
const FRAMES_PER_SVAR = 405
const BUDGET_60FPS = 16.7

const SESSIONER = Array.from({ length: ANTAL_SESSIONER }, (_, i) => {
  // Hans faktiske sammensætning, målt: ~278 chat, ~181 autonome, resten kode.
  if (i % 3 === 0) return { id: `auto-heartbeat-${i}`, title: `Autonom · Hjerteslag · ${i}`, updated_at: 'x' }
  if (i % 7 === 0) {
    return { id: `chat-code-${i}`, title: `ret lige den fil ${i}`, updated_at: 'x',
             workspace_kind: 'code', workspace_root: '/media/projects/jarvis-v2' }
  }
  return { id: `chat-${i}`, title: `samtale ${i}`, updated_at: 'x', workspace_kind: null }
})

vi.mock('../../hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: SESSIONER, activeId: null,
    select: vi.fn(), create: vi.fn(), rename: vi.fn(), remove: vi.fn(), newChat: vi.fn(),
    releaseWorkspace: vi.fn(),
  }),
}))
vi.mock('../../hooks/useSettings', () => ({ useSettings: () => ({ settings: null }) }))
vi.mock('../../lib/api', () => ({
  searchSessions: vi.fn().mockResolvedValue([]),
  getActiveRuns: vi.fn().mockResolvedValue([]),
}))

import { Sidebar } from './Sidebar'

/** En stream-tilstand. Kun de felter Sidebar kan røre ved er interessante. */
function tilstand(tekst: string): StreamContextValue {
  // `workingSessionId` står STILLE — det er hele pointen. Det der ændrer sig
  // er svarets tekst, som en chunk gør.
  return { workingSessionId: null, provisionalText: tekst,
           status: 'working' } as unknown as StreamContextValue
}

describe('sidepanelets rendertid per stream-chunk', () => {
  it('rendrer IKKE om naar kun svarets tekst aendrer sig', () => {
    const lager = lavVaerdiLager(tilstand(''))
    const varigheder: number[] = []
    const traeet = (
      <StreamContext.Provider value={lager}>
        <Profiler id="sidebar" onRender={(_i, _f, faktisk) => varigheder.push(faktisk)}>
          <Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />
        </Profiler>
      </StreamContext.Provider>
    )
    render(traeet as ReactNode)
    const montering = varigheder[0] ?? 0
    const efterMontering = varigheder.length

    // 20 chunks gennem den RIGTIGE vej: ny tilstand ind i lageret.
    const N = 20
    for (let i = 0; i < N; i++) {
      act(() => { lager.saet(tilstand(`svar ${i}`)) })
    }
    const renders = varigheder.length - efterMontering
    const sum = varigheder.slice(efterMontering).reduce((a, b) => a + b, 0)

    console.log(`\n  sessioner i listen      : ${ANTAL_SESSIONER}`)
    console.log(`  foerste montering       : ${montering.toFixed(1)} ms`)
    console.log(`  renders ved ${N} chunks     : ${renders}`)
    console.log(`  tid brugt paa dem       : ${sum.toFixed(1)} ms`)
    if (renders > 0) {
      const snit = sum / renders
      console.log(`  snit per chunk          : ${snit.toFixed(2)} ms  (budget ${BUDGET_60FPS} ms)`)
      console.log(`  ét svar (${FRAMES_PER_SVAR} frames)  : ${(snit * FRAMES_PER_SVAR / 1000).toFixed(1)} s ren sidebar-render`)
    }
    console.log('')

    expect(renders).toBe(0)
  })

  it('maaler hvor meget DOM listen holder — det hver render laegges oven paa', () => {
    const lager = lavVaerdiLager(tilstand(''))
    const { container } = render(
      <StreamContext.Provider value={lager}>
        <Sidebar surface="chat" onSurface={() => {}} userName="Bjørn" />
      </StreamContext.Provider> as ReactNode,
    )
    const knuder = container.querySelectorAll('*').length
    console.log(`\n  DOM-knuder i sidepanelet: ${knuder}  (${ANTAL_SESSIONER} sessioner, ingen virtualisering)`)
    console.log('  Dette er hvorfor «flere paneler» gør det vaerre: en React-render')
    console.log('  udloeser et layout/paint over HELE vinduet, og sidepanelets DOM')
    console.log('  ligger der uanset hvad der ellers er aabent.\n')
    // Ingen taerskel — tallet er maalingen. Den ene paastand er at listen
    // IKKE er virtualiseret, for det er forudsaetningen for resten.
    expect(knuder).toBeGreaterThan(ANTAL_SESSIONER)
  })
})
