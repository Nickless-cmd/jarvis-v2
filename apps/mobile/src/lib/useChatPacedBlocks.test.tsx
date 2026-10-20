import { act, renderHook } from '@testing-library/react-native'
import type { ContentBlock } from './sseProtocol'
import { useChatPacedBlocks } from './useChatPacedBlocks'

type Frame = (time: number) => void

describe('useChatPacedBlocks', () => {
  let frames: Frame[]
  let clock: number

  beforeEach(() => {
    frames = []
    clock = 0
    global.requestAnimationFrame = jest.fn((callback: Frame) => {
      frames.push(callback)
      return frames.length
    })
    global.cancelAnimationFrame = jest.fn()
  })

  async function nextFrame(delta = 16) {
    clock += delta
    const callback = frames.shift()
    expect(callback).toBeDefined()
    await act(async () => callback?.(clock))
  }

  it('fortsætter i trin efter message_stop og dumper aldrig resten', async () => {
    const text = 'Et roligt svar. '.repeat(40)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = await renderHook(({ live }: { live: boolean }) => useChatPacedBlocks(blocks, {
      live, finalAnswerStarted: true, runId: 'run-1',
    }), { initialProps: { live: true } })
    await nextFrame()
    await nextFrame()
    const beforeStop = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(beforeStop.length).toBeGreaterThan(0)
    await rerender({ live: false })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(beforeStop)
    let previous = beforeStop.length
    while ((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length < text.length) {
      await nextFrame()
      const current = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length
      expect(current - previous).toBeLessThanOrEqual(6)
      previous = current
    }
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
  })

  it('viser en persisteret tekst straks fordi den aldrig blev set live', async () => {
    const text = 'Et allerede færdigt svar.'
    const { result } = await renderHook(() => useChatPacedBlocks([{ type: 'text', text }], {
      live: false, finalAnswerStarted: true, runId: 'saved',
    }))
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('ruller færdig når finalAnswerStarted udebliver', async () => {
    const text = 'Svar '.repeat(100)
    const blocks: ContentBlock[] = [{ type: 'text', text }]
    const { result, rerender } = await renderHook(({
      live, paceAllText,
    }: { live: boolean; paceAllText: boolean }) => useChatPacedBlocks(blocks, {
      live, paceAllText, finalAnswerStarted: false, runId: 'uden-fold',
    }), { initialProps: { live: true, paceAllText: true } })
    await nextFrame()
    await nextFrame()
    const beforeStop = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
    expect(beforeStop.length).toBeGreaterThan(0)
    await rerender({ live: false, paceAllText: false })
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(beforeStop)
    while ((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length < text.length) {
      await nextFrame()
    }
    expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
  })
})
