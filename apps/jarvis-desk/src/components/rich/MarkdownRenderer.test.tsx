import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
  it('renders bold markdown as <strong>', () => {
    const { container } = render(<MarkdownRenderer text="**fed**" streaming={false} />)
    expect(container.querySelector('strong')?.textContent).toBe('fed')
  })
  it('does NOT render raw HTML (XSS guard)', () => {
    const { container } = render(<MarkdownRenderer text={'<img src=x onerror=alert(1)>'} streaming={false} />)
    expect(container.querySelector('img')).toBeNull()
  })
  it('blocks javascript: links (renders without href)', () => {
    const { container } = render(<MarkdownRenderer text={'[klik](javascript:alert(1))'} streaming={false} />)
    const a = container.querySelector('a')
    expect(a?.getAttribute('href') ?? null).toBeNull()
  })
})
