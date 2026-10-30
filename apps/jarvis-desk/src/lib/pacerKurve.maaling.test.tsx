/**
 * MÅLING, ikke en vagt: HVORNÅR kommer teksten — ikke bare hvor længe.
 *
 * Bjørn 30/10-2026: «Pacen løber for stærkt». Det er svært at forene med at
 * 2000 tegn tager 7,2 s. Forklaringen kan kun ligge i FORDELINGEN: hvis
 * størstedelen af teksten lander i det første sekund og resten haler bagefter,
 * føles det som et skvulp — ikke som en jævn udrulning. Gennemsnittet skjuler
 * det.
 *
 * Derfor måles her gennem den ÆGTE hook (`useChatPacedBlocks`), frame for
 * frame, med det samme simulerede ur som de øvrige pacer-tests bruger.
 *
 * En tidligere udgave af denne måling genskabte `naesteRate` i hånden og gav
 * 100 % på 0,5 s — det stik modsatte af hvad hooken gør. Den målte sin egen
 * fejl, ikke produktionen. Det er grunden til at denne version går gennem
 * komponenten.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatPacedBlocks } from './useChatPacedBlocks'
import type { ContentBlock } from './sseProtocol'

type FrameRequestCallback = (time: number) => void

describe('PACER-KURVEN — fordelingen af synligt indhold over tid', () => {
  let frames: FrameRequestCallback[] = []
  let ur = 0

  beforeEach(() => {
    frames = []
    ur = 0
    vi.stubGlobal('requestAnimationFrame', vi.fn((cb: FrameRequestCallback) => {
      frames.push(cb)
      return frames.length
    }))
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })
  afterEach(() => vi.unstubAllGlobals())

  function nextFrame(deltaMs = 16): void {
    ur += deltaMs
    const cb = frames.shift()
    expect(cb).toBeDefined()
    act(() => cb?.(ur))
  }

  it('2000 tegn: hvor stor en andel er synlig efter 0,5 / 1 / 2 / 3 s?', () => {
    const tekst = 'Paceren måler ankomsten over et vindue i stedet for pr. frame. '.repeat(40)
    const blocks: ContentBlock[] = [{ type: 'text', text: tekst }]
    const { result } = renderHook(() =>
      useChatPacedBlocks(blocks, { live: true, finalAnswerStarted: true, runId: 'kurve' }),
    )
    const shown = () =>
      (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
    const total = tekst.length
    const rapporter = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 7, 8]
    const punkter: string[] = []
    let idx = 0
    let frames_ = 0

    while (shown() < total && frames_ < 6000) {
      nextFrame()
      frames_ += 1
      const t = frames_ / 60
      while (idx < rapporter.length && t >= (rapporter[idx] ?? 0)) {
        const merke = rapporter[idx] ?? 0
        punkter.push(
          `  t=${merke.toFixed(1)}s  ${shown()}/${total} tegn  ` +
            `(${((shown() / total) * 100).toFixed(0)}%)`,
        )
        idx += 1
      }
    }
    // eslint-disable-next-line no-console
    console.log(`KURVE ${total} tegn:\n${punkter.join('\n')}\n  FÆRDIG efter ${(frames_ / 60).toFixed(2)} s`)

    expect(shown()).toBe(total)
  })

  it('1000 tegn: samme kurve — er den front-loaded?', () => {
    const tekst = 'Et svar der lander i ét hug skal rulle roligt ud over skærmen. '.repeat(17)
    const blocks: ContentBlock[] = [{ type: 'text', text: tekst }]
    const { result } = renderHook(() =>
      useChatPacedBlocks(blocks, { live: true, finalAnswerStarted: true, runId: 'kurve-2' }),
    )
    const shown = () =>
      (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
    const total = tekst.length
    const rapporter = [0.5, 1, 2, 3, 4, 5]
    const punkter: string[] = []
    let idx = 0
    let frames_ = 0

    while (shown() < total && frames_ < 6000) {
      nextFrame()
      frames_ += 1
      const t = frames_ / 60
      while (idx < rapporter.length && t >= (rapporter[idx] ?? 0)) {
        const merke = rapporter[idx] ?? 0
        punkter.push(
          `  t=${merke.toFixed(1)}s  ${shown()}/${total} tegn  ` +
            `(${((shown() / total) * 100).toFixed(0)}%)`,
        )
        idx += 1
      }
    }
    // eslint-disable-next-line no-console
    console.log(`KURVE ${total} tegn:\n${punkter.join('\n')}\n  FÆRDIG efter ${(frames_ / 60).toFixed(2)} s`)

    expect(shown()).toBe(total)
  })
})
