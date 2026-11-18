import { act, renderHook } from '@testing-library/react-native'
import { usePacedBlocks } from './usePacedBlocks'
import type { ContentBlock } from './sseProtocol'

afterEach(() => jest.useRealTimers())

it('mobilen viser en hurtig tekstbid over flere trin og fortsætter pacen ved stop', async () => {
  jest.useFakeTimers()
  const text = 'Mange ord på én gang. '.repeat(15)
  const blocks: ContentBlock[] = [{ type: 'text', text }]
  const { result, rerender } = await renderHook(({ live }: { live: boolean }) => usePacedBlocks(blocks, live), {
    initialProps: { live: true },
  })
  expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
  await act(async () => { jest.advanceTimersByTime(33) })
  const first = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
  expect(first.length).toBeGreaterThan(0)
  expect(first.length).toBeLessThan(30)
  await act(async () => { jest.advanceTimersByTime(99) })
  expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text.length).toBeGreaterThan(first.length)
  await rerender({ live: false })
  const afterStop = (result.current[0] as Extract<ContentBlock, { type: 'text' }>).text
  expect(afterStop.length).toBeGreaterThan(first.length)
  expect(afterStop.length).toBeLessThan(text.length)
  // 18/11-2026: budgettet var 2000 ms, som var den gamle kadence (28 tegn pr.
  // 33 ms-tick = 848 tegn/s). Modellen er nu desks, og den fordeler
  // efterslæbet over 2 s i stedet for at klippe det: 360 tegn lander på
  // ~4 s — samme kurve som desk er målt til (300 tegn = 3,45 s, 500 = 4,45 s).
  // Kontrakten er at teksten BLIVER færdig, ikke hvor hurtigt.
  await act(async () => { jest.advanceTimersByTime(6000) })
  expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe(text)
})

it('mobilen starter et nyt svar uden synlig tekst fra den forrige tur', async () => {
  jest.useFakeTimers()
  const first = 'Jarvis: ' + 'A'.repeat(72)
  const next = 'Jarvis: ' + 'B'.repeat(72)
  const { result, rerender } = await renderHook(({ text, live }: { text: string; live: boolean }) =>
    usePacedBlocks([{ type: 'text', text }], live), { initialProps: { text: first, live: true } })
  await act(async () => { jest.advanceTimersByTime(33) })
  await rerender({ text: first, live: false })
  await rerender({ text: next, live: true })
  expect((result.current[0] as Extract<ContentBlock, { type: 'text' }>).text).toBe('')
})
