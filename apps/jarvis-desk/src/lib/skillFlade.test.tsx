import { describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { streamReducer, initialStreamState, liveBlokke } from './streamReducer'
import { foldToolResults } from './foldToolResults'
import { MessageRow } from '../components/rich/MessageRow'
import type { StreamEvent } from './sseProtocol'

const matches = [{ name: 'xlsx', score: 0.78, primary: true }, { name: 'csv', score: 0.71, primary: false }]
const start = (id: string) => ({ type: 'message_start', message: { id, model: 'm', provider: 'p', lane: 'l', usage: { input_tokens: 0 } } }) as unknown as StreamEvent

describe('skill_surface i strømmen', () => {
  it('v2-formen (system_event) lander — den direkte case alene ville aldrig fyre', () => {
    let s = streamReducer(initialStreamState(), start('r1'))
    s = streamReducer(s, { type: 'system_event', kind: 'skill_surface', payload: { matches, primary: true } } as unknown as StreamEvent)
    expect(s.skillFlade?.matches.map((m) => m.name)).toEqual(['xlsx', 'csv'])
  })

  it('v1-formen lander også', () => {
    const s = streamReducer(initialStreamState(), { type: 'skill_surface', matches, primary: true })
    expect(s.skillFlade?.primary).toBe(true)
  })

  it('står FØRST i de live blokke og overlever første tekst-blok på index 0', () => {
    let s = streamReducer(initialStreamState(), start('r1'))
    s = streamReducer(s, { type: 'skill_surface', matches, primary: true })
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: 'hej' } })
    expect(liveBlokke(s).map((b) => b.type)).toEqual(['skill_surface', 'text'])
  })

  it('nyt run nulstiller, samme run (replay) beholder', () => {
    let s = streamReducer(initialStreamState(), start('r1'))
    s = streamReducer(s, { type: 'skill_surface', matches, primary: true })
    expect(streamReducer(s, start('r1')).skillFlade).toBeDefined()
    expect(streamReducer(s, start('r2')).skillFlade).toBeUndefined()
  })

  it('gemt blok foldes med', () => {
    const [b] = foldToolResults([{ type: 'skill_surface', matches, primary: true }])
    expect(b).toEqual({ type: 'skill_surface', matches, primary: true })
  })
})

describe('SkillSurfaceLine', () => {
  it('stærkt match: navn, score og «stærkt match»; fold ud viser alle', () => {
    render(<MessageRow role="assistant" density="compact" streaming={false} blocks={[{ type: 'skill_surface', matches, primary: true }]} />)
    expect(screen.getByText(/Skill-match: xlsx/)).toBeInTheDocument()
    expect(screen.getByText(/· 0,78 · stærkt match · \+1 svagere/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Skill-match/ }))
    expect(screen.getByText('csv')).toBeInTheDocument()
  })

  it('kun svage: foreslået, ikke match', () => {
    render(<MessageRow role="assistant" density="compact" streaming={false} blocks={[{ type: 'skill_surface', primary: false, matches: [{ name: 'pdf', score: 0.72, primary: false }] }]} />)
    expect(screen.getByText(/Skills foreslået: pdf/)).toBeInTheDocument()
    expect(screen.getByText(/bedst 0,72/)).toBeInTheDocument()
  })
})

describe('kobling', () => {
  it('begge views tegner live-beskeden gennem liveBlokke', async () => {
    const fs = await import('fs')
    for (const v of ['ChatView', 'CodeView']) {
      const k = fs.readFileSync(`src/views/${v}.tsx`, 'utf-8')
      expect(k).toMatch(/liveBlokke\(stream\)/)
      expect(k).not.toMatch(/withoutPauseAsk\(stream\.blocks\)/)
    }
  })
})
