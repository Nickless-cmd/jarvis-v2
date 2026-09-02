import { REAL_TURN_BLOCKS } from './realTurnFixture'
import { hasOrdering, parseBlocks, threadBlocks } from './persistedBlocks'
import type { ChatMessage } from './types'

/**
 * Regressionsvagt mod ÆGTE data.
 *
 * Fixturen er en rigtig tur hentet fra /chat/sessions efter server-rettelsen
 * 2026-09-02 — ikke et konstrueret eksempel. Den fanger to ting på én gang:
 * at serveren gemmer rækkefølgen, og at klienten kan læse den form serveren
 * faktisk sender (et array, ikke en JSON-streng — den antagelse væltede
 * MessageList første gang).
 */
const message: ChatMessage = {
  id: 'real-1',
  role: 'assistant',
  content: 'den flade, sammenklaskede udgave',
  created_at: '2026-09-02T16:35:00Z',
  content_json: REAL_TURN_BLOCKS
}

it('turen fra serveren har ægte rækkefølge', () => {
  const blocks = parseBlocks(message)
  expect(blocks).not.toBeNull()
  expect(hasOrdering(blocks)).toBe(true)
})

it('tråden læses som fortælling → værktøj → fortælling', () => {
  const types = threadBlocks(parseBlocks(message)!).map((b) => b.type)
  expect(types).toEqual([
    'text',
    'tool_use', 'tool_result',
    'text',
    'tool_use', 'tool_result',
    'text',
    'tool_use', 'tool_result',
    'text'
  ])
})

it('hver syntese er sin egen blok — ikke én klump', () => {
  const texts = threadBlocks(parseBlocks(message)!).filter((b) => b.type === 'text')
  expect(texts.length).toBe(4)
  // Fejlen viste sig som sammenklistret tekst uden mellemrum («broen.Imponerende»).
  texts.forEach((t) => expect((t.text ?? '').trim().length).toBeGreaterThan(0))
})

it('progress-sporet holdes ude af tråden', () => {
  const all = parseBlocks(message)!
  expect(all.some((b) => b.type === 'progress')).toBe(true)
  expect(threadBlocks(all).some((b) => b.type === 'progress')).toBe(false)
})
