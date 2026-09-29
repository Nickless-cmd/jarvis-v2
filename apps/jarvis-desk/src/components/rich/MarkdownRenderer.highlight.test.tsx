import { describe, expect, it } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

describe('MarkdownRenderer-kode', () => {
  it('viser færdige linjer under streaming og farver koden asynkront', async () => {
    const view = render(<MarkdownRenderer text={'Før\n```ts\nconst a = 1\nconst b'} streaming />)
    expect(view.container.querySelector('pre code')?.textContent).toBe('const a = 1\n')
    expect(view.container.textContent).not.toContain('const b')
    await waitFor(() => expect(view.container.querySelector('pre.chat-shiki')).not.toBeNull())
    expect(view.container.querySelector('pre code')?.textContent).toBe('const a = 1\n')
    view.rerender(<MarkdownRenderer text={'Før\n```ts\nconst a = 1\nconst b = 2\n'} streaming />)
    await waitFor(() => expect(view.container.querySelector('pre.chat-shiki code')?.textContent)
      .toBe('const a = 1\nconst b = 2\n'))
  })

  it('bevarer rå kode ved ukendt sprog og inline-kode uden blok', async () => {
    const view = render(<MarkdownRenderer text={'`inline`\n\n```ikke-et-sprog\n<hej>\n```'} streaming={false} />)
    expect(view.container.querySelector('p code')?.textContent).toBe('inline')
    await waitFor(() => expect(view.container.querySelector('pre code')?.textContent).toBe('<hej>\n'))
    expect(view.container.querySelector('pre.chat-shiki')).toBeNull()
    expect(view.container.querySelector('pre')?.innerHTML).not.toContain('<hej>')
  })
})
