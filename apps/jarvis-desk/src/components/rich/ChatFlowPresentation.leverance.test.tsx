/**
 * Widgetten maa foerst slippes naar pacen er slut — og pladsen skal vaere
 * reserveret imens, ellers hopper LAYOUTET i stedet for widgetten.
 *
 * Bjørn 29/10-2026: «det bør kun tilføjes naturligt i enden af pacen altså ikk
 * før pacen er slut med en levende forlængning? fade eller sådan noget?»
 *
 * Denne fil styrer `requestAnimationFrame` manuelt, saa pacens ur er
 * deterministisk — samme harness som `ChatFlowPresentation.pacing.test.tsx`.
 */
import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// `AttachmentBlock` (som tegner en filblok) kræver SettingsProvider. Uden
// denne mock kastede HELE testen på provideren, og så målte den intet om
// widgettens ankomst — samme fælde som `AttachmentBlock.test.tsx` undgår.
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' } }),
}))

import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

let rafKo: FrameRequestCallback[] = []
let ur = 0

beforeEach(() => {
  rafKo = []
  ur = 0
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
    rafKo.push(cb)
    return rafKo.length
  })
  vi.stubGlobal('cancelAnimationFrame', () => undefined)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function frame(ms = 16) {
  ur += ms
  const ko = rafKo
  rafKo = []
  act(() => {
    for (const cb of ko) cb(ur)
  })
}

const LANG = 'Dette er et langt svar som serveren leverede i et enkelt hug, og det maa ikke vises paa én gang, for pacen skal rulle det ud over flere sekunder.'

const widget: ContentBlock = {
  type: 'file',
  filename: 'flade.html',
  mime_type: 'text/html; charset=utf-8',
  kilde: 'generated',
  attachment_id: 'att-widget',
}

const svar: ContentBlock = { type: 'text', text: LANG, phase: 'final_answer' }

function widgetSynlig(container: HTMLElement): boolean {
  const node = container.querySelector('[data-leverance="widget"]')
  if (!node) return false
  return node.getAttribute('data-ankomst') !== 'venter'
}

describe('ChatFlowPresentation — widgetten ankommer efter pacen', () => {
  it('holder widgetten tilbage mens pacen ruller svaret ud', () => {
    const view = render(
      <ChatFlowPresentation blocks={[widget, svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-widget"
        paceFinalAnswer />,
    )
    frame()
    frame()
    // Pacen er ikke faerdig: teksten er delvist vist, widgetten er IKKE sluppet.
    const vist = view.container.querySelector('.chat-flow-answer')?.textContent ?? ''
    expect(vist.length).toBeLessThan(LANG.length)
    expect(widgetSynlig(view.container)).toBe(false)
  })

  it('reserverer pladsen mens widgetten venter — layoutet maa ikke hoppe', () => {
    const view = render(
      <ChatFlowPresentation blocks={[widget, svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-widget-plads"
        paceFinalAnswer />,
    )
    frame()
    const plads = view.container.querySelector('[data-leverance-plads]')
    expect(plads).not.toBeNull()
  })

  it('slipper widgetten naar pacen er faerdig', () => {
    const view = render(
      <ChatFlowPresentation blocks={[widget, svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-widget-slip"
        paceFinalAnswer />,
    )
    // Kør uret langt forbi svarets længde.
    for (let i = 0; i < 400; i += 1) frame(50)
    const vist = view.container.querySelector('.chat-flow-answer')?.textContent ?? ''
    expect(vist).toContain(LANG)
    expect(widgetSynlig(view.container)).toBe(true)
  })

  it('en persisteret besked (ingen pace) viser widgetten med det samme', () => {
    const view = render(
      <ChatFlowPresentation blocks={[svar, widget]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="run-historisk" />,
    )
    expect(widgetSynlig(view.container)).toBe(true)
  })
})
