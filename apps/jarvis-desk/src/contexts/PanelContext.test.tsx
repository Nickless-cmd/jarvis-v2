import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { PanelProvider } from './PanelContext'
import { usePanel } from '../hooks/usePanel'

function Probe() {
  const p = usePanel()
  return (
    <div>
      <span data-testid="open">{String(p.open)}</span>
      <span data-testid="title">{p.artifact?.title ?? '-'}</span>
      <button onClick={() => p.open_({ kind: 'markdown', title: 'Spec', content: '# x' })}>open</button>
      <button onClick={() => p.close()}>close</button>
    </div>
  )
}

describe('PanelContext', () => {
  it('open_ åbner med artifact, close lukker', () => {
    render(<PanelProvider defaultWidth={480}><Probe /></PanelProvider>)
    expect(screen.getByTestId('open').textContent).toBe('false')
    act(() => { screen.getByText('open').click() })
    expect(screen.getByTestId('open').textContent).toBe('true')
    expect(screen.getByTestId('title').textContent).toBe('Spec')
    act(() => { screen.getByText('close').click() })
    expect(screen.getByTestId('open').textContent).toBe('false')
  })
})
