import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WebSidebarFrame } from './WebSidebarFrame'

describe('WebSidebarFrame', () => {
  it('starts closed in web mode and toggles the sidebar with its button', () => {
    render(
      <WebSidebarFrame web sidebar={<aside>Mine samtaler</aside>}>
        <main>Samtale</main>
      </WebSidebarFrame>,
    )

    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
    expect(screen.getByText('Samtale')).toBeInTheDocument()
    const open = screen.getByRole('button', { name: 'Åbn sidepanel' })
    expect(open).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(open)
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    const close = screen.getByRole('button', { name: 'Luk sidepanel' })
    expect(close).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(close)
    expect(screen.queryByText('Mine samtaler')).not.toBeInTheDocument()
  })

  it('keeps the desktop sidebar visible without a web toggle', () => {
    render(
      <WebSidebarFrame web={false} sidebar={<aside>Mine samtaler</aside>}>
        <main>Samtale</main>
      </WebSidebarFrame>,
    )
    expect(screen.getByText('Mine samtaler')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Luk sidepanel' })).not.toBeInTheDocument()
  })
})
