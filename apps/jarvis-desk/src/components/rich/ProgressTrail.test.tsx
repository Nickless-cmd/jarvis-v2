import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProgressTrail } from './ProgressTrail'
import type { ContentBlock } from '../../lib/sseProtocol'

type ProgressBlock = Extract<ContentBlock, { type: 'progress' }>

function step(message: string, status: ProgressBlock['status'] = 'done', id = 't'): ProgressBlock {
  return { type: 'progress', tool_use_id: id, parent_tool_use_id: null, message, status }
}

describe('ProgressTrail', () => {
  it('viser Forløb-tælleren og narrationen (kort spor = åbent)', () => {
    render(<ProgressTrail items={[step('Analyserede billede: foto.png'), step('Kørte kommando')]} />)
    expect(screen.getByText(/Forløb \(2\)/)).toBeInTheDocument()
    expect(screen.getByText('Analyserede billede: foto.png')).toBeInTheDocument()
    expect(screen.getByText('Kørte kommando')).toBeInTheDocument()
  })

  it('er foldet som default når sporet er langt (>3)', () => {
    const items = Array.from({ length: 5 }, (_, i) => step(`Trin ${i}`, 'done', `t${i}`))
    render(<ProgressTrail items={items} />)
    expect(screen.getByRole('button', { name: /Forløb \(5\)/ })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Trin 0')).not.toBeInTheDocument()
  })

  it('udfolder ved klik', async () => {
    const user = userEvent.setup()
    const items = Array.from({ length: 4 }, (_, i) => step(`Trin ${i}`, 'done', `t${i}`))
    render(<ProgressTrail items={items} />)
    await user.click(screen.getByRole('button', { name: /Forløb \(4\)/ }))
    expect(screen.getByText('Trin 0')).toBeInTheDocument()
  })

  it('renders intet ved tomt spor', () => {
    const { container } = render(<ProgressTrail items={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
