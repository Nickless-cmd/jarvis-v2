import { describe, expect, it } from 'vitest'
import { act, render } from '@testing-library/react'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { ContentBlock } from '../../lib/sseProtocol'

let ur = 0
let rafKo: FrameRequestCallback[] = []
globalThis.requestAnimationFrame = ((cb: FrameRequestCallback) => { rafKo.push(cb); return rafKo.length }) as never
globalThis.cancelAnimationFrame = (() => {}) as never
function frame(ms = 16) { ur += ms; const ko = rafKo; rafKo = []; act(() => { for (const cb of ko) cb(ur) }) }

const LANG = 'Dette er et langt svar som serveren leverede i et enkelt hug, og det maa ikke vises paa en gang.'
const widget: ContentBlock = { type: 'file', filename: 'flade.html', mime_type: 'text/html; charset=utf-8', kilde: 'generated', attachment_id: 'att-widget' }
const svar: ContentBlock = { type: 'text', text: LANG, phase: 'final_answer' }

describe('REPRO — widget dublet', () => {
  it('widgetten maa kun optraede ÉN gang efter pacen', () => {
    const view = render(
      <ChatFlowPresentation blocks={[widget, svar]} mode="living" density="compact"
        streaming={false} status="done" finalAnswerStarted runId="repro-1" paceFinalAnswer />,
    )
    for (let i = 0; i < 400; i += 1) frame(50)
    const html = view.container.innerHTML
    const antal = (html.match(/flade\.html/g) || []).length
    const iSvar = (view.container.querySelector('.chat-flow-answer')?.innerHTML.match(/flade\.html/g) || []).length
    const iLev = (view.container.querySelector('[data-leverance="widget"]')?.innerHTML.match(/flade\.html/g) || []).length
    console.log('FORELKOMSTER i alt:', antal, '| i .chat-flow-answer:', iSvar, '| i leverance-blok:', iLev)
    expect(antal).toBe(1)
  })
})
