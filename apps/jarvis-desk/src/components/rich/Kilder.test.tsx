import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Kilder } from './Kilder'
import type { ContentBlock } from '../../lib/sseProtocol'

const recallBlok = (result: string): ContentBlock =>
  ({ type: 'tool_use', id: 'r1', name: 'recall', input: {}, result } as ContentBlock)

const webBlok = (url: string): ContentBlock =>
  ({ type: 'tool_use', id: 'w1', name: 'web_fetch', input: { url }, result: '' } as ContentBlock)

describe('Kilder', () => {
  it('viser hukommelses-kilder naar svaret trak paa hukommelsen', () => {
    const blocks = [recallBlok(JSON.stringify({
      results: [{ source: 'MEMORY.md' }, { source: 'brain' }],
    }))]
    render(<Kilder blocks={blocks} />)
    expect(screen.getByText('Hukommelse')).toBeTruthy()
    expect(screen.getByText('Langtidshukommelse')).toBeTruthy()
    expect(screen.getByText('Hjernen')).toBeTruthy()
  })

  it('viser baade hukommelse og web, hver for sig', () => {
    const blocks = [
      recallBlok(JSON.stringify({ results: [{ source: 'MEMORY.md' }] })),
      webBlok('https://www.dr.dk/nyt'),
    ]
    render(<Kilder blocks={blocks} />)
    expect(screen.getByText('Hukommelse')).toBeTruthy()
    expect(screen.getByText('Web')).toBeTruthy()
    expect(screen.getByText('dr.dk')).toBeTruthy()
  })

  it('tegner intet naar der hverken er web eller hukommelse', () => {
    const { container } = render(<Kilder blocks={[]} />)
    expect(container.querySelector('.msg-kilder')).toBeNull()
  })

  it('web-kilder er stadig klikbare links', () => {
    render(<Kilder blocks={[webBlok('https://www.dr.dk/nyt')]} />)
    const a = screen.getByText('dr.dk') as HTMLAnchorElement
    expect(a.tagName).toBe('A')
    expect(a.getAttribute('href')).toBe('https://www.dr.dk/nyt')
  })
})
