import { describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RunTimeline } from './RunTimeline'
import type { ContentBlock } from '../../lib/sseProtocol'

const t = (name: string, input: Record<string, unknown> = {}, status: 'done' | 'error' = 'done') =>
  ({ type: 'tool_use', id: name + Math.random(), name, input, status }) as ContentBlock
const tekst = () => ({ type: 'text', text: 'færdig' }) as ContentBlock

const FORLOEB = [
  t('read_file'), t('read_file'), t('edit_file'),
  t('bash', { command: 'pytest -q' }, 'error'),
  t('edit_file'), t('bash', { command: 'pytest -q' }), tekst(),
]

describe('RunTimeline', () => {
  it('viser resuméet sammenfoldet og forløbet når man åbner', () => {
    render(<RunTimeline blocks={FORLOEB} />)
    expect(screen.getByText(/Læste 2 filer · Ændrede en fil · Kørte tests/)).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
    fireEvent.click(screen.getByRole('button'))
    // læste(2) · ændrede · testede(fejl) · ændrede · testede · svarede
    expect(screen.getAllByRole('listitem')).toHaveLength(6)
  })

  it('markerer en tur hvor noget fejlede', () => {
    const { container } = render(<RunTimeline blocks={FORLOEB} />)
    expect(container.querySelector('.runtl.har-fejl')).toBeTruthy()
  })

  it('viser intet på en tur uden værktøjsarbejde — ren snak har ingen forløb', () => {
    const { container } = render(<RunTimeline blocks={[{ type: 'thinking', thinking: 'hm' } as ContentBlock, tekst()]} />)
    expect(container.firstChild).toBeNull()
  })

  it('nævner hvilken testkommando der kørte', () => {
    render(<RunTimeline blocks={FORLOEB} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getAllByText('pytest -q').length).toBeGreaterThan(0)
  })
})
